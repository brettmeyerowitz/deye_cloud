from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN

class DeyeTOUBatteryNumber(NumberEntity):
    def __init__(self, coordinator, api, slot_index, initial_soc, device_sn):
        self._index_string  = str(slot_index + 1)

        self._attr_name = f"Time {self._index_string} Battery"
        self._attr_unique_id = f"{device_sn}_tou_{self._index_string}_soc"

        self._attr_native_min_value = 1
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_value = initial_soc
        self._coordinator = coordinator
        self._api = api
        self._slot_index = slot_index
        self._device_sn = device_sn
        self._attr_should_poll = False
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_sn)},
            "name": f"Deye Inverter ({device_sn})",
            "manufacturer": "Deye"
        }

    async def async_set_native_value(self, value: float):
        tou_config = await self._api.get_time_of_use()
        tou_config[self._slot_index]["soc"] = int(value)
        await self._api.update_time_of_use(tou_config)
        self._attr_native_value = int(value)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self._coordinator.async_add_listener(self.async_write_ha_state)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    await coordinator.async_config_entry_first_refresh()
    tou_data = await api.get_time_of_use()
    if not isinstance(tou_data, list):
        tou_data = []

    controls = []
    for index, program in enumerate(tou_data):
        controls.append(DeyeTOUBatteryNumber(coordinator, api, index, program["soc"], entry.data["device_sn"]))

    async_add_entities(controls)