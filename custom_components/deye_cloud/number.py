from __future__ import annotations
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.number import NumberDeviceClass

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DeyeTOUBatteryNumber(NumberEntity):
    def __init__(self, coordinator, api, slot_index, program, entry):
        from .helpers import build_device_info

        self._key = "soc"

        self._index_string  = str(slot_index + 1)
        self._coordinator = coordinator
        self._api = api
        self._slot_index = slot_index
        self._device_sn = entry.data["device_sn"]

        self._attr_name = f"Prog {self._index_string} Battery"
        self._attr_unique_id = f"deye_{entry.data["device_sn"]}_tou_{self._index_string}_{self._key}"

        self._attr_device_class = NumberDeviceClass.BATTERY

        self._attr_should_poll = False

        self._attr_native_value = program[self._key] if self._key in program else None
        self._attr_native_min_value = 1
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = PERCENTAGE

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = build_device_info(api, entry)
        self._attr_extra_state_attributes = {
            "time": program["time"]
        }

    async def async_set_native_value(self, value: float):
        tou_config = await self._api.get_time_of_use()
        tou_config[self._slot_index][self._key] = int(value)
        await self._api.update_time_of_use(tou_config)
        self._attr_native_value = int(value)
        await self._coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._coordinator.async_remove_listener(self.async_write_ha_state)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["toucoordinator"]
    api = data["api"]

    tou_data = coordinator.data
    if not tou_data:
        _LOGGER.warning("Coordinator returned no data during setup")
        await coordinator.async_config_entry_first_refresh()

    tou_data = coordinator.data
    if not isinstance(tou_data, list):
        tou_data = []

    controls = []
    for index, program in enumerate(tou_data):
        controls.append(DeyeTOUBatteryNumber(coordinator, api, index, program, entry))

    async_add_entities(controls)