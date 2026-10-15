"""Tests for vivosun_thermo coordinator."""

from asyncio import TimeoutError as AsyncTimeoutError
from struct import pack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.exc import BleakError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.vivosun_thermo.const import CONF_UPDATE_MODE, UpdateMode
from custom_components.vivosun_thermo.coordinator import VivosunThermoSensorCoordinator


def _advertisement(main_temp, main_humidity, external_temp, external_humidity, counter):
    """Broadcast payload for AA:BB:CC:DD:EE:FF: the address reversed, an unknown uint16, the
    four readings (int16 / 16) and the seconds-since-power-up counter."""
    return bytes.fromhex("ffeeddccbbaa") + pack(
        "<HhhhhI", 0x1360, main_temp, main_humidity, external_temp, external_humidity, counter
    )


def _service_info(manufacturer_data):
    info = MagicMock()
    info.manufacturer_data = manufacturer_data
    return info


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

    async def test_read_raw_data_ignores_extra_notifications(
        self, mock_bleak_client, valid_sensor_data_both_probes
    ):
        """A chatty device must not raise InvalidStateError out of the notify callback."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)
            callback(None, bytearray(11))

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        data = await VivosunThermoSensorCoordinator._read_raw_data(mock_bleak_client)

        assert data == valid_sensor_data_both_probes

    async def test_read_raw_data_timeout(self, mock_bleak_client):
        """Test timeout when reading from BLE device."""

        async def mock_notify_timeout(uuid, callback):
            # Don't call callback to simulate timeout
            pass

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify_timeout)

        with pytest.raises(AsyncTimeoutError):
            await VivosunThermoSensorCoordinator._read_raw_data(mock_bleak_client)

    async def test_read_sensor_data(
        self, hass, mock_config_entry, mock_bleak_client, valid_sensor_data_both_probes
    ):
        """Test reading and decoding sensor data."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 22.5
        assert data["main"]["humidity"] == 65.0
        assert data["external"]["temperature_c"] == 18.0
        assert data["external"]["humidity"] == 70.0

    @pytest.mark.parametrize(
        "failure",
        [BleakError("boom"), TimeoutError()],
        ids=["bleak_error", "timeout"],
    )
    async def test_read_sensor_data_connect_failure(self, hass, mock_config_entry, failure):
        """Connect failures surface as UpdateFailed, not raw bleak errors."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with (
            patch(
                "custom_components.vivosun_thermo.coordinator.bluetooth."
                "async_ble_device_from_address",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.vivosun_thermo.coordinator.establish_connection",
                AsyncMock(side_effect=failure),
            ),
            pytest.raises(UpdateFailed),
        ):
            await coordinator._read_sensor_data()

    async def test_read_sensor_data_device_out_of_range(self, hass, mock_config_entry):
        """A device HA cannot currently see surfaces as UpdateFailed."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with (
            patch(
                "custom_components.vivosun_thermo.coordinator.bluetooth."
                "async_ble_device_from_address",
                return_value=None,
            ),
            pytest.raises(UpdateFailed),
        ):
            await coordinator._read_sensor_data()

    async def test_read_sensor_data_disconnects_after_read(
        self, hass, mock_config_entry, mock_bleak_client, valid_sensor_data_both_probes
    ):
        """The connection is always released, so the device stays reachable to other clients."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        await coordinator._read_sensor_data()

        mock_bleak_client.disconnect.assert_awaited_once()

    async def test_read_sensor_data_disconnects_after_read_failure(
        self, hass, mock_config_entry, mock_bleak_client
    ):
        """A failed read still releases the connection rather than leaking it."""
        mock_bleak_client.start_notify = AsyncMock(side_effect=BleakError("boom"))

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await coordinator._read_sensor_data()

        mock_bleak_client.disconnect.assert_awaited_once()

    async def test_read_sensor_data_survives_failing_disconnect(
        self, hass, mock_config_entry, mock_bleak_client, valid_sensor_data_both_probes
    ):
        """A teardown failure must not discard a reading that already succeeded."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)
        mock_bleak_client.disconnect = AsyncMock(side_effect=BleakError("disconnect failed"))

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 22.5

    async def test_failing_disconnect_does_not_mask_read_error(
        self, hass, mock_config_entry, mock_bleak_client
    ):
        """The read failure, not the teardown failure, is what reaches the coordinator."""
        mock_bleak_client.start_notify = AsyncMock(side_effect=BleakError("read boom"))
        mock_bleak_client.disconnect = AsyncMock(side_effect=BleakError("disconnect failed"))

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed, match="read boom"):
            await coordinator._read_sensor_data()

    @pytest.mark.parametrize("size", [0, 4, 10], ids=["empty", "truncated", "one_byte_short"])
    async def test_read_sensor_data_rejects_short_payload(
        self, hass, mock_config_entry, mock_bleak_client, size
    ):
        """A frame too short to decode is a failed update, not a struct error."""

        async def mock_notify(uuid, callback):
            callback(None, bytearray(size))

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed, match="need 11"):
            await coordinator._read_sensor_data()

    async def test_read_sensor_data_accepts_minimal_payload(
        self, hass, mock_config_entry, mock_bleak_client
    ):
        """The shortest frame that carries every reading is still decoded."""

        async def mock_notify(uuid, callback):
            callback(None, bytearray(11))

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 0.0

    async def test_coordinator_initialization(self, hass, mock_config_entry):
        """Test coordinator initialization."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        assert coordinator.name == "VIVOSUN AeroLab THB1S"
        assert coordinator.discovery_name == "ThermoBeacon2"
        assert coordinator.discovery_address == "AA:BB:CC:DD:EE:FF"

    async def test_coordinator_update_method(
        self, hass, mock_config_entry, mock_bleak_client, valid_sensor_data_main_only
    ):
        """Test coordinator update method integration."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_main_only)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        assert coordinator.data["main"]["temperature_c"] == 22.5
        assert coordinator.data["external"] is None

    @pytest.mark.parametrize(
        ("options", "expected"),
        [
            ({}, UpdateMode.PASSIVE),
            ({CONF_UPDATE_MODE: "passive"}, UpdateMode.PASSIVE),
            ({CONF_UPDATE_MODE: "active"}, UpdateMode.ACTIVE),
        ],
        ids=["default", "passive", "active"],
    )
    async def test_update_mode_from_options(self, hass, mock_config_entry, options, expected):
        """The update mode comes from the entry options and defaults to passive."""
        mock_config_entry.options = options

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        assert coordinator.update_mode is expected

    async def test_passive_reads_advertisement_without_connecting(
        self, hass, mock_config_entry, last_service_info
    ):
        """Passive mode answers the poll from the broadcast and never connects."""
        mock_config_entry.options = {CONF_UPDATE_MODE: UpdateMode.PASSIVE}
        last_service_info.return_value = _service_info(
            {0x0019: _advertisement(360, 1040, 288, 1120, 100)}
        )
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with patch(
            "custom_components.vivosun_thermo.coordinator.establish_connection", AsyncMock()
        ) as connect:
            first = await coordinator._read_sensor_data()
            second = await coordinator._read_sensor_data()

        connect.assert_not_called()
        assert first == second
        assert first["main"]["temperature_c"] == 22.5
        assert first["main"]["humidity"] == 65.0
        assert first["external"] is not None
        assert first["external"]["temperature_c"] == 18.0
        assert first["external"]["humidity"] == 70.0
        last_service_info.assert_called_with(hass, "AA:BB:CC:DD:EE:FF", connectable=False)

    async def test_passive_advertisement_without_external_probe(
        self, hass, mock_config_entry, last_service_info
    ):
        """A broadcast with no external probe reports it as missing, like the status frame."""
        mock_config_entry.options = {CONF_UPDATE_MODE: UpdateMode.PASSIVE}
        last_service_info.return_value = _service_info(
            {0x0019: _advertisement(360, 1040, -1, -1, 100)}
        )

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 22.5
        assert data["external"] is None

    @pytest.mark.parametrize(
        ("regular_counter", "button_counter", "expected_temp"),
        [(200, 150, 22.5), (150, 200, 20.0)],
        ids=["regular_newer", "button_newer"],
    )
    async def test_passive_newest_record_wins(
        self,
        hass,
        mock_config_entry,
        last_service_info,
        regular_counter,
        button_counter,
        expected_temp,
    ):
        """Home Assistant keeps the last 0x0019 and 0x8019 records; the newer one is used."""
        mock_config_entry.options = {CONF_UPDATE_MODE: UpdateMode.PASSIVE}
        last_service_info.return_value = _service_info(
            {
                0x0019: _advertisement(360, 1040, 288, 1120, regular_counter),
                0x8019: _advertisement(320, 960, 288, 1120, button_counter),
            }
        )

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == expected_temp

    async def test_passive_skips_short_record(self, hass, mock_config_entry, last_service_info):
        """A truncated record is ignored when the other company id carries a full one."""
        mock_config_entry.options = {CONF_UPDATE_MODE: UpdateMode.PASSIVE}
        last_service_info.return_value = _service_info(
            {0x0019: bytes(19), 0x8019: _advertisement(320, 960, -1, -1, 100)}
        )

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 20.0

    @pytest.mark.parametrize(
        ("manufacturer_data", "message"),
        [
            (None, "No broadcast heard"),
            ({}, "No readings"),
            ({0x0019: bytes(19)}, "No readings"),
            ({0x1234: _advertisement(320, 960, 288, 1120, 100)}, "No readings"),
        ],
        ids=["not_heard", "no_records", "short_record", "other_company"],
    )
    async def test_passive_unusable_broadcast_fails_without_connecting(
        self, hass, mock_config_entry, last_service_info, manufacturer_data, message
    ):
        """Passive mode fails the poll rather than falling back to a connection."""
        mock_config_entry.options = {CONF_UPDATE_MODE: UpdateMode.PASSIVE}
        last_service_info.return_value = (
            None if manufacturer_data is None else _service_info(manufacturer_data)
        )
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)

        with (
            patch(
                "custom_components.vivosun_thermo.coordinator.establish_connection", AsyncMock()
            ) as connect,
            pytest.raises(UpdateFailed, match=message),
        ):
            await coordinator._read_sensor_data()

        connect.assert_not_called()

    async def test_active_ignores_advertisement(
        self,
        hass,
        mock_config_entry,
        mock_bleak_client,
        valid_sensor_data_both_probes,
        last_service_info,
    ):
        """Active mode connects even when a broadcast is available."""
        last_service_info.return_value = _service_info(
            {0x0019: _advertisement(320, 960, 288, 1120, 100)}
        )

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        data = await coordinator._read_sensor_data()

        assert data["main"]["temperature_c"] == 22.5
        mock_bleak_client.start_notify.assert_called_once()
        last_service_info.assert_not_called()
