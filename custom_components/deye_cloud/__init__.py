from .const import DOMAIN

PLATFORMS = ["sensor", "number", "switch"]

import logging
_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .deye_api import DeyeCloudAPI
from homeassistant.helpers.storage import Store

async def async_get_options_flow(config_entry: ConfigEntry):
    from .config_flow import DeyeCloudOptionsFlow
    return DeyeCloudOptionsFlow(config_entry)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = DeyeCloudAPI(
        base_url=entry.data["base_url"],
        app_id=entry.data["app_id"],
        app_secret=entry.data["app_secret"],
        email=entry.data["email"],
        password=entry.data["password"],
        device_sn=entry.data["device_sn"]
    )

    _LOGGER.debug(
        "Initialized DeyeCloudAPI with device_sn=%s for station %s",
        entry.data["device_sn"],
        entry.title
    )

    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    # Create a dummy coordinator if not already done
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=api.get_realtime_data,
        update_interval=None,  # could set a default interval here
    )

    toucoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=api.get_time_of_use,
        update_interval=None,  # could set a default interval here
    )

    # Perform the first data refresh to populate coordinator.data
    await coordinator.async_config_entry_first_refresh()
    await toucoordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "toucoordinator": toucoordinator
    }

    # Save config to storage
    store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}.json")
    await store.async_save({
        "base_url": entry.data["base_url"],
        "app_id": entry.data["app_id"],
        "app_secret": entry.data["app_secret"],
        "email": entry.data["email"],
        "password": entry.data["password"],
        "device_sn": entry.data["device_sn"],
        "station_name": entry.title
    })

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok