

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from . import DOMAIN

DATA_SCHEMA = vol.Schema({
    vol.Required("base_url"): str,
    vol.Required("app_id"): str,
    vol.Required("app_secret"): str,
    vol.Required("email"): str,
    vol.Required("password"): str,
    vol.Required("device_id"): str,
})

class DeyeCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Deye Cloud."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(f"deye_{user_input['device_id']}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Deye Cloud",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DeyeCloudOptionsFlow(config_entry)


class DeyeCloudOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )