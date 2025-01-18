from datetime import timedelta
from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature, EntityCategory

ATTR_DISCOVERY_INFO: Final = "discovery_info"

DOMAIN: Final = "vivosun_thermo"

DEVICE_TYPES: Final = {
    "ThermoBeacon2": {
        "name": "VIVOSUN AeroLab THB1S",
        "manufacturer": "VIVOSUN",
        "model": "THB1S",
    }
}

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

PROBE_TYPE_MAIN = "main"
PROBE_TYPE_EXTERNAL = "external"

PROBE_TYPES = ["main", "external"]

SENSOR_TYPE_TEMPERATURE = "temperature_c"
SENSOR_TYPE_HUMIDITY = "humidity"
SENSOR_TYPE_VPD = "vpd"

SENSOR_TYPES = {
    "temperature_c": {
        "name": "Temperature",
        "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_category": None,
        "precision": 1,  # 0.1
    },
    "humidity": {
        "name": "Humidity",
        "native_unit_of_measurement": PERCENTAGE,
        "icon": "mdi:water-percent",
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_category": None,
        "precision": 0,  # 1
    },
    "vpd": {
        "name": "Vapor Pressure Deficit",
        "native_unit_of_measurement": "kPa",
        "icon": "mdi:air-filter",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_category": EntityCategory.DIAGNOSTIC,
        "precision": 2,  # 0.01
    },
}
