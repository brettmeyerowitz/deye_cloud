import json
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SWITCH_TYPES = {
    "enableGridCharge": "Grid Charge",
    "enableGeneration": "Generation",
}

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["toucoordinator"]
    api = data["api"]

    if not coordinator.data:
        _LOGGER.warning("Coordinator returned no data during setup")
        await coordinator.async_config_entry_first_refresh()
    
    tou_data = coordinator.data
    if not isinstance(tou_data, list):
        tou_data = []

    switches = []
    for index, program in enumerate(tou_data):
        switches.append(DeyeTOUSwitch(coordinator, api, index, "enableGridCharge", program, entry.data["device_sn"]))
        switches.append(DeyeTOUSwitch(coordinator, api, index, "enableGeneration", program, entry.data["device_sn"]))

    async_add_entities(switches)

class DeyeTOUSwitch(SwitchEntity):
    def __init__(self, coordinator, api, slot_index, key, program, device_sn):
        self._index_string  = str(slot_index + 1)

        self._attr_name = f"Time {self._index_string} {SWITCH_TYPES[key]}"
        self._attr_unique_id = f"{device_sn}_tou_{self._index_string}_{key}"

        self._key = key
        self._slot_index = slot_index
        self._attr_icon = "mdi:toggle-switch"
        self._api = api
        self._coordinator = coordinator
        self._attr_native_value = program[key] if key in program else None

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_sn)},
            "name": f"Deye Inverter ({device_sn})",
            "manufacturer": "Deye"
        }

    @property
    def is_on(self):
        try:
            value = self._coordinator.data[self._slot_index][self._key]
            return value if value is not None else False
        except Exception as e:
            _LOGGER.error(f"Failed to determine state of {self._attr_name}: {e}")
            return False

    async def async_turn_on(self, **kwargs):
        await self._update_switch_value(True)

    async def async_turn_off(self, **kwargs):
        await self._update_switch_value(False)

    async def _update_switch_value(self, new_value):
        tou_config = await self._api.get_time_of_use()
        tou_config[self._slot_index][self._key] = new_value
        await self._api.update_time_of_use(tou_config)
        await self._coordinator.async_request_refresh()
        self._attr_native_value = new_value
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self._coordinator.async_add_listener(self.async_write_ha_state)