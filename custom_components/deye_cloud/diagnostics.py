

"""Diagnostics support for Deye Cloud integration."""
from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import DeviceEntry

from .const import CONF_APP_ID, CONF_APP_SECRET, CONF_EMAIL, CONF_PASSWORD, DOMAIN

TO_REDACT = {CONF_APP_ID, CONF_APP_SECRET, CONF_EMAIL, CONF_PASSWORD}

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
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "device_sn": getattr(api, "_device_sn", None),
        "coordinator_data": coordinator.data if coordinator else None,
    }

    return result