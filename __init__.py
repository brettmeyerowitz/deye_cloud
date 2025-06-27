
import logging
_LOGGER = logging.getLogger(__name__)


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .deye_api import DeyeCloudAPI

DOMAIN = "deye_cloud"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Deye Cloud integration from configuration.yaml."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Deye Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # In a full config flow, these would be extracted from entry.data
    config = entry.data
    api = DeyeCloudAPI(
        base_url=config["base_url"],
        app_id=config["app_id"],
        app_secret=config["app_secret"],
        email=config["email"],
        password=config["password"],
        device_id=config["device_id"]
    )

    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    _LOGGER.info("Deye Cloud integration successfully set up with device ID: %s", config["device_id"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True