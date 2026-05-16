"""
vtrackerd_openvr.py
VIVE Ultimate Tracker -> OpenVR pose -> WebSocket broadcast + HTTP server
Supports multiple simultaneous trackers.

Requirements:  pip install openvr websockets

Stack needed:
  - VHConsole.exe  (starts ViveHubServer + ViveTrackerServer)
  - SteamVR        (vrserver.exe)
  - Trackers USB connected, LEDs solid
"""

import argparse
import asyncio
import json
import math
import sys
import time
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import openvr
import websockets

WS_HOST     = "0.0.0.0"
WS_PORT     = 8765
HTTP_PORT   = 8080
POLL_HZ     = 100

VUT_SDK_DIR = Path(__file__).resolve().parent          # C:\Users\vive_\dev\vut-sdk
ROLES_FILE  = VUT_SDK_DIR / "tracker_roles.json"


# ---------------------------------------------------------------------------
# HTTP server — static files + POST /save-roles
# ---------------------------------------------------------------------------

class _HttpHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/save-roles":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            roles = json.loads(body)
            if not isinstance(roles, dict) or not all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in roles.items()
            ):
                raise ValueError("Expected dict of string → string")
            with open(ROLES_FILE, "w") as fh:
                json.dump(roles, fh, indent=2)
            resp = json.dumps({"status": "ok"}).encode()
            code = 200
        except Exception as exc:
            resp = json.dumps({"status": "error", "message": str(exc)}).encode()
            code = 400
        self.send_response(code)
        self.send_header("Content-Type",                "application/json")
        self.send_header("Content-Length",              len(resp))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, *_):
        pass


def _start_http() -> None:
    handler = partial(_HttpHandler, directory=str(VUT_SDK_DIR))
    server  = HTTPServer(("", HTTP_PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"HTTP server      ->  http://localhost:{HTTP_PORT}")


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
_clients:    set        = set()
_latest_msg: str | None = None   # serial-keyed pose dict
_frame_id   = 0
_pkts_total = 0
_pps        = 0.0


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
# Main loop: poll OpenVR at POLL_HZ, broadcast at --fps rate
# ---------------------------------------------------------------------------
async def _main_loop(vr, trackers, broadcast_hz: int):
    """trackers: list of {"index": int, "serial": str, "model": str}"""
    global _latest_msg, _frame_id, _pkts_total, _pps

    poll_interval      = 1.0 / POLL_HZ
    broadcast_interval = 1.0 / broadcast_hz
    latency_ms         = round(1000 / broadcast_hz)
    status_interval    = 0.1          # 10 Hz console

    last_broadcast = 0.0
    last_status    = 0.0
    pps_count      = 0
    pps_t0         = time.perf_counter()

    while True:
        t0 = time.perf_counter()

        # --- poll all device poses in one call (~0.1 ms) ---
        all_poses = vr.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseRawAndUncalibrated, 0,
            openvr.k_unMaxTrackedDeviceCount,
        )

        # Keyed by serial — stable across SteamVR restarts unlike session index
        serial_poses: dict = {}
        any_valid = False

        for trk in trackers:
            idx    = trk["index"]
            serial = trk["serial"]
            model  = trk["model"]
            p      = all_poses[idx]

            if p.bPoseIsValid and p.eTrackingResult == openvr.TrackingResult_Running_OK:
                pos, quat = _mat34_to_pos_quat(p.mDeviceToAbsoluteTracking)
                try:
                    batt_raw    = vr.getFloatTrackedDeviceProperty(
                        idx, openvr.Prop_DeviceBatteryPercentage_Float)
                    battery_pct = int(round(batt_raw * 100))
                except Exception:
                    battery_pct = None
                serial_poses[serial] = {
                    "position": {
                        "x": round(pos[0], 4),
                        "y": round(pos[1], 4),
                        "z": round(pos[2], 4),
                    },
                    "rotation": {
                        "w": round(quat[0], 6),
                        "x": round(quat[1], 6),
                        "y": round(quat[2], 6),
                        "z": round(quat[3], 6),
                    },
                    "timestamp":     time.time(),
                    "battery_pct":   battery_pct,
                    "session_index": idx,    # informational only — do not key on this
                    "model":         model,  # informational only
                }
                any_valid = True

        if any_valid:
            _frame_id   += 1
            _pkts_total += 1
            pps_count   += 1

            elapsed = t0 - pps_t0
            if elapsed >= 1.0:
                _pps      = round(pps_count / elapsed, 1)
                pps_count = 0
                pps_t0    = t0

            payload = dict(serial_poses)
            payload["meta"] = {
                "fps":           broadcast_hz,
                "latency_ms":    latency_ms,
                "tracker_count": len(serial_poses),
            }
            _latest_msg = json.dumps(payload)

        # --- broadcast at --fps rate ---
        now = time.perf_counter()
        if _latest_msg and _clients and (now - last_broadcast) >= broadcast_interval:
            last_broadcast = now
            dead = set()
            for ws in list(_clients):
                try:
                    await ws.send(_latest_msg)
                except Exception:
                    dead.add(ws)
            _clients.difference_update(dead)

        # --- console status at 10 Hz (single overwriting line) ---
        if any_valid and (now - last_status) >= status_interval:
            last_status = now
            parts = [f"frame={_frame_id:6d}  {_pps:.0f}Hz  clients={len(_clients)}"]
            for i, trk in enumerate(trackers, 1):
                entry = serial_poses.get(trk["serial"])
                if entry:
                    p = entry["position"]
                    parts.append(
                        f"  T{i}({trk['serial'][-8:]}): "
                        f"({p['x']:+.3f},{p['y']:+.3f},{p['z']:+.3f})"
                    )
                else:
                    parts.append(f"  T{i}({trk['serial'][-8:]}): --no pose--")
            print("  " + "".join(parts) + "   ", end="\r")

        # --- sleep remainder of poll interval ---
        sleep_s = poll_interval - (time.perf_counter() - t0)
        await asyncio.sleep(max(0.0, sleep_s))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="VUT tracker WebSocket daemon")
    parser.add_argument(
        "--fps", type=int, default=30, choices=[30, 60, 100],
        help="Broadcast rate (30=~33ms, 60=~17ms, 100=~10ms latency)",
    )
    args = parser.parse_args()
    latency_ms = round(1000 / args.fps)

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
    print(f"  [OK] Broadcast rate  : {args.fps} fps (~{latency_ms}ms latency)")

    _start_http()

    async def _run():
        async with websockets.serve(_ws_handler, WS_HOST, WS_PORT):
            print(f"WebSocket server  ->  ws://localhost:{WS_PORT}")
            print(f"Polling at {POLL_HZ} Hz, broadcasting at {args.fps} fps\n")
            await _main_loop(vr, trackers, args.fps)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n\nStopped.")
    finally:
        openvr.shutdown()


if __name__ == "__main__":
    main()
