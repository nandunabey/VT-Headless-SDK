# Examples

Quick-start examples for connecting to the VT Headless SDK WebSocket stream.

## Serial number formats

| Format | Type |
|--------|------|
| 41-XXXXXXXX or 42-XXXXXXXX | VIVE Ultimate Tracker |
| LHR-XXXXXXXX | Vive Tracker 3.0 |

All examples work with both tracker types.
Replace serial numbers with your own.

## Prerequisites
START_VUT_ROBOTICS_SDK.bat must be running.
WebSocket stream: ws://localhost:8765

## Examples

| File | Language | Description |
|------|----------|-------------|
| quickstart.py | Python | Print live poses |
| two_trackers.py | Python | Live distance between 2 trackers |
| record_to_csv.py | Python | Record session to CSV |
| nodejs_consumer.js | Node.js | Print live poses |
| unity_consumer.cs | C# / Unity | Drive GameObjects from poses |
| ros_publisher.py | Python / ROS2 | Publish as ROS topics (v0.3) |

## WebSocket message format

```json
{
  "41-A33204726": {
    "position": {"x": 0.12, "y": 0.95, "z": -0.34},
    "rotation": {"w": 0.99, "x": 0.01, "y": 0.05, "z": 0.02},
    "battery_pct": 86,
    "status": "tracking",
    "session_index": 1,
    "model": "VIVE Ultimate Tracker 1"
  },
  "meta": {
    "fps": 60,
    "latency_ms": 18,
    "tracker_count": 4
  }
}
```

## Key rule
Always skip the `"meta"` key when iterating trackers.
Serial numbers are stable across SteamVR restarts.
