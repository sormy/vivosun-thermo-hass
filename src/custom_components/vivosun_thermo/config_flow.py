from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import ATTR_NAME

from .const import DEVICE_TYPES, DOMAIN


class VivosunThermoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        if discovery_info.name in DEVICE_TYPES:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=discovery_info.name,
            data={ATTR_NAME: discovery_info.name},
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        return self.async_abort(reason="not_supported")
