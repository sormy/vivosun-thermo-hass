from logging import getLogger

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import ATTR_NAME

from .const import ATTR_ADDRESS, DEVICE_TYPES, DOMAIN

_LOGGER = getLogger(__name__)


class VivosunThermoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    STEP_CONFIRM = "confirm"

    def __init__(self):
        self.setup_address: str
        self.setup_name: str

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        _LOGGER.debug(f"Discovered {discovery_info.name} with address {discovery_info.address}")

        # Ensure unique configuration
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Store discovery info for later use
        self.setup_address = discovery_info.address
        self.setup_name = DEVICE_TYPES.get(discovery_info.name, {}).get("name", discovery_info.name)

        # Ask the user whether to set up the device
        return self.async_show_form(
            step_id=self.STEP_CONFIRM,
            description_placeholders={ATTR_NAME: self.setup_name},
            data_schema=None,
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        _LOGGER.debug("Attempt to manually add integration")
        return self.async_abort(reason="Manual configuration is not supported")

    async def async_step_confirm(self, user_input=None) -> ConfigFlowResult:
        _LOGGER.debug("Confirming device setup")

        if user_input is None:
            # Redisplay the form if the user hasn't confirmed yet
            return self.async_show_form(
                step_id=self.STEP_CONFIRM,
                description_placeholders={ATTR_NAME: self.setup_name},
                data_schema=None,
            )

        # Create the config entry
        return self.async_create_entry(
            title=self.setup_name,
            data={
                ATTR_NAME: self.setup_name,
                ATTR_ADDRESS: self.setup_address,
            },
        )
