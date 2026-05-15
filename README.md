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

---

## Screenshots

### vut-status — health check
![vut-status](docs/screenshots/vut-status.png)
*All systems operational with active trackers*

### Robotics visualiser — top-down view
![Robotics mode](docs/screenshots/robotics-mode.png)
*Live 6DoF tracking, multiple trackers, 64fps*

### Body tracking visualiser
![Body mode](docs/screenshots/body-mode.png)
*5-tracker body tracking with inferred skeleton joints*

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

Poses are broadcast as JSON at approximately 60–90 fps:

```json
{
  "tracker_0": {
    "position": {"x": 0.12, "y": 0.95, "z": -0.34},
    "rotation": {"w": 0.99, "x": 0.01, "y": 0.05, "z": 0.02},
    "timestamp": 1715000000.123
  }
}
```

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
Head of Product ANZ, HTC VIVE

---

## Licence

MIT
