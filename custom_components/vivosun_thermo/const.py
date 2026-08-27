from datetime import timedelta
from typing import Final, TypedDict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature

DOMAIN: Final = "vivosun_thermo"

DEVICE_TYPES: Final = {
    "ThermoBeacon2": {
        "name": "VIVOSUN AeroLab THB1S",
        "manufacturer": "VIVOSUN",
        "model": "THB1S",
    }
}

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

PROBE_TYPES: Final = ("main", "external")

SENSOR_TYPES: Final = (
    SensorEntityDescription(
        key="temperature_c",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="vpd",
        name="Vapor Pressure Deficit",
        native_unit_of_measurement="kPa",
        icon="mdi:air-filter",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
    ),
)


class ConfigEntryData(TypedDict):
    name: str
    discovery_name: str
    discovery_address: str
