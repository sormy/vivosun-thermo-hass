"""Tests for vivosun_thermo coordinator."""

from asyncio import TimeoutError as AsyncTimeoutError
from unittest.mock import AsyncMock

import pytest

from custom_components.vivosun_thermo.coordinator import VivosunThermoSensorCoordinator


class TestVivosunThermoSensorCoordinator:
    """Test VivosunThermoSensorCoordinator."""

    async def test_decode_int16(self):
        """Test decoding int16 values."""
        data = bytearray([0x68, 0x01])  # 360 in little-endian
        assert VivosunThermoSensorCoordinator._decode_int16(data, 0) == 360

        data = bytearray([0xFF, 0xFF])  # -1 in little-endian
        assert VivosunThermoSensorCoordinator._decode_int16(data, 0) == -1

    async def test_decode_float(self):
        """Test decoding float values (int16 / 16)."""
        data = bytearray([0x68, 0x01])  # 360 / 16 = 22.5
        assert VivosunThermoSensorCoordinator._decode_float(data, 0) == 22.5

        data = bytearray([0x00, 0x00])  # 0 / 16 = 0.0
        assert VivosunThermoSensorCoordinator._decode_float(data, 0) == 0.0

        data = bytearray([0x10, 0x04])  # 1040 / 16 = 65.0
        assert VivosunThermoSensorCoordinator._decode_float(data, 0) == 65.0

    async def test_calculate_vpd_normal(self):
        """Test VPD calculation with normal values."""
        # At 22.5°C and 65% RH, VPD should be ~0.95 kPa
        vpd = VivosunThermoSensorCoordinator._calculate_vpd(22.5, 65.0)
        assert 0.9 < vpd < 1.0

    async def test_calculate_vpd_low_humidity(self):
        """Test VPD calculation with low humidity (high VPD)."""
        # At 25°C and 30% RH, VPD should be higher (~2.2 kPa)
        vpd = VivosunThermoSensorCoordinator._calculate_vpd(25.0, 30.0)
        assert 2.0 < vpd < 2.5

    async def test_calculate_vpd_high_humidity(self):
        """Test VPD calculation with high humidity (low VPD)."""
        # At 20°C and 90% RH, VPD should be lower (~0.23 kPa)
        vpd = VivosunThermoSensorCoordinator._calculate_vpd(20.0, 90.0)
        assert 0.2 < vpd < 0.3

    async def test_calculate_vpd_saturation(self):
        """Test VPD calculation at 100% humidity (VPD = 0)."""
        vpd = VivosunThermoSensorCoordinator._calculate_vpd(20.0, 100.0)
        assert abs(vpd) < 0.01  # Should be very close to 0

    async def test_decode_probe_data(self):
        """Test decoding probe data."""
        data = bytearray(
            [
                0x00,
                0x68,
                0x01,  # temp = 360 (22.5°C)
                0x10,
                0x04,  # humidity = 1040 (65.0%)
            ]
        )

        probe = VivosunThermoSensorCoordinator._decode_probe_data(data, 1, 3)

        assert probe["temperature_c"] == 22.5
        assert probe["humidity"] == 65.0
        assert 0.9 < probe["vpd"] < 1.0

    async def test_decode_raw_data_both_probes(self, valid_sensor_data_both_probes):
        """Test decoding data with both probes connected."""
        result = VivosunThermoSensorCoordinator._decode_raw_data(valid_sensor_data_both_probes)

        assert result["main"]["temperature_c"] == 22.5
        assert result["main"]["humidity"] == 65.0
        assert 0.9 < result["main"]["vpd"] < 1.0

        assert result["external"] is not None
        assert result["external"]["temperature_c"] == 18.0
        assert result["external"]["humidity"] == 70.0
        assert 0.5 < result["external"]["vpd"] < 0.7

    async def test_decode_raw_data_main_only(self, valid_sensor_data_main_only):
        """Test decoding data with only main probe connected."""
        result = VivosunThermoSensorCoordinator._decode_raw_data(valid_sensor_data_main_only)

        assert result["main"]["temperature_c"] == 22.5
        assert result["main"]["humidity"] == 65.0
        assert result["external"] is None

    async def test_decode_raw_data_edge_values(self):
        """Test decoding with edge case values."""
        # Very low temperature and humidity
        data = bytearray(
            [
                0x00,
                0x00,
                0x00,  # temp = 0 (0.0°C)
                0x00,
                0x00,  # humidity = 0 (0.0%)
                0x00,
                0x00,
                0xFF,
                0xFF,  # External not connected
                0xFF,
                0xFF,
            ]
        )

        result = VivosunThermoSensorCoordinator._decode_raw_data(data)
        assert result["main"]["temperature_c"] == 0.0
        assert result["main"]["humidity"] == 0.0
        assert result["external"] is None

    async def test_read_raw_data(self, mock_bleak_client, valid_sensor_data_both_probes):
        """Test reading raw data from BLE device."""

        async def mock_notify(uuid, callback):
            # Simulate notification callback
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        data = await VivosunThermoSensorCoordinator._read_raw_data(mock_bleak_client)

        assert data == valid_sensor_data_both_probes
        mock_bleak_client.start_notify.assert_called_once()
        mock_bleak_client.write_gatt_char.assert_called_once()
        mock_bleak_client.stop_notify.assert_called_once()

    async def test_read_raw_data_timeout(self, mock_bleak_client):
        """Test timeout when reading from BLE device."""

        async def mock_notify_timeout(uuid, callback):
            # Don't call callback to simulate timeout
            pass

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify_timeout)

        with pytest.raises(AsyncTimeoutError):
            await VivosunThermoSensorCoordinator._read_raw_data(mock_bleak_client)

    async def test_read_sensor_data(
        self, hass, config_entry_data, mock_bleak_client, valid_sensor_data_both_probes
    ):
        """Test reading and decoding sensor data."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 22.5
        assert data["main"]["humidity"] == 65.0
        assert data["external"]["temperature_c"] == 18.0
        assert data["external"]["humidity"] == 70.0

    async def test_coordinator_initialization(self, hass, config_entry_data):
        """Test coordinator initialization."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)

        assert coordinator.name == "VIVOSUN AeroLab THB1S"
        assert coordinator.discovery_name == "ThermoBeacon2"
        assert coordinator.discovery_address == "AA:BB:CC:DD:EE:FF"

    async def test_coordinator_update_method(
        self, hass, config_entry_data, mock_bleak_client, valid_sensor_data_main_only
    ):
        """Test coordinator update method integration."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_main_only)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        await coordinator.async_refresh()

        assert coordinator.data["main"]["temperature_c"] == 22.5
        assert coordinator.data["external"] is None
