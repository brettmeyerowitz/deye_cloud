# Deye Cloud Integration for Home Assistant

![HACS Custom Component](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)

## Overview

The **Deye Cloud** integration connects Home Assistant to Deye solar inverters via their official cloud API. This integration allows you to monitor your solar generation, consumption, and inverter status directly from Home Assistant — with no need to connect via Modbus or local networks.

This is a **custom integration** and is currently distributed through [HACS (Home Assistant Community Store)](https://hacs.xyz).

## Features

- ☀️ Real-time solar power generation
- 🔋 Battery state of charge, current, and voltage
- ⚡ Grid feed-in / draw metrics
- 📈 Daily, monthly, and lifetime statistics
- 🧠 Dynamically discovers and creates sensors for all datapoints from the `/device/latest` API
- ✨ Human-readable sensor names and proper units, classes, and state types
- 🔔 Fault and warning status sensors
- ⏱️ Time-of-Use program control and battery setpoint support
- 🧠 Uses `DataUpdateCoordinator` for efficient polling
- 🔧 Frontend reconfiguration via options flow (no need to remove and re-add)

## Installation

### Easy Installation via HACS

You can quickly add this repository to HACS by clicking the button below:

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=brettmeyerowitz&repository=deye_cloud&category=integration)

### 1. Add Custom Repository

1. Open Home Assistant
2. Go to **HACS > Integrations**
3. Click the three-dot menu (top right) and choose **Custom repositories**
4. Add this repo:  
   ```
   https://github.com/brettmeyerowitz/deye_cloud
   ```
   Select category: **Integration**

### 2. Install

- After adding the repo, search for **Deye Cloud** under HACS > Integrations
- Click **Install**

### 3. Restart Home Assistant

Restart is required to load the new or updated integration.


## Configuration

After installation:

1. Go to **Settings > Devices & Services**
2. Click **Add Integration** and search for **Deye Cloud**
3. Enter the following required fields:

   - **Base URL** – Use the Deye developer API endpoint for your region (see table below)
   - **App ID** – Retrieved from your Deye Developer account
   - **App Secret** – Retrieved from your Deye Developer account
   - **Email** – Your Deye Cloud login email
   - **Password** – Your Deye Cloud login password
4. Select your inverter device from the list presented after login.

### Get Your Deye Developer Credentials (Required)

Before using this integration, you must register a DeyeCloud developer account and create an application to obtain your App ID and App Secret.

#### Step-by-step:

1. Go to [https://developer.deyecloud.com](https://developer.deyecloud.com)
2. Create a free developer account.
   - During registration, choose the appropriate **data center**:
     - **Europe, Africa, Asia-Pacific**: select **EU**, base URL will be `https://eu1-developer.deyecloud.com`
     - **North/South America**: select **US**, base URL will be `https://us1-developer.deyecloud.com`
3. After logging in, navigate to **Cloud Development > Create Application**
4. Fill out the application form. A name and minimal metadata are sufficient.
5. After creating the application, your **App ID** and **App Secret** will be displayed. Copy and store these securely.

You’ll enter these values during integration setup in Home Assistant.

## Supported Entities

All available metrics from your Deye inverter are automatically discovered using the `/device/latest` API.

This includes sensors such as:

| Entity Example                      | Description                                  |
|------------------------------------|----------------------------------------------|
| `sensor.deye_dc_voltage_pv1`       | DC voltage from PV1                          |
| `sensor.deye_external_ct1_power`   | External CT1 Power reading                   |
| `sensor.deye_bms_soc`              | Battery State of Charge                      |
| `sensor.deye_ups_load_power`       | UPS Load Power                               |
| `sensor.deye_grid_frequency`       | Grid Frequency                               |
| `binary_sensor.deye_fault`         | Fault status                                 |

All sensors are automatically labeled, unit-classified, and assigned state/device classes where appropriate. Actual entities vary by inverter model and firmware version.

## Known Limitations

- Time ranges for TOU programs are shown in entity attributes and handled internally by the integration, but not exposed as editable values in Home Assistant.
- Cloud polling interval is based on Deye API update rate, typically every 5–15 minutes.

## Time-of-Use (TOU) Scheduling and Battery Setpoints

The integration exposes Time-of-Use (TOU) configuration options, pulled directly from the Deye Cloud.

Each TOU slot includes:

| Option               | Description                                       |
|----------------------|---------------------------------------------------|
| `enableGridCharge`   | Toggle grid usage for this time slot              |
| `enableGeneration`   | Toggle solar generation for this slot             |
| `soc`                | Set minimum battery SoC for the slot (1–100%)     |
| `time`               | Time window associated with this TOU slot (read-only) |

These are surfaced in Home Assistant as:

- `switch` entities (e.g., `switch.prog_1_grid_charge`)
- `number` entities (e.g., `number.prog_1_battery`)

These settings are validated and written back to the Deye Cloud as a full TOU schedule whenever any value is modified, and provide smart energy usage scheduling through the UI.

## Troubleshooting

- Make sure your Deye credentials work in the mobile app.
- Check Home Assistant logs for errors: **Settings > System > Logs**
- API connectivity issues are usually due to incorrect login or region selection.

---

> 🌐 This integration is not affiliated with or endorsed by Deye. Use at your own risk.