# Setup — Vive Tracker 3.0 + Base Stations

## Before starting the SDK

Ensure the following before running
START_VT_SDK.bat:

1. Base stations powered on — solid green light
2. Trackers paired in SteamVR and showing green
3. VIVE Hub is not required for this setup

The SDK starts automatically once SteamVR
shows trackers as active.

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

Vive Tracker 3.0 serials start with `LHR-`
e.g. `LHR-3668F399`

These are handled identically to VUT trackers
by the SDK — no configuration changes needed.

## Advantages over VUT

- Works in complete darkness
- No room scan required
- Persistent coordinate system

## Setup reference

For base station mounting, tracker pairing,
and SteamVR configuration:
- HTC documentation: vive.com/setup
- Valve SteamVR docs: help.steampowered.com/steamvr
