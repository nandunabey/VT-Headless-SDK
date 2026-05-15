"""
vtrackerd_openvr.py
VIVE Ultimate Tracker -> OpenVR pose -> WebSocket broadcast
Supports multiple simultaneous trackers.

Requirements:  pip install openvr websockets

Stack needed:
  - VHConsole.exe  (starts ViveHubServer + ViveTrackerServer)
  - SteamVR        (vrserver.exe)
  - Trackers USB connected, LEDs solid
"""

import asyncio
import json
import math
import sys
import time
from collections import deque

import openvr
import websockets

WS_HOST      = "0.0.0.0"
WS_PORT      = 8765
BROADCAST_HZ = 30
POLL_HZ      = 100
TRAJ_LEN     = 500


# ---------------------------------------------------------------------------
# Rotation matrix (3x4) -> position + quaternion
# ---------------------------------------------------------------------------
def _mat34_to_pos_quat(mat):
    px, py, pz = mat[0][3], mat[1][3], mat[2][3]
    m = [[mat[r][c] for c in range(3)] for r in range(3)]

    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s  = 0.5 / math.sqrt(trace + 1.0)
        qw = 0.25 / s
        qx = (m[2][1] - m[1][2]) * s
        qy = (m[0][2] - m[2][0]) * s
        qz = (m[1][0] - m[0][1]) * s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s  = 2.0 * math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2])
        qw = (m[2][1] - m[1][2]) / s
        qx = 0.25 * s
        qy = (m[0][1] + m[1][0]) / s
        qz = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s  = 2.0 * math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2])
        qw = (m[0][2] - m[2][0]) / s
        qx = (m[0][1] + m[1][0]) / s
        qy = 0.25 * s
        qz = (m[1][2] + m[2][1]) / s
    else:
        s  = 2.0 * math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1])
        qw = (m[1][0] - m[0][1]) / s
        qx = (m[0][2] + m[2][0]) / s
        qy = (m[1][2] + m[2][1]) / s
        qz = 0.25 * s

    return (px, py, pz), (qw, qx, qy, qz)


# ---------------------------------------------------------------------------
# State shared between coroutines (all on the same asyncio thread)
# ---------------------------------------------------------------------------
_clients:     set        = set()
_latest_msg:  str | None = None   # pose_multi  (new format)
_compat_msg:  str | None = None   # pose        (backwards-compat, first tracker only)
_frame_id    = 0
_pkts_total  = 0
_pps         = 0.0


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------
async def _ws_handler(websocket):
    _clients.add(websocket)
    addr = getattr(websocket, "remote_address", "?")
    print(f"  + client {addr}  ({len(_clients)} connected)")
    try:
        await websocket.wait_closed()
    finally:
        _clients.discard(websocket)
        print(f"  - client gone   ({len(_clients)} connected)")


