from .const import DOMAIN

PLATFORMS = ["sensor", "number", "switch", "select"]

import logging
_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .deye_api import DeyeCloudAPI
from homeassistant.helpers.storage import Store
from datetime import timedelta

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
        update_interval=timedelta(seconds=60),
    )

    toucoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=api.get_time_of_use,
        update_interval=timedelta(seconds=60),
    )

    # Perform the first data refresh to populate coordinator.data
    try:
        await coordinator.async_config_entry_first_refresh()
        await toucoordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.exception("Initial data refresh failed: %s", e)
        return False

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

    # Register the refresh_data service only once for all instances
    if not hass.services.has_service(DOMAIN, "refresh_data"):
        async def handle_refresh_service(call):
            """Handle manual refresh service call for all configured entries."""
            for instance in hass.data.get(DOMAIN, {}).values():
                await instance["coordinator"].async_request_refresh()
                await instance["toucoordinator"].async_request_refresh()
            _LOGGER.info("Manual refresh_data service triggered for all entries")

        hass.services.async_register(
            DOMAIN,
            "refresh_data",
            handle_refresh_service
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "refresh_data")
    return unload_ok

# Support config entry reloads
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)