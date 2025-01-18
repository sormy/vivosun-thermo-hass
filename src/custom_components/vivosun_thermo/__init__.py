from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, ATTR_NAME
from homeassistant.core import HomeAssistant

from .const import ATTR_DISCOVERY_INFO, DOMAIN
from .coordinator import VivosunThermoSensorCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = VivosunThermoSensorCoordinator(
        hass, entry.data[ATTR_NAME], entry.data[ATTR_DISCOVERY_INFO]
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
    if unloaded:
        del hass.data[DOMAIN][entry.entry_id]
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
    return unloaded
