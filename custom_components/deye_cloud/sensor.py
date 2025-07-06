from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity

DOMAIN = "deye_cloud"
from .deye_api import DeyeCloudAPI

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)

class DeyeDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: DeyeCloudAPI):
        super().__init__(hass, _LOGGER, name="Deye Cloud Coordinator", update_interval=SCAN_INTERVAL)
        self.api = api

    async def _async_update_data(self):
        try:
            data_list = await self.api.get_realtime_data()
            return data_list
        except Exception as e:
            _LOGGER.error(f"Failed to fetch real-time data: {e}")
            return []

class DeyeRealtimeSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    def __init__(self, coordinator, api, entry, key, unit):
        super().__init__(coordinator)

        from .helpers import (build_device_info, get_display_name, get_sensor_attributes)

        self._key = key
        self._unit = unit

        self._attr_name = get_display_name(key)
        self._attr_unique_id = f"deye_{entry.data['device_sn']}_{key.lower()}"

        self._attr_device_info = build_device_info(api, entry)

        sensor_attrs = get_sensor_attributes(unit, key)
        for attr_name, attr_value in sensor_attrs.items():
            setattr(self, f"_attr_{attr_name}", attr_value)

    @property
    def native_value(self):
        for item in self.coordinator.data:
            if item.get("key") == self._key:
                return item.get("value")
        return None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.coordinator.data:
            return
        old_state = await self.async_get_last_state()
        if old_state and old_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = old_state.state

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
    
async def async_setup_entry(
    hass: HomeAssistant,
    entry : ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: DeyeCloudAPI = data["api"]
    coordinator = data["coordinator"]

    sensors: list[SensorEntity] = []

    _LOGGER.info("Setting up Deye realtime sensors")
    if not coordinator.data:
        _LOGGER.warning("Coordinator returned no data during setup")
        return
    for sensor in coordinator.data:
        key = sensor.get("key")
        unit = sensor.get("unit")
        if key is not None:
            sensors.append(DeyeRealtimeSensor(coordinator, api, entry, key, unit))

    async_add_entities(sensors)    