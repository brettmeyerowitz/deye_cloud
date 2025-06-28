from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from .const import DOMAIN

def build_device_info(api, entry) -> dict:
    return {
        "identifiers": {(DOMAIN, api._device_sn)},
        "name": entry.data.get("device_name", f"Deye Inverter {api._device_sn}"),
        "manufacturer": "Deye",
        "model": "Inverter",
        "configuration_url": entry.data.get("base_url", "https://deyecloud.com"),
    }

def get_display_name(key: str) -> str:
    replacements = {
        "BMSSOC": "BMS SOC",
        "BMSDisChargeVoltage": "BMS Discharge Voltage",
        "UPSLoadPower": "UPS Load Power",
        "BMSChargeVoltage": "BMS Charge Voltage",
        "BMSCurrent": "BMS Current",
        "DCVoltagePV1": "DC Voltage PV1",
        "DCVoltagePV2": "DC Voltage PV2",
        "DCVoltagePV3": "DC Voltage PV3",
        "DCVoltagePV4": "DC Voltage PV4",
        "DCCurrentPV1": "DC Current PV1",
        "DCCurrentPV2": "DC Current PV2",
        "DCCurrentPV3": "DC Current PV3",
        "DCCurrentPV4": "DC Current PV4",
        "DCPowerPV1": "DC Power PV1",
        "DCPowerPV2": "DC Power PV2",
        "DCPowerPV3": "DC Power PV3",
        "DCPowerPV4": "DC Power PV4",
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

def get_sensor_attributes(unit: str, key: str) -> dict:
    safe_unit = unit.lower()
    key = key.lower()

    if safe_unit == "v":
        return {"device_class": SensorDeviceClass.VOLTAGE, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "a":
        return {"device_class": SensorDeviceClass.CURRENT, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "w":
        return {"device_class": SensorDeviceClass.POWER, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "kw":
        return {"device_class": SensorDeviceClass.POWER, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "kwh":
        if "total" in key or "daily" in key:
            return {"device_class": SensorDeviceClass.ENERGY, "native_unit_of_measurement": unit, "state_class": SensorStateClass.TOTAL_INCREASING}
        return {"device_class": SensorDeviceClass.ENERGY, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "hz":
        return {"device_class": SensorDeviceClass.FREQUENCY, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "%":
        return {"device_class": SensorDeviceClass.BATTERY, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}
    if safe_unit == "va":
        return {"device_class": SensorDeviceClass.APPARENT_POWER, "native_unit_of_measurement": unit, "state_class": SensorStateClass.MEASUREMENT}

    return {"native_unit_of_measurement": safe_unit, "state_class": SensorStateClass.MEASUREMENT}


