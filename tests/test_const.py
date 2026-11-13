"""The lookup tables must agree with the shape the coordinator decodes."""

from custom_components.vivosun_thermo.const import (
    BATTERY_VOLTAGE_SENSOR,
    PROBE_TYPES,
    SENSOR_TYPES,
)
from custom_components.vivosun_thermo.coordinator import ProbeData, SensorData


class TestTablesMatchDecodedShape:
    """Entities are built from the tables but read from the decoded data."""

    def test_sensor_types_cover_probe_readings(self):
        """A description whose key is not decoded would KeyError on every state read."""
        assert {d.key for d in SENSOR_TYPES} == set(ProbeData.__annotations__)

    def test_probe_types_cover_decoded_probes(self):
        """A probe absent from the table gets no entities; an unknown one gets dead ones."""
        device_readings = {BATTERY_VOLTAGE_SENSOR.key}
        assert set(PROBE_TYPES) == set(SensorData.__annotations__) - device_readings

    def test_battery_sensor_key_is_decoded(self):
        """The battery sensor reads its key straight from the decoded data."""
        assert BATTERY_VOLTAGE_SENSOR.key in SensorData.__annotations__

    def test_sensor_type_keys_are_unique(self):
        """Duplicate keys would build two entities sharing a unique_id."""
        keys = [d.key for d in SENSOR_TYPES]
        assert len(keys) == len(set(keys))
