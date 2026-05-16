# VUT SDK

> ⚠️ **Alpha Release — v0.1.0-alpha**
> This SDK is in early development. APIs may change
> between releases. Not recommended for production use.
> Tested on 4x VIVE Ultimate Trackers in VO mode on Windows 11.

> ⚠️ **Unofficial SDK — Community Project**
> This is an independent, community-built SDK and is
> NOT affiliated with, endorsed by, or supported by
> HTC Corporation or Valve Corporation.
> VIVE, VIVE Ultimate Tracker, and SteamVR are
> trademarks of their respective owners.
> Use at your own risk.

Headless 6DoF pose streaming for VIVE Ultimate Trackers.

No HMD. No VR headset. Tracker poses streamed directly
over WebSocket for robotics, motion capture, and body tracking.

---

## What this is

VUT SDK bridges SteamVR and Python, streaming live 6DoF poses
from VIVE Ultimate Trackers to any application via WebSocket.

- Real-time position + orientation per tracker
- Up to 4+ trackers simultaneously
- WebSocket API at `ws://localhost:8765`
- Includes robotics and body tracking visualisers
- Foundation for [vut-skeleton](placeholder) body tracking

---

## Prerequisites

**Hardware**
- VIVE Ultimate Trackers (tested with 4x simultaneously)
- Any SteamVR-compatible base station or camera setup

**Software**
- Windows 11
- SteamVR installed and running
- Python 3.10+
### Tracking modes
| Mode | Licence | Room Scan | Map Persists |
|---|---|---|---|
| Standard | None | Each session | No |
| VO mode (recommended) | Business+ | First time only | Yes |

Standard mode confirmed working out of the box.
VO mode: apply at vive.com/business

---

## Installation

```bash
pip install vut-sdk
```

Or from source:

```bash
git clone https://github.com/[username]/vut-sdk.git
cd vut-sdk
pip install -e .
```

---

## Quick start

**Step 1 — Start the SDK stack:**
```
START_VUT_ROBOTICS_SDK.bat
```

**Step 2 — Check tracker status:**
```bash
python -m vut_sdk.tools.vut_status
```

**Step 3 — Connect your app:**
```python
import asyncio
import websockets
import json

async def receive_poses():
    async with websockets.connect("ws://localhost:8765") as ws:
        async for message in ws:
            poses = json.loads(message)
            for tracker_id, pose in poses.items():
                print(tracker_id, pose["position"], pose["rotation"])

asyncio.run(receive_poses())
```

### Using the Python SDK directly
```python
from vut_sdk.tracker import VUTTracker

tracker = VUTTracker("41-A33204726")  # serial number
tracker.connect()

# Single pose read
pose = tracker.get_pose()
print(pose.position, pose.rotation)

# Streaming
def on_pose(pose):
    print(f"{pose.tracker_id}: {pose.position}")

tracker.on_pose(on_pose)
tracker.stream()  # blocks, calls on_pose at --fps rate
```

### Multiple trackers simultaneously
```python
from vut_sdk.fleet import VUTTrackerFleet

fleet = VUTTrackerFleet()
fleet.connect_all()

for serial, pose in fleet.get_poses().items():
    print(f"{serial}: {pose.position}")
```

---

## Screenshots

### Robotics visualiser — 5-tracker top-down view
![Robotics visualiser](docs/screenshots/robotics-visualiser.png)
*5-tracker top-down view with distance lines, 63fps*

### Tracker dashboard — live telemetry
![Tracker dashboard](docs/screenshots/tracker-dashboard.png)
*Live tracker dashboard — serial, pose, battery, tracking status*

### Tracker daemon — WebSocket stream
![Tracker daemon](docs/screenshots/tracker-daemon.png)
*VUT Tracker Daemon — serial-keyed pose stream at 64Hz*

---

## Demo

### Robotics visualiser — live 5-tracker tracking
[![Unofficial VUT Headless SDK - Robotics view](https://img.youtube.com/vi/VURLUIOaj9Y/maxresdefault.jpg)](https://www.youtube.com/watch?v=VURLUIOaj9Y)
*Unofficial VUT Headless SDK — Robotics view*

### Body tracking visualiser
[![Unofficial VUT Headless SDK - Body tracking](https://img.youtube.com/vi/1m04uqlcWGM/maxresdefault.jpg)](https://www.youtube.com/watch?v=1m04uqlcWGM)
*Unofficial VUT Headless SDK — Body tracking*

---

## Architecture

```
4x VIVE Ultimate Trackers
  → SteamVR
  → vtrackerd_openvr.py
  → WebSocket ws://localhost:8765
  → Your application
```

---

## WebSocket API

Broadcast rate is set with `--fps` (default 30, start script uses 60):

| `--fps` | Interval | Latency estimate | Use case |
|---------|----------|-----------------|----------|
| 30      | ~33 ms   | ~33 ms          | Body tracking, low CPU |
| 60      | ~17 ms   | ~17 ms          | Robotics (recommended) |
| 100     | ~10 ms   | ~10 ms          | Minimum latency, higher CPU |

Each broadcast is a flat JSON dict keyed by hardware serial number
(stable across SteamVR restarts), plus a `meta` block:

```json
{
  "41-A33204726": {
    "position":      {"x": 0.12,  "y": 0.95,  "z": -0.34},
    "rotation":      {"w": 0.99,  "x": 0.01,  "y": 0.05,  "z": 0.02},
    "timestamp":     1715000000.123,
    "battery_pct":   46,
    "session_index": 1,
    "model":         "VIVE Ultimate Tracker 1"
  },
  "41-A33200148": {
    "position":      {"x": -0.05, "y": 0.10,  "z": 0.15},
    "rotation":      {"w": 1.0,   "x": 0.0,   "y": 0.0,   "z": 0.0},
    "timestamp":     1715000000.123,
    "battery_pct":   null,
    "session_index": 2,
    "model":         "VIVE Ultimate Tracker 3"
  },
  "meta": {
    "fps":           60,
    "latency_ms":    17,
    "tracker_count": 2
  }
}
```

`battery_pct`: integer 0–100, or `null` if the property read failed.
`session_index` and `model` are informational — never use them as stable
identifiers. Always key on the serial number (top-level dict key).
`meta` is not a tracker entry — skip it when iterating poses.

---

## Tested on

- Windows 11 ✓
- Python 3.14 ✓
- 4x VIVE Ultimate Trackers confirmed simultaneously
- Standard tracking mode confirmed (no licence required)
- VO mode confirmed with Business+ licence
- vut-skeleton body tracking: 5 trackers → 17 joints

---

## Limitations

- Unofficial: not affiliated with or supported by HTC VIVE or Valve
- Standard mode requires room scan each session
- Windows only (SteamVR dependency)
- Tracker IDs may reorder on reconnect — use serial numbers for
  consistent assignment
- No built-in recording/playback (use --mock in vut-skeleton)
- SteamVR must be running before starting the SDK stack

---

## Related projects

### vut-skeleton
17-joint body tracking skeleton solver built on vut-sdk.
5 VIVE Ultimate Trackers → full body pose with inferred joints.
https://github.com/[username]/vut-skeleton

---

## Author

Nandun Abeynayake
github.com/nandunabey

---

## Licence

MIT