# ---------------------------------------------------------------------------
# Main loop: poll OpenVR at POLL_HZ, broadcast at BROADCAST_HZ
# ---------------------------------------------------------------------------
async def _main_loop(vr, trackers):
    """trackers: list of {"index": int, "serial": str, "model": str}"""
    global _latest_msg, _compat_msg, _frame_id, _pkts_total, _pps

    poll_interval      = 1.0 / POLL_HZ
    broadcast_interval = 1.0 / BROADCAST_HZ
    status_interval    = 0.1          # 10 Hz console

    last_broadcast = 0.0
    last_status    = 0.0
    pps_count      = 0
    pps_t0         = time.perf_counter()

    # Per-tracker trajectory buffers keyed by serial
    trajectories = {t["serial"]: deque(maxlen=TRAJ_LEN) for t in trackers}

    # First tracker is the primary for the backwards-compat single-pose message
    primary_serial = trackers[0]["serial"]

    while True:
        t0 = time.perf_counter()

        # --- poll all device poses in one call (~0.1 ms) ---
        all_poses = vr.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseRawAndUncalibrated, 0,
            openvr.k_unMaxTrackedDeviceCount,
        )

        tracker_payloads = []
        any_valid = False

        for trk in trackers:
            idx    = trk["index"]
            serial = trk["serial"]
            p      = all_poses[idx]

            if p.bPoseIsValid and p.eTrackingResult == openvr.TrackingResult_Running_OK:
                pos, quat = _mat34_to_pos_quat(p.mDeviceToAbsoluteTracking)
                pt = {"x": round(pos[0], 4),
                      "y": round(pos[1], 4),
                      "z": round(pos[2], 4)}
                trajectories[serial].append(pt)
                tracker_payloads.append({
                    "id":    serial,
                    "index": idx,
                    "pos":   pt,
                    "rot": {
                        "w": round(quat[0], 6),
                        "x": round(quat[1], 6),
                        "y": round(quat[2], 6),
                        "z": round(quat[3], 6),
                    },
                    "valid": True,
                })
                any_valid = True
            else:
                tracker_payloads.append({
                    "id":    serial,
                    "index": idx,
                    "pos":   {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rot":   {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
                    "valid": False,
                })

        if any_valid:
            _frame_id   += 1
            _pkts_total += 1
            pps_count   += 1

            elapsed = t0 - pps_t0
            if elapsed >= 1.0:
                _pps      = round(pps_count / elapsed, 1)
                pps_count = 0
                pps_t0    = t0

            now_ms = int(time.time() * 1000)

            # --- pose_multi: all trackers ---
            _latest_msg = json.dumps({
                "type":      "pose_multi",
                "trackers":  tracker_payloads,
                "timestamp": now_ms,
                "frame_id":  _frame_id,
                "stats": {
                    "tracker_count":   len(trackers),
                    "packets_per_sec": _pps,
                    "status":          "tracking",
                },
                "trajectories": {
                    serial: list(traj)
                    for serial, traj in trajectories.items()
                },
            })

            # --- pose: backwards-compat single-tracker (primary) ---
            primary = next(
                (t for t in tracker_payloads if t["id"] == primary_serial),
                tracker_payloads[0]
            )
            _compat_msg = json.dumps({
                "type":      "pose",
                "pos":       primary["pos"],
                "rot":       primary["rot"],
                "timestamp": now_ms,
                "frame_id":  _frame_id,
                "stats": {
                    "packets_received": _pkts_total,
                    "packets_per_sec":  _pps,
                    "packet_size":      48,
                    "parse_format":     "openvr_matrix34",
                    "status":           "tracking",
                    "tracker_id":       primary_serial,
                },
                "trajectory": list(trajectories[primary_serial]),
            })

        # --- broadcast at BROADCAST_HZ ---
        now = time.perf_counter()
        if _latest_msg and _compat_msg and _clients and (now - last_broadcast) >= broadcast_interval:
            last_broadcast = now
            dead = set()
            for ws in list(_clients):
                try:
                    await ws.send(_latest_msg)
                    await ws.send(_compat_msg)
                except Exception:
                    dead.add(ws)
            _clients.difference_update(dead)

        # --- console status at 10 Hz (single overwriting line) ---
        if any_valid and (now - last_status) >= status_interval:
            last_status = now
            parts = [f"frame={_frame_id:6d}  {_pps:.0f}Hz  clients={len(_clients)}"]
            for i, tp in enumerate(tracker_payloads, 1):
                p = tp["pos"]
                if tp["valid"]:
                    parts.append(
                        f"  T{i}({tp['id'][-8:]}): "
                        f"({p['x']:+.3f},{p['y']:+.3f},{p['z']:+.3f})"
                    )
                else:
                    parts.append(f"  T{i}({tp['id'][-8:]}): --no pose--")
            print("  " + "".join(parts) + "   ", end="\r")

        # --- sleep remainder of poll interval ---
        sleep_s = poll_interval - (time.perf_counter() - t0)
        await asyncio.sleep(max(0.0, sleep_s))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    print("Initialising OpenVR...")
    try:
        vr = openvr.init(openvr.VRApplication_Background)
        print("  OK")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    # Find ALL GenericTrackers
    trackers = []
    for i in range(openvr.k_unMaxTrackedDeviceCount):
        if vr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_GenericTracker:
            try:
                serial = vr.getStringTrackedDeviceProperty(
                    i, openvr.Prop_SerialNumber_String)
            except Exception:
                serial = f"tracker_{i}"
            try:
                model = vr.getStringTrackedDeviceProperty(
                    i, openvr.Prop_ModelNumber_String)
            except Exception:
                model = "?"
            print(f"  Tracker [{i}]  serial={serial}  model={model}")
            trackers.append({"index": i, "serial": serial, "model": model})

    if not trackers:
        print("No GenericTrackers found — is SteamVR running with trackers active?")
        openvr.shutdown()
        sys.exit(1)

    print(f"\n  {len(trackers)} tracker(s) found")

    async def _run():
        async with websockets.serve(_ws_handler, WS_HOST, WS_PORT):
            print(f"\nWebSocket server  ->  ws://localhost:{WS_PORT}")
            print(f"Polling at {POLL_HZ} Hz, broadcasting at {BROADCAST_HZ} fps\n")
            await _main_loop(vr, trackers)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n\nStopped.")
    finally:
        openvr.shutdown()


if __name__ == "__main__":
    main()
