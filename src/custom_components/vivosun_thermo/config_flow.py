from logging import getLogger

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import ATTR_NAME

from .const import ATTR_DISCOVERY_INFO, DEVICE_TYPES, DOMAIN

_LOGGER = getLogger(__name__)


class VivosunThermoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.name: str
        self.discovery_info: BluetoothServiceInfoBleak

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        _LOGGER.debug(f"Discovered {discovery_info.name} with address {discovery_info.address}")

        # Ensure unique configuration
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Store discovery info for later use
        self.name = DEVICE_TYPES.get(discovery_info.name, {}).get("name", discovery_info.name)

        # Ask the user whether to set up the device
        return self.async_show_confirm()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        _LOGGER.debug("Attempt to manually add integration")
        return self.async_abort(reason="not_supported")

    async def async_step_confirm(self, user_input=None) -> ConfigFlowResult:
        _LOGGER.debug(f"Confirming setup {self.name} with user input {user_input}")

        # Redisplay the form if the user hasn't confirmed yet
        if user_input is None:
            return self.async_show_confirm()

        # Create the config entry using user-provided name
        return self.async_create_entry(
            title=self.name,
            data={
                ATTR_NAME: user_input[ATTR_NAME],
                ATTR_DISCOVERY_INFO: self.discovery_info,
            },
        )

    def async_show_confirm(self) -> ConfigFlowResult:
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={ATTR_NAME: self.name},
            data_schema=vol.Schema({vol.Optional(ATTR_NAME, default=self.name): str}),
        )
