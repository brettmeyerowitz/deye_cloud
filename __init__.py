DOMAIN = "deye_cloud"

PLATFORMS = ["sensor"]

import logging
_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .deye_api import DeyeCloudAPI

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = DeyeCloudAPI(
        base_url=entry.data["base_url"],
        app_id=entry.data["app_id"],
        app_secret=entry.data["app_secret"],
        email=entry.data["email"],
        password=entry.data["password"],
        device_sn=entry.data["device_sn"]
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
