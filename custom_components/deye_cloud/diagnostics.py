

"""Diagnostics support for Deye Cloud integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    if not data:
        return {"error": "No data found for config entry"}

    api = data.get("api")
    coordinator = data.get("coordinator")

    result = {
        "config_entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "device_sn": getattr(api, "_device_sn", None),
        "coordinator_data": coordinator.data if coordinator else None,
    }

    return result