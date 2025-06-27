from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

DOMAIN = "deye_cloud"
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

def get_sensor_attributes(key: str) -> dict:
    key_lower = key.lower()
    if "voltage" in key_lower:
        return {"device_class": "voltage", "unit_of_measurement": "V", "state_class": "measurement"}
    if "current" in key_lower:
        return {"device_class": "current", "unit_of_measurement": "A", "state_class": "measurement"}
    if "power" in key_lower:
        return {"device_class": "power", "unit_of_measurement": "W", "state_class": "measurement"}
    if "energy" in key_lower or "kwh" in key_lower:
        return {"device_class": "energy", "unit_of_measurement": "kWh", "state_class": "total_increasing"}
    if "temperature" in key_lower:
        return {"device_class": "temperature", "unit_of_measurement": "°C", "state_class": "measurement"}
    if "frequency" in key_lower:
        return {"device_class": "frequency", "unit_of_measurement": "Hz", "state_class": "measurement"}
    if "soc" in key_lower or "capacity" in key_lower:
        return {"unit_of_measurement": "%", "state_class": "measurement"}
    return {"state_class": "measurement"}

TOU_KEY_NAME_MAP = {
    "power": "Power",
    "voltage": "Voltage",
    "enableGridCharge": "Grid Charge",
    "enableGeneration": "Generation",
    "soc": "Battery",
    "time": "Start Time",
}

def get_tou_sensor_attributes(key: str) -> dict:
    key_lower = key.lower()
    if key_lower == "voltage":
        return {"device_class": "voltage", "unit_of_measurement": "V", "state_class": "measurement"}
    if key_lower == "power":
        return {"device_class": "power", "unit_of_measurement": "W", "state_class": "measurement"}
    if key_lower == "soc":
        return {"unit_of_measurement": "%", "state_class": "measurement"}
    if key_lower in ["enablegridcharge", "enablegeneration"]:
        return {"device_class": "enum", "options": ["Enabled", "Disabled"]}
    if key_lower == "time":
        return {"unit_of_measurement": None, "state_class": None} # remove device_class to treat it as plain text
    return {}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    api: DeyeCloudAPI = hass.data[DOMAIN][entry.entry_id]

    coordinator = DeyeDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    sensors: list[SensorEntity] = []

    device_info = {
        "identifiers": {(DOMAIN, api._device_sn)},
        "name": f"Deye Inverter {api._device_sn}",
        "manufacturer": "Deye",
        "model": "Inverter",
        "configuration_url": "https://deyecloud.com",
    }

    _LOGGER.info("Setting up Deye realtime sensors")
    for key, value in coordinator.data.items():
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
        self._attr_name = get_display_name(safe_key)
        self._attr_device_info = device_info

        sensor_attrs = get_sensor_attributes(safe_key)
        for attr_name, attr_value in sensor_attrs.items():
            setattr(self, f"_attr_{attr_name}", attr_value)

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

class DeyeTOUSensor(SensorEntity):
    def __init__(self, slot_data: dict, key: str, index: int, device_info: dict):
        self._slot_data = slot_data
        self._key = key
        self._index = index
        self._attr_unique_id = f"deye_prog{index}_{key.lower()}"

        display_names = {
            "enableGridCharge": "Grid Charge",
            "enableGeneration": "Generation",
            "soc": "Battery",
            "power": "Power",
            "voltage": "Voltage",
            "time": "Time"
        }

        pretty_key = display_names.get(key, key)
        self._attr_name = f"Program {index} {pretty_key}"
        self._attr_device_info = device_info

        sensor_attrs = get_tou_sensor_attributes(key)
        for attr_name, attr_value in sensor_attrs.items():
            setattr(self, f"_attr_{attr_name}", attr_value)

    @property
    def native_value(self):
        val = self._slot_data.get(self._key)

        if self._key in ["enableGridCharge", "enableGeneration"]:
            return "Enabled" if val else "Disabled"

        if self._key.lower() == "time":
            raw_time = self._slot_data.get(self._key)
            if isinstance(raw_time, str) and len(raw_time) == 4:
                return f"{raw_time[:2]}:{raw_time[2:]}"
            return self._slot_data.get(self._key)

        return val
