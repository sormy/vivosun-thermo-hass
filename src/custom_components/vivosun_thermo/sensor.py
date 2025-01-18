from datetime import date, datetime
from decimal import Decimal
from typing import override

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, PROBE_TYPES, SENSOR_TYPES
from .coordinator import VivosunThermoSensorCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VivosunThermoSensorCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        VivosunThermoSensor(coordinator, probe_type, sensor_type, entry)
        for sensor_type in SENSOR_TYPES
        for probe_type in PROBE_TYPES
        if coordinator.data.get(probe_type) is not None
    ]

    async_add_entities(entities)


class VivosunThermoSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: VivosunThermoSensorCoordinator,
        probe_type: str,
        sensor_type: str,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)

        self.probe_type: str = probe_type
        self.sensor_type: str = sensor_type

        sensor_info = SENSOR_TYPES[sensor_type]
        device_info = DEVICE_TYPES.get(coordinator.discovery_info.name, {})

        device_name = device_info.get("name", coordinator.discovery_info.name)
        device_manufacturer = device_info.get("manufacturer")
        device_model = device_info.get("model")

        self._attr_name = f"{coordinator.name} {probe_type.capitalize()} {sensor_info['name']}"
        self._attr_icon = sensor_info["icon"]
        self._attr_device_class = sensor_info["device_class"]
        self._attr_state_class = sensor_info["state_class"]
        self._attr_entity_category = sensor_info["entity_category"]
        self._attr_native_unit_of_measurement = sensor_info["native_unit_of_measurement"]
        self._attr_suggested_display_precision = sensor_info["precision"]
        self._attr_unique_id = f"{coordinator.discovery_info.name}-{coordinator.discovery_info.address}-{probe_type}-{sensor_type}"
        self._attr_should_poll = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.discovery_info.address)},
            name=device_name,
            manufacturer=device_manufacturer,
            model=device_model,
        )

    @property
    @override
    def native_value(self) -> StateType | date | datetime | Decimal:  # type: ignore
        probe_data = self.coordinator.data.get(self.probe_type, {})
        return probe_data.get(self.sensor_type)

    @property
    @override
    def available(self) -> bool:  # type: ignore
        return self.coordinator.data.get(self.probe_type) is not None
