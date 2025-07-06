from __future__ import annotations

import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN
from .helpers import build_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    toucoordinator = data["toucoordinator"]
    api = data["api"]

    tou_data = toucoordinator.data
    if not tou_data:
        _LOGGER.warning("TOU Coordinator returned no data during setup")
        await toucoordinator.async_config_entry_first_refresh()

    tou_data = toucoordinator.data
    if not isinstance(tou_data, list):
        tou_data = []

    entities = []
    options = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

    for i, program in enumerate(tou_data):
        entities.append(DeyeTOUTimeSelect(toucoordinator, api, entry, i, program, options))

    async_add_entities(entities)

class DeyeTOUTimeSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, api, entry, index, program, options):
        super().__init__(coordinator)
        from .helpers import build_device_info
        self.api = api
        self.index = index
        self._attr_name = f"Prog {index+1} Time"
        self._attr_unique_id = f"deye_{entry.data['device_sn']}_tou_{index+1}_time"
        self._attr_options = options
        self._attr_icon = "mdi:clock"
        self._attr_device_info = build_device_info(api, entry)
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        try:
            raw = self.coordinator.data[self.index].get("time")
            if raw and len(raw) == 4 and raw.isdigit():
                return f"{raw[:2]}:{raw[2:]}"
            return None
        except Exception as e:
            _LOGGER.warning(f"Unable to get current TOU time option: {e}")
            return None

    async def async_select_option(self, option: str) -> None:
        try:
            formatted = option.replace(":", "")
            tou_config = await self.api.get_time_of_use()
            tou_config[self.index]["time"] = formatted
            await self.api.update_time_of_use(tou_config)
            await self.coordinator.async_request_refresh()
            self._attr_current_option = option
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Failed to set TOU time: {e}")