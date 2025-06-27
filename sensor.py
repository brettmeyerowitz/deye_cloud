from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

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
        "ExternalCT1Power": "External CT1 Power",
        "ExternalCT2Power": "External CT2 Power",
        "ExternalCT3Power": "External CT3 Power"
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

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: DeyeCloudAPI = data["api"]
    coordinator = data["coordinator"]

    sensors: list[SensorEntity] = []

    device_info = {
        "identifiers": {(DOMAIN, api._device_sn)},
        "name": entry.data.get("device_name", f"Deye Inverter {api._device_sn}"),
        "manufacturer": "Deye",
        "model": "Inverter",
        "configuration_url": entry.data.get("base_url", "https://deyecloud.com"),
    }

    _LOGGER.info("Setting up Deye realtime sensors")
    if not coordinator.data:
        _LOGGER.warning("Coordinator returned no data during setup")
        return
    for entry in coordinator.data:
        key = entry.get("key")
        if key is not None:
            sensors.append(DeyeRealtimeSensor(coordinator, key, device_info))

    async_add_entities(sensors)

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
        for item in self.coordinator.data:
            if item.get("key") == self._key:
                return item.get("value")
        return None