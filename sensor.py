from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from . import DOMAIN
from .deye_api import DeyeCloudAPI

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)

def get_display_name(key: str) -> str:
    replacements = {
        "BMSSOC": "BMS SOC",
        "BMSDisChargeVoltage": "BMS Discharge Voltage",
        "UPSLoadPower": "UPS Load Power",
        "BMSChargeVoltage": "BMS Charge Voltage",
        "BMSCurrent": "BMS Current",
        "DCVoltagePV1": "DC Voltage PV1",
        "DCVoltagePV2": "DC Voltage PV2",
    }
    if key in replacements:
        return replacements[key]

    import re
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
    name = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", name)
    name = name.replace("Pv", "PV").replace("pv", "PV")
    return name.strip()

def get_sensor_metadata(key: str) -> tuple[str | None, str | None, str | None]:
    key = key.lower()
    if "voltage" in key:
        return ("voltage", "V", "measurement")
    if "current" in key:
        return ("current", "A", "measurement")
    elif "power" in key or "load" in key:
        return "power", "W", "measurement"
    elif "temperature" in key:
        return "temperature", "°C", "measurement"
    elif "energy" in key:
        return "energy", "Wh", "total_increasing"
    elif "soc" in key or "capacity" in key:
        return "battery", "%", "measurement"
    elif "frequency" in key:
        return ("frequency", "Hz", "measurement")
    return (None, None, None)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    api: DeyeCloudAPI = hass.data[DOMAIN][entry.entry_id]

    coordinator = DeyeDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    device_info = DeviceInfo(
        identifiers={(DOMAIN, api._device_id)},
        name=f"Deye Inverter ({api._device_id})",
        manufacturer="Deye",
        model="Hybrid Inverter",
    )

    sensors: list[SensorEntity] = []
    
    _LOGGER.info("Setting up Deye realtime sensors")
    for key in coordinator.data:
        if key is not None:
            sensors.append(DeyeRealtimeSensor(coordinator, key, device_info))

    try:
        tou_data = await api.get_time_of_use()
        for idx, slot in enumerate(tou_data, start=1):
            for key in slot:
                sensors.append(DeyeTOUSensor(slot, key, idx, device_info))
    except Exception as e:
        _LOGGER.warning(f"TOU data could not be fetched: {e}")

    async_add_entities(sensors)


class DeyeDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: DeyeCloudAPI):
        super().__init__(
            hass,
            _LOGGER,
            name="Deye Cloud Coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self):
        try:
            data_list = await self.api.get_realtime_data()
            return {entry["key"]: entry["value"] for entry in data_list}
        except Exception as e:
            _LOGGER.error(f"Failed to fetch real-time data: {e}")
            return {}


class DeyeRealtimeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DeyeDataCoordinator, key: str, device_info: dict):
        super().__init__(coordinator)
        safe_key = key if isinstance(key, str) else "unknown"
        self._key = key
        self._attr_unique_id = f"deye_{safe_key.lower()}"
        self._attr_name = f"Deye {get_display_name(safe_key)}"
        self._attr_device_info = device_info
        device_class, unit, state_class = get_sensor_metadata(safe_key)
        self._attr_device_class = device_class
        self._attr_unit_of_measurement = unit
        self._attr_state_class = state_class

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class DeyeTOUSensor(SensorEntity):
    def __init__(self, slot_data: dict, key: str, index: int, device_info: dict):
        self._slot_data = slot_data
        self._key = key
        self._index = index
        self._attr_unique_id = f"deye_prog{index}_{key.lower()}"
        self._attr_name = f"Deye prog{index}_{key}"
        self._attr_device_info = device_info

    @property
    def native_value(self):
        return self._slot_data.get(self._key)