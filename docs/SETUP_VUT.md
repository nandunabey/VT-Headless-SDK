# Setup Guide — VIVE Ultimate Tracker (VUT)

## Before starting the SDK
Ensure the following before running
START_VT_SDK.bat:

1. VIVE Hub installed and running
2. Trackers paired and showing green in VIVE Hub
3. SteamVR running and trackers active

## Headless Mode Setup (required)

SteamVR must be configured to run without a VR headset.
If you see "Please plug in your VR headset", apply these
settings:

**File 1:** `Steam\config\steamvr.vrsettings`
In the `"steamvr"` section, set:
```json
"requireHmd": false,
"forcedDriver": "null",
"activateMultipleDrivers": true
```

**File 2:**
`Steam\steamapps\common\SteamVR\drivers\null\resources\settings\default.vrsettings`
In the `"driver_null"` section, set:
```json
"enable": true
```

Restart SteamVR after editing.

**Prevent recurrence:** SteamVR updates can reset these
settings. To stop automatic updates, go to Steam > Library
> SteamVR > Properties > Updates and set "Only update this
game when I launch it".

## Serial number format
VUT serials start with 41- or 42-
e.g. 41-A33204726

## Tracking modes
| Mode | Licence | Notes |
|------|---------|-------|
| Standard | Free |  |
| VO mode | Business+ | |

## Setup reference
For VIVE Hub installation, tracker pairing,
and room scan setup:
- HTC documentation: vive.com/setup
- VIVE Hub: vive.com/vive-hub
