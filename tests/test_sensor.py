"""Tests for vivosun_thermo sensor."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from custom_components.vivosun_thermo.const import DOMAIN, SENSOR_TYPES
from custom_components.vivosun_thermo.coordinator import VivosunThermoSensorCoordinator
from custom_components.vivosun_thermo.sensor import VivosunThermoSensor, async_setup_entry


def description(key):
    """The SensorEntityDescription a platform would hand the entity for `key`."""
    return next(d for d in SENSOR_TYPES if d.key == key)


class TestVivosunThermoSensor:
    """Test VivosunThermoSensor."""

    async def test_sensor_attributes_temperature(self, hass, mock_config_entry):
        """Test temperature sensor attributes."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", description("temperature_c"))

        assert sensor.name == "Main Temperature"
        assert sensor.device_class == SensorDeviceClass.TEMPERATURE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor.suggested_display_precision == 1
        assert sensor._attr_unique_id == "ThermoBeacon2-AA:BB:CC:DD:EE:FF-main-temperature_c"
        assert sensor.should_poll is False

    async def test_sensor_attributes_humidity(self, hass, mock_config_entry):
        """Test humidity sensor attributes."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", description("humidity"))

        assert sensor.name == "Main Humidity"
        assert sensor.device_class == SensorDeviceClass.HUMIDITY
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.suggested_display_precision == 0

    async def test_sensor_attributes_vpd(self, hass, mock_config_entry):
        """Test VPD sensor attributes."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", description("vpd"))

        assert sensor.name == "Main Vapor Pressure Deficit"
        assert sensor.device_class is None
        assert sensor.native_unit_of_measurement == "kPa"
        assert sensor.suggested_display_precision == 2

    async def test_sensor_native_value(self, hass, mock_config_entry):
        """Test sensor native value property."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            "external": {"temperature_c": 18.0, "humidity": 70.0, "vpd": 0.62},
        }

        sensor_main_temp = VivosunThermoSensor(coordinator, "main", description("temperature_c"))
        assert sensor_main_temp.native_value == 22.5

        sensor_main_humidity = VivosunThermoSensor(coordinator, "main", description("humidity"))
        assert sensor_main_humidity.native_value == 65.0

        sensor_external_temp = VivosunThermoSensor(
            coordinator, "external", description("temperature_c")
        )
        assert sensor_external_temp.native_value == 18.0

    async def test_sensor_available_with_data(self, hass, mock_config_entry):
        """Test sensor availability when data exists."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", description("temperature_c"))
        assert sensor.available is True

    async def test_sensor_unavailable_without_data(self, hass, mock_config_entry):
        """Test sensor unavailability when probe data is missing."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            # external probe not connected
        }

        sensor = VivosunThermoSensor(coordinator, "external", description("temperature_c"))
        assert sensor.available is False

    async def test_sensor_device_info(self, hass, mock_config_entry):
        """Test sensor device info."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", description("temperature_c"))

        assert sensor._attr_device_info["identifiers"] == {(DOMAIN, "AA:BB:CC:DD:EE:FF")}
        assert sensor._attr_device_info["name"] == "VIVOSUN AeroLab THB1S"
        assert sensor._attr_device_info["manufacturer"] == "VIVOSUN"
        assert sensor._attr_device_info["model"] == "THB1S"

    async def test_sensor_device_info_unknown_device(self, hass):
        """Test sensor device info for unknown device type."""
        entry = MagicMock()
        entry.data = {
            "name": "Unknown Sensor",
            "discovery_name": "UnknownDevice",
            "discovery_address": "AA:BB:CC:DD:EE:FF",
        }

        coordinator = VivosunThermoSensorCoordinator(hass, entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", description("temperature_c"))

        assert sensor._attr_device_info["name"] == "Unknown Sensor"
        assert sensor._attr_device_info["manufacturer"] is None
        assert sensor._attr_device_info["model"] is None

    @pytest.mark.parametrize(
        ("last_update_success", "expected"),
        [(True, True), (False, False)],
        ids=["polling_ok", "polling_failed"],
    )
    async def test_available_follows_update_success(
        self, hass, mock_config_entry, last_update_success, expected
    ):
        """A device that stops answering must not keep serving its last reading."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {"main": {"temperature_c": 22.5}, "external": None}
        coordinator.last_update_success = last_update_success

        sensor = VivosunThermoSensor(coordinator, "main", description("temperature_c"))

        assert sensor.available is expected

    async def test_available_false_for_absent_probe(self, hass, mock_config_entry):
        """An unplugged external probe stays unavailable even while polling succeeds."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {"main": {"temperature_c": 22.5}, "external": None}
        coordinator.last_update_success = True

        sensor = VivosunThermoSensor(coordinator, "external", description("temperature_c"))

        assert sensor.available is False

    async def test_async_setup_entry_both_probes(self, hass, mock_config_entry):
        """Test async_setup_entry creates entities for both probes."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            "external": {"temperature_c": 18.0, "humidity": 70.0, "vpd": 0.62},
        }

        mock_config_entry.runtime_data = coordinator

        entities = []

        def mock_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create 6 entities: 3 sensor types × 2 probes
        assert len(entities) == 6

        # Verify we have main and external sensors
        probe_types = {e.probe_type for e in entities}
        assert probe_types == {"main", "external"}

        # Verify we have all sensor types
        sensor_types = {e.sensor_type for e in entities}
        assert sensor_types == {"temperature_c", "humidity", "vpd"}

    async def test_async_setup_entry_main_probe_only(self, hass, mock_config_entry):
        """Test async_setup_entry creates entities only for main probe."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            # external probe not connected
        }

        mock_config_entry.runtime_data = coordinator

        entities = []

        def mock_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create 3 entities: 3 sensor types × 1 probe (main only)
        assert len(entities) == 3

        # Verify all are main probe sensors
        probe_types = {e.probe_type for e in entities}
        assert probe_types == {"main"}

    async def test_sensor_unique_ids_different(self, hass, mock_config_entry):
        """Test that sensors have unique IDs."""
        coordinator = VivosunThermoSensorCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            "external": {"temperature_c": 18.0, "humidity": 70.0, "vpd": 0.62},
        }

        sensors = [
            VivosunThermoSensor(coordinator, "main", description("temperature_c")),
            VivosunThermoSensor(coordinator, "main", description("humidity")),
            VivosunThermoSensor(coordinator, "external", description("temperature_c")),
        ]

        unique_ids = [s._attr_unique_id for s in sensors]
        assert len(unique_ids) == len(set(unique_ids))  # All unique
