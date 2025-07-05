import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant import exceptions

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_DEVICE_SN,
    CONF_STATION_LABEL,
)

from .deye_api import DeyeCloudAPI

_LOGGER = logging.getLogger(__name__)

# Schema for initial user input: base URL, app credentials, and user login info
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_BASE_URL): TextSelector(TextSelectorConfig(type="text")),
    vol.Required(CONF_APP_ID): TextSelector(TextSelectorConfig(type="text")),
    vol.Required(CONF_APP_SECRET): TextSelector(TextSelectorConfig(type="text")),
    vol.Required(CONF_EMAIL): TextSelector(TextSelectorConfig(type="text")),
    vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type="text")),
})

class DeyeCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                # Initialize API with user credentials; device_sn will be set after inverter selection
                api = DeyeCloudAPI(
                    base_url=user_input[CONF_BASE_URL],
                    app_id=user_input[CONF_APP_ID],
                    app_secret=user_input[CONF_APP_SECRET],
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    device_sn=None  # Will be set after inverter selection
                )
                # Authenticate with the API
                await api.authenticate()
                _LOGGER.warning("✅ Deye authentication successful.")
                # Retrieve headers needed for further API calls
                headers = await api.get_headers()
                # URL to fetch list of stations with devices
                station_url = f"{user_input[CONF_BASE_URL]}/station/listWithDevice"
                # Make POST request to get station and device info
                async with api._session.post(
                    station_url, headers=headers, json={"page": 1, "size": 50}
                ) as resp:
                    result = await resp.json()

                inverters = []
                # Iterate over stations and devices to find inverters
                for station in result.get("stationList", []):
                    name = station.get("name", "Unknown")
                    for device in station.get("deviceListItems", []):
                        if device.get("deviceType") == "INVERTER":
                            label = f"{name} ({device['deviceSn']})"
                            inverters.append((device["deviceSn"], label))

                if not inverters:
                    # No inverters found, raise error to show form error
                    raise ValueError("No inverters found")

                # Store user input and inverter choices for next step
                self._user_input = user_input
                self._inverter_choices = inverters

                # Proceed to inverter selection step
                return await self.async_step_select_inverter()

            except Exception as e:
                _LOGGER.exception("❌ Authentication failed in config flow: %s", e)
                # Authentication or API call failed, show error on form
                errors["base"] = "auth_failed"

        # Show form for user to input credentials
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    async def async_step_select_inverter(self, user_input=None) -> FlowResult:
        """Handle the step where user selects an inverter device."""
        if user_input is not None:
            selected_sn = user_input[CONF_DEVICE_SN]
            label = dict(self._inverter_choices)[selected_sn]
            # Create the config entry with selected inverter info
            return self.async_create_entry(
                title=label,
                data={**self._user_input, CONF_DEVICE_SN: selected_sn, CONF_STATION_LABEL: label},
            )

        # Show form with inverter choices for user to select
        schema = vol.Schema({
            vol.Required(CONF_DEVICE_SN): vol.In(dict(self._inverter_choices)),
        })

        return self.async_show_form(step_id="select_inverter", data_schema=schema)

class DeyeCloudOptionsFlow(config_entries.OptionsFlow):
    """Options flow handler to update Deye Cloud credentials and device selection."""
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                # Create a temporary API client with updated input
                api = DeyeCloudAPI(
                    base_url=self.config_entry.data[CONF_BASE_URL],
                    app_id=user_input[CONF_APP_ID],
                    app_secret=user_input[CONF_APP_SECRET],
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    device_sn=None,
                )
                await api.authenticate()
                headers = await api.get_headers()
                station_url = f"{self.config_entry.data[CONF_BASE_URL]}/station/listWithDevice"
                async with api._session.post(
                    station_url, headers=headers, json={"page": 1, "size": 50}
                ) as resp:
                    result = await resp.json()

                valid_device_sns = {
                    device["deviceSn"]
                    for station in result.get("stationList", [])
                    for device in station.get("deviceListItems", [])
                    if device.get("deviceType") == "INVERTER"
                }

                # Get the current saved SN
                current_sn = self.config_entry.data.get(CONF_DEVICE_SN)
                updated_data = {
                    **self.config_entry.data,
                    CONF_APP_ID: user_input[CONF_APP_ID],
                    CONF_APP_SECRET: user_input[CONF_APP_SECRET],
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }

                if current_sn not in valid_device_sns:
                    updated_data.pop(CONF_DEVICE_SN, None)
                    updated_data.pop(CONF_STATION_LABEL, None)

                return self.async_create_entry(title="", data=updated_data)

            except Exception as e:
                _LOGGER.exception("❌ Options flow auth failed: %s", e)
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_APP_ID, default=self.config_entry.data.get(CONF_APP_ID, "")): str,
                vol.Required(CONF_APP_SECRET, default=self.config_entry.data.get(CONF_APP_SECRET, "")): str,
                vol.Required(CONF_EMAIL, default=self.config_entry.data.get(CONF_EMAIL, "")): str,
                vol.Required(CONF_PASSWORD, default=self.config_entry.data.get(CONF_PASSWORD, "")): str,
            }),
            errors=errors
        )

from homeassistant.config_entries import ConfigEntry
