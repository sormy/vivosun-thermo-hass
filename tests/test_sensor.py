"""Tests for vivosun_thermo sensor."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from custom_components.vivosun_thermo.const import DOMAIN
from custom_components.vivosun_thermo.coordinator import VivosunThermoSensorCoordinator
from custom_components.vivosun_thermo.sensor import VivosunThermoSensor, async_setup_entry


class TestVivosunThermoSensor:
    """Test VivosunThermoSensor."""

    async def test_sensor_attributes_temperature(self, hass, config_entry_data, mock_config_entry):
        """Test temperature sensor attributes."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", "temperature_c", mock_config_entry)

        assert sensor._attr_name == "VIVOSUN AeroLab THB1S Main Temperature"
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor._attr_suggested_display_precision == 1
        assert sensor._attr_unique_id == "ThermoBeacon2-AA:BB:CC:DD:EE:FF-main-temperature_c"
        assert sensor._attr_should_poll is False

    async def test_sensor_attributes_humidity(self, hass, config_entry_data, mock_config_entry):
        """Test humidity sensor attributes."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", "humidity", mock_config_entry)

        assert sensor._attr_name == "VIVOSUN AeroLab THB1S Main Humidity"
        assert sensor._attr_device_class == SensorDeviceClass.HUMIDITY
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        assert sensor._attr_suggested_display_precision == 0

    async def test_sensor_attributes_vpd(self, hass, config_entry_data, mock_config_entry):
        """Test VPD sensor attributes."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", "vpd", mock_config_entry)

        assert sensor._attr_name == "VIVOSUN AeroLab THB1S Main Vapor Pressure Deficit"
        assert sensor._attr_device_class is None
        assert sensor._attr_native_unit_of_measurement == "kPa"
        assert sensor._attr_suggested_display_precision == 2

    async def test_sensor_native_value(self, hass, config_entry_data, mock_config_entry):
        """Test sensor native value property."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            "external": {"temperature_c": 18.0, "humidity": 70.0, "vpd": 0.62},
        }

        sensor_main_temp = VivosunThermoSensor(
            coordinator, "main", "temperature_c", mock_config_entry
        )
        assert sensor_main_temp.native_value == 22.5

        sensor_main_humidity = VivosunThermoSensor(
            coordinator, "main", "humidity", mock_config_entry
        )
        assert sensor_main_humidity.native_value == 65.0

        sensor_external_temp = VivosunThermoSensor(
            coordinator, "external", "temperature_c", mock_config_entry
        )
        assert sensor_external_temp.native_value == 18.0

    async def test_sensor_available_with_data(self, hass, config_entry_data, mock_config_entry):
        """Test sensor availability when data exists."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", "temperature_c", mock_config_entry)
        assert sensor.available is True

    async def test_sensor_unavailable_without_data(
        self, hass, config_entry_data, mock_config_entry
    ):
        """Test sensor unavailability when probe data is missing."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            # external probe not connected
        }

        sensor = VivosunThermoSensor(coordinator, "external", "temperature_c", mock_config_entry)
        assert sensor.available is False

    async def test_sensor_device_info(self, hass, config_entry_data, mock_config_entry):
        """Test sensor device info."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", "temperature_c", mock_config_entry)

        assert sensor._attr_device_info["identifiers"] == {(DOMAIN, "AA:BB:CC:DD:EE:FF")}
        assert sensor._attr_device_info["name"] == "VIVOSUN AeroLab THB1S"
        assert sensor._attr_device_info["manufacturer"] == "VIVOSUN"
        assert sensor._attr_device_info["model"] == "THB1S"

    async def test_sensor_device_info_unknown_device(self, hass, mock_config_entry):
        """Test sensor device info for unknown device type."""
        config_data = {
            "name": "Unknown Sensor",
            "discovery_name": "UnknownDevice",
            "discovery_address": "AA:BB:CC:DD:EE:FF",
        }

        coordinator = VivosunThermoSensorCoordinator(hass, config_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
        }

        sensor = VivosunThermoSensor(coordinator, "main", "temperature_c", mock_config_entry)

        assert sensor._attr_device_info["name"] == "UnknownDevice"
        assert sensor._attr_device_info["manufacturer"] is None
        assert sensor._attr_device_info["model"] is None

    async def test_async_setup_entry_both_probes(
        self, hass, mock_config_entry, config_entry_data, mock_bleak_client
    ):
        """Test async_setup_entry creates entities for both probes."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            "external": {"temperature_c": 18.0, "humidity": 70.0, "vpd": 0.62},
        }

        hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

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

    async def test_async_setup_entry_main_probe_only(
        self, hass, mock_config_entry, config_entry_data, mock_bleak_client
    ):
        """Test async_setup_entry creates entities only for main probe."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            # external probe not connected
        }

        hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

        entities = []

        def mock_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create 3 entities: 3 sensor types × 1 probe (main only)
        assert len(entities) == 3

        # Verify all are main probe sensors
        probe_types = {e.probe_type for e in entities}
        assert probe_types == {"main"}

    async def test_sensor_unique_ids_different(self, hass, config_entry_data, mock_config_entry):
        """Test that sensors have unique IDs."""
        coordinator = VivosunThermoSensorCoordinator(hass, config_entry_data)
        coordinator.data = {
            "main": {"temperature_c": 22.5, "humidity": 65.0, "vpd": 0.95},
            "external": {"temperature_c": 18.0, "humidity": 70.0, "vpd": 0.62},
        }

        sensors = [
            VivosunThermoSensor(coordinator, "main", "temperature_c", mock_config_entry),
            VivosunThermoSensor(coordinator, "main", "humidity", mock_config_entry),
            VivosunThermoSensor(coordinator, "external", "temperature_c", mock_config_entry),
        ]

        unique_ids = [s._attr_unique_id for s in sensors]
        assert len(unique_ids) == len(set(unique_ids))  # All unique
