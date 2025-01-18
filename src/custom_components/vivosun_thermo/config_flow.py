from logging import getLogger

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import ATTR_NAME

from .const import ATTR_ADDRESS, DEVICE_TYPES, DOMAIN

_LOGGER = getLogger(__name__)


class VivosunThermoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        _LOGGER.debug(f"Discovered {discovery_info.name} with address {discovery_info.address}")

        await self.async_set_unique_id(discovery_info.address)

        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=DEVICE_TYPES.get(discovery_info.name, {}).get("name", discovery_info.name),
            data={ATTR_NAME: discovery_info.name, ATTR_ADDRESS: discovery_info.address},
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        _LOGGER.debug("Attempt to manually add integration")
        return self.async_abort(reason="Manual configuration is not supported")
