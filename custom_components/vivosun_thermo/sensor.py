from datetime import date, datetime
from decimal import Decimal
from typing import override

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VivosunThermoConfigEntry
from .const import BATTERY_VOLTAGE_SENSOR, DEVICE_TYPES, DOMAIN, PROBE_TYPES, SENSOR_TYPES
from .coordinator import ProbeData, VivosunThermoSensorCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VivosunThermoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        VivosunThermoSensor(coordinator, probe_type, description)
        for description in SENSOR_TYPES
        for probe_type in PROBE_TYPES
        if coordinator.data.get(probe_type) is not None
    ]
    if coordinator.data.get("battery_voltage") is not None:
        entities.append(VivosunThermoBatterySensor(coordinator))
    async_add_entities(entities)


def _device_info(coordinator: VivosunThermoSensorCoordinator) -> DeviceInfo:
    device_type = DEVICE_TYPES.get(coordinator.discovery_name, {})
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.discovery_address)},
        name=coordinator.name,
        manufacturer=device_type.get("manufacturer"),
        model=device_type.get("model"),
    )


class VivosunThermoSensor(CoordinatorEntity[VivosunThermoSensorCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: VivosunThermoSensorCoordinator,
        probe_type: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)

        self.entity_description = description
        self.probe_type = probe_type
        self.sensor_type = description.key

        self._attr_name = f"{probe_type.capitalize()} {description.name}"
        self._attr_unique_id = (
            f"{coordinator.discovery_name}-{coordinator.discovery_address}"
            f"-{probe_type}-{description.key}"
        )
        self._attr_device_info = _device_info(coordinator)

    def _probe_data(self) -> ProbeData | None:
        return self.coordinator.data.get(self.probe_type)

    @property
    @override
    def native_value(self) -> StateType | date | datetime | Decimal:
        probe_data = self._probe_data()
        return probe_data[self.sensor_type] if probe_data is not None else None

    @property
    @override
    def available(self) -> bool:
        return super().available and self._probe_data() is not None


class VivosunThermoBatterySensor(CoordinatorEntity[VivosunThermoSensorCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: VivosunThermoSensorCoordinator) -> None:
        super().__init__(coordinator)

        self.entity_description = BATTERY_VOLTAGE_SENSOR
        self._attr_unique_id = (
            f"{coordinator.discovery_name}-{coordinator.discovery_address}"
            f"-{BATTERY_VOLTAGE_SENSOR.key}"
        )
        self._attr_device_info = _device_info(coordinator)

    @property
    @override
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.coordinator.data.get("battery_voltage")

    @property
    @override
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("battery_voltage") is not None
