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
import csv
import io
import json
import math
import sys
import time
import threading
import uuid
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import openvr
import websockets

WS_HOST     = "0.0.0.0"
WS_PORT     = 8765
HTTP_PORT   = 8080
POLL_HZ     = 100
SDK_VERSION = "0.2"


def get_tracker_type(serial: str) -> str:
    """Detect tracker type from serial number format."""
    if serial.upper().startswith("LHR-"):
        return "lighthouse"
    elif serial.startswith(("41-", "42-")):
        return "vut"
    else:
        return "unknown"


VUT_SDK_DIR   = Path(__file__).resolve().parent          # C:\Users\vive_\dev\vut-sdk
ROLES_FILE    = VUT_SDK_DIR / "tracker_roles.json"
RECORDINGS_DIR = VUT_SDK_DIR / "recordings"
ANCHORS_FILE   = VUT_SDK_DIR / "anchors.json"
SPACECAL_FILE = VUT_SDK_DIR / "space_calibration.json"
SCAN_DIR      = VUT_SDK_DIR / "scan_app"
SCAN_HTML     = SCAN_DIR / "scan.html"
SESSIONS_DIR  = VUT_SDK_DIR / "sessions"
MAP_DIR_VIVE  = Path(
    r"C:\ProgramData\HTC\ViveSoftware\VBStorage\VBPManager\Files"
)


# ---------------------------------------------------------------------------
# Tracker list — populated once in main() after OpenVR enumerate
# ---------------------------------------------------------------------------
_trackers: list = []    # [{"index": int, "serial": str, "model": str}, …]

# ---------------------------------------------------------------------------
# Map-file watcher state  (thread-safe via _watcher_lock)
# ---------------------------------------------------------------------------
_watcher_lock     = threading.Lock()
_watcher_active   = False
_watcher_baseline: set = set()          # ZIP paths present when watcher was armed
_loop: asyncio.AbstractEventLoop | None = None   # set inside _run()

# ---------------------------------------------------------------------------
# Recording state (accessed only from HTTP thread via threading.Lock)
# ---------------------------------------------------------------------------
_rec_lock      = threading.Lock()
_rec_active    = False
_rec_session_id: str | None = None
_rec_label     = ""
_rec_frames: list = []          # list of {"timestamp": float, "poses": dict}
_rec_started_at: float = 0.0

_play_active   = False

# ---------------------------------------------------------------------------
# Space calibration state
# ---------------------------------------------------------------------------
_spacecal_config: dict | None = None   # loaded calibration JSON or None
_spacecal_mode:   str         = "off"  # "off" | "unify"
_spacecal_R_quat: tuple       = (1.0, 0.0, 0.0, 0.0)  # rotation as quaternion (w,x,y,z)


def _rot_mat_to_quat(R: list) -> tuple:
    """Convert 3×3 rotation matrix (list of lists) to quaternion (w,x,y,z)."""
    m = R
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
    return (qw, qx, qy, qz)


def _quat_mul(q1: tuple, q2: tuple) -> tuple:
    """Hamilton product of two quaternions (w,x,y,z)."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def _load_spacecal() -> dict | None:
    if SPACECAL_FILE.is_file():
        try:
            return json.loads(SPACECAL_FILE.read_text())
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Anchor drift correction state
# ---------------------------------------------------------------------------
_anchor_active:  bool        = False
_anchor_serial:  str | None  = None
_anchor_ref_pos: list | None = None   # [x, y, z] in unified (LH) space
_anchor_buf:     list        = []     # rolling 10-frame position buffer
_drift_vec:      list        = [0.0, 0.0, 0.0]   # applied per-frame correction


def _apply_anchor_config(cal: dict) -> None:
    """Activate anchor correction from calibration dict. Only effective in unify mode."""
    global _anchor_active, _anchor_serial, _anchor_ref_pos, _anchor_buf, _drift_vec
    anc = cal.get("drift_anchor")
    if anc and _spacecal_mode == "unify":
        _anchor_serial  = anc.get("lh_serial")
        _anchor_ref_pos = anc.get("reference_position_lh")
        del _anchor_buf[:]       # clear in-place (safe across threads)
        _drift_vec[0] = _drift_vec[1] = _drift_vec[2] = 0.0
        _anchor_active  = bool(_anchor_serial and _anchor_ref_pos)
    else:
        _anchor_active  = False
        _anchor_serial  = None
        _anchor_ref_pos = None


# ---------------------------------------------------------------------------
# HTTP server — static files + /save-roles + /recorder/*
# ---------------------------------------------------------------------------

class _HttpHandler(SimpleHTTPRequestHandler):
    def _clean_path(self) -> str:
        """Strip query string and fragment so routes match cleanly."""
        return urlparse(self.path).path

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self._clean_path()
        if path == "/scan":
            self._serve_scan_html()
        elif path == "/api/trackers":
            self._get_api_trackers()
        elif path == "/api/mapfiles":
            self._get_api_mapfiles()
        elif path == "/api/sessions":
            self._get_api_scan_sessions()
        elif path.startswith("/api/sessions/"):
            self._get_api_scan_session(path[len("/api/sessions/"):])
        elif path == "/api/scan/watch/status":
            self._get_watch_status()
        elif path == "/recorder/sessions":
            self._get_sessions()
        elif path == "/calibration/anchors":
            self._get_calibration_anchors()
        elif path == "/spacecal/current":
            self._get_spacecal_current()
        else:
            super().do_GET()

    def do_POST(self):
        path = self._clean_path()
        routes = {
            "/save-roles":               self._post_save_roles,
            "/recorder/start":           self._post_rec_start,
            "/recorder/stop":            self._post_rec_stop,
            "/recorder/play":            self._post_rec_play,
            "/recorder/pause":           self._post_rec_pause,
            "/recorder/stop_playback":   self._post_rec_stop_playback,
            "/recorder/export/csv":      self._post_export_csv,
            "/recorder/export/json":     self._post_export_json,
            "/calibration/save-anchors":  self._post_save_anchors,
            "/api/session":               self._post_api_session,
            "/api/scan/watch/start":      self._post_watch_start,
            "/api/scan/watch/stop":       self._post_watch_stop,
            "/spacecal/save":             self._post_spacecal_save,
            "/spacecal/set-anchor":       self._post_spacecal_set_anchor,
            "/spacecal/clear-anchor":     self._post_spacecal_clear_anchor,
        }
        handler = routes.get(path)
        if handler is None:
            self._json_resp({"error": f"unknown route: {path}"}, 404)
            return
        handler()

    # ── /save-roles ──────────────────────────────────────────────────────────
    def _post_save_roles(self):
        body = self._read_body()
        try:
            roles = json.loads(body)
            if not isinstance(roles, dict):
                raise ValueError("Expected dict")
            for k, v in roles.items():
                if not isinstance(k, str):
                    raise ValueError("Keys must be strings")
                if isinstance(v, str):
                    pass  # old format — accept as-is
                elif isinstance(v, dict):
                    if "role" not in v or not isinstance(v.get("role"), str):
                        raise ValueError(f"Object value for '{k}' must have string 'role' key")
                else:
                    raise ValueError(f"Value for '{k}' must be string or object")
            with open(ROLES_FILE, "w") as fh:
                json.dump(roles, fh, indent=2)
            self._json_resp({"status": "ok"})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 400)

    # ── /recorder/start ───────────────────────────────────────────────────────
    def _post_rec_start(self):
        global _rec_active, _rec_session_id, _rec_label, _rec_frames, _rec_started_at
        body = self._read_body()
        try:
            data  = json.loads(body) if body else {}
            label = str(data.get("label", "session"))[:64]
        except Exception:
            label = "session"
        with _rec_lock:
            if _rec_active:
                self._json_resp({"status": "error", "message": "already recording"}, 400)
                return
            _rec_active     = True
            _rec_session_id = str(uuid.uuid4())[:8]
            _rec_label      = label
            _rec_frames     = []
            _rec_started_at = time.time()
        self._json_resp({"status": "ok", "session_id": _rec_session_id})

    # ── /recorder/stop ────────────────────────────────────────────────────────
    def _post_rec_stop(self):
        global _rec_active, _rec_session_id
        with _rec_lock:
            if not _rec_active:
                self._json_resp({"status": "error", "message": "not recording"}, 400)
                return
            _rec_active = False
            frames      = list(_rec_frames)
            label       = _rec_label
            started_at  = _rec_started_at

        RECORDINGS_DIR.mkdir(exist_ok=True)
        ts       = time.strftime("%Y%m%d_%H%M%S", time.localtime(started_at))
        filename = f"{ts}_{label[:20].replace(' ','_')}.vut"
        filepath = RECORDINGS_DIR / filename

        with open(filepath, "w") as fh:
            meta_line = {"type": "meta", "label": label,
                         "started_at": started_at, "sdk_version": SDK_VERSION}
            fh.write(json.dumps(meta_line) + "\n")
            for fr in frames:
                fh.write(json.dumps({"type": "frame",
                                     "timestamp": fr["timestamp"],
                                     "poses": fr["poses"]}) + "\n")

        self._json_resp({"status": "ok", "file": filename, "frames": len(frames)})

    # ── /recorder/sessions ────────────────────────────────────────────────────
    def _get_sessions(self):
        RECORDINGS_DIR.mkdir(exist_ok=True)
        sessions = []
        for f in sorted(RECORDINGS_DIR.glob("*.vut"), key=lambda x: x.stat().st_mtime, reverse=True):
            info = {"file": f.name, "label": f.stem, "started_at": None,
                    "duration_s": 0, "frames": 0, "trackers": 0}
            try:
                lines = f.read_text().splitlines()
                meta  = json.loads(lines[0]) if lines else {}
                if meta.get("type") == "meta":
                    info["label"]      = meta.get("label", f.stem)
                    info["started_at"] = meta.get("started_at")
                frame_lines = [l for l in lines[1:] if l]
                info["frames"] = len(frame_lines)
                if frame_lines:
                    first = json.loads(frame_lines[0])
                    last  = json.loads(frame_lines[-1])
                    info["duration_s"] = round(last["timestamp"] - first["timestamp"], 2)
                    serials = set()
                    for fl in frame_lines[:10]:
                        poses = json.loads(fl).get("poses", {})
                        serials.update(poses.keys())
                    info["trackers"]         = len(serials)
                    info["vut_count"]        = sum(1 for s in serials if get_tracker_type(s) == "vut")
                    info["lighthouse_count"] = sum(1 for s in serials if get_tracker_type(s) == "lighthouse")
            except Exception:
                pass
            sessions.append(info)
        self._json_resp({"sessions": sessions})

    # ── /recorder/play ────────────────────────────────────────────────────────
    def _post_rec_play(self):
        body = self._read_body()
        try:
            data  = json.loads(body)
            fname = data.get("file", "")
        except Exception:
            self._json_resp({"status": "error", "message": "bad request"}, 400)
            return

        fpath = RECORDINGS_DIR / fname
        if not fpath.is_file() or not fname.endswith(".vut"):
            self._json_resp({"status": "error", "message": "file not found"}, 404)
            return

        frames = []
        try:
            lines = fpath.read_text().splitlines()
            for line in lines:
                obj = json.loads(line)
                if obj.get("type") == "frame":
                    frames.append({"timestamp": obj["timestamp"], "poses": obj.get("poses", {})})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 500)
            return

        duration = 0
        if len(frames) > 1:
            duration = round(frames[-1]["timestamp"] - frames[0]["timestamp"], 2)

        self._json_resp({"status": "ok", "frames": frames, "duration_s": duration})

    # ── /recorder/pause ───────────────────────────────────────────────────────
    def _post_rec_pause(self):
        self._json_resp({"status": "ok"})

    # ── /recorder/stop_playback ───────────────────────────────────────────────
    def _post_rec_stop_playback(self):
        self._json_resp({"status": "ok"})

    # ── /recorder/export/csv ─────────────────────────────────────────────────
    def _post_export_csv(self):
        body = self._read_body()
        try:
            data  = json.loads(body)
            fname = data.get("file", "")
        except Exception:
            self._json_resp({"status": "error", "message": "bad request"}, 400)
            return

        fpath = RECORDINGS_DIR / fname
        if not fpath.is_file() or not fname.endswith(".vut"):
            self._json_resp({"status": "error", "message": "file not found"}, 404)
            return

        try:
            lines = fpath.read_text().splitlines()
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 500)
            return

        # Collect all serials in order of first appearance
        serials = []
        frame_rows = []
        for line in lines:
            obj = json.loads(line)
            if obj.get("type") != "frame":
                continue
            poses = obj.get("poses", {})
            for s in poses:
                if s not in serials:
                    serials.append(s)
            frame_rows.append((obj["timestamp"], poses))

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "serial", "tracker_type",
                         "x", "y", "z", "qw", "qx", "qy", "qz", "battery_pct"])
        for ts, poses in frame_rows:
            for s in serials:
                p = poses.get(s)
                if not p:
                    continue
                pos = p.get("position", {})
                rot = p.get("rotation", {})
                writer.writerow([
                    ts, s, get_tracker_type(s),
                    pos.get("x", ""), pos.get("y", ""), pos.get("z", ""),
                    rot.get("w", ""), rot.get("x", ""), rot.get("y", ""), rot.get("z", ""),
                    p.get("battery_pct", ""),
                ])

        data_bytes = buf.getvalue().encode()
        outname    = fname.replace(".vut", ".csv")
        self.send_response(200)
        self.send_header("Content-Type",               "text/csv")
        self.send_header("Content-Disposition",        f'attachment; filename="{outname}"')
        self.send_header("Content-Length",             len(data_bytes))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data_bytes)

    # ── /recorder/export/json ────────────────────────────────────────────────
    def _post_export_json(self):
        body = self._read_body()
        try:
            data  = json.loads(body)
            fname = data.get("file", "")
        except Exception:
            self._json_resp({"status": "error", "message": "bad request"}, 400)
            return

        fpath = RECORDINGS_DIR / fname
        if not fpath.is_file() or not fname.endswith(".vut"):
            self._json_resp({"status": "error", "message": "file not found"}, 404)
            return

        try:
            raw = fpath.read_bytes()
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 500)
            return

        outname = fname.replace(".vut", ".json")
        self.send_response(200)
        self.send_header("Content-Type",               "application/json")
        self.send_header("Content-Disposition",        f'attachment; filename="{outname}"')
        self.send_header("Content-Length",             len(raw))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    # ── /calibration/anchors ─────────────────────────────────────────────────
    def _get_calibration_anchors(self):
        if ANCHORS_FILE.is_file():
            try:
                data = json.loads(ANCHORS_FILE.read_text())
                self._json_resp(data)
                return
            except Exception:
                pass
        self._json_resp({"origin": None, "anchors": {}, "zones": {}})

    # ── /calibration/save-anchors ─────────────────────────────────────────────
    def _post_save_anchors(self):
        body = self._read_body()
        try:
            data = json.loads(body)
            ANCHORS_FILE.write_text(json.dumps(data, indent=2))
            self._json_resp({"status": "ok"})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 400)

    # ── /scan ────────────────────────────────────────────────────────────────
    def _serve_scan_html(self):
        if not SCAN_HTML.is_file():
            self._json_resp({"error": "scan.html not found — create scan_app/scan.html"}, 404)
            return
        data = SCAN_HTML.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",   "text/html; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.send_header("Cache-Control",  "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # ── /api/trackers ─────────────────────────────────────────────────────────
    def _get_api_trackers(self):
        # Extract latest battery / tracking state from the live pose snapshot.
        poses: dict = {}
        if _latest_msg:
            try:
                frame = json.loads(_latest_msg)
                poses = {k: v for k, v in frame.items() if k != "meta"}
            except Exception:
                pass
        out = []
        for trk in _trackers:
            serial = trk["serial"]
            pose   = poses.get(serial, {})
            out.append({
                "serial":       serial,
                "model":        trk.get("model", ""),
                "tracker_type": trk.get("tracker_type", get_tracker_type(serial)),
                "index":        trk.get("index"),
                "battery_pct":  pose.get("battery_pct"),
                "tracking":     bool(pose),
            })
        self._json_resp({"trackers": out, "count": len(out)})

    # ── /api/mapfiles ─────────────────────────────────────────────────────────
    def _get_api_mapfiles(self):
        files = []
        if MAP_DIR_VIVE.exists():
            for z in sorted(
                MAP_DIR_VIVE.rglob("*.zip"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                try:
                    st = z.stat()
                    files.append({
                        "name":        z.name,
                        "path":        str(z),
                        "size_bytes":  st.st_size,
                        "modified":    round(st.st_mtime, 3),
                    })
                except Exception:
                    pass
        self._json_resp({"map_files": files, "count": len(files)})

    # ── /api/session (POST) ───────────────────────────────────────────────────
    def _post_api_session(self):
        body = self._read_body()
        try:
            data = json.loads(body)
            sid  = data.get("id") or time.strftime("%Y%m%d_%H%M%S")
            SESSIONS_DIR.mkdir(exist_ok=True)
            fpath = SESSIONS_DIR / f"session_{sid}.json"
            fpath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            self._json_resp({"status": "ok", "id": sid, "file": fpath.name})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 400)

    # ── /api/sessions (GET) ───────────────────────────────────────────────────
    def _get_api_scan_sessions(self):
        SESSIONS_DIR.mkdir(exist_ok=True)
        sessions = []
        for f in sorted(
            SESSIONS_DIR.glob("session_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                sessions.append(json.loads(f.read_text()))
            except Exception:
                sessions.append({"file": f.name, "error": "parse failed"})
        self._json_resp({"sessions": sessions, "count": len(sessions)})

    # ── /api/sessions/<id> (GET) ──────────────────────────────────────────────
    def _get_api_scan_session(self, sid: str):
        SESSIONS_DIR.mkdir(exist_ok=True)
        candidates = [
            SESSIONS_DIR / f"session_{sid}.json",
            SESSIONS_DIR / sid,
        ]
        for c in candidates:
            if c.is_file():
                try:
                    self._json_resp(json.loads(c.read_text()))
                    return
                except Exception:
                    break
        self._json_resp({"error": "session not found", "id": sid}, 404)

    # ── /api/scan/watch/* ─────────────────────────────────────────────────────
    def _get_watch_status(self):
        with _watcher_lock:
            self._json_resp({
                "active":         _watcher_active,
                "baseline_count": len(_watcher_baseline),
            })

    def _post_watch_start(self):
        global _watcher_active, _watcher_baseline
        try:
            zips = {str(p) for p in MAP_DIR_VIVE.rglob("*.zip")} \
                   if MAP_DIR_VIVE.exists() else set()
        except Exception:
            zips = set()
        with _watcher_lock:
            _watcher_active  = True
            _watcher_baseline = zips
        print(f"\n  [map watcher] armed — baseline {len(zips)} ZIP(s)")
        self._json_resp({"status": "ok", "baseline_count": len(zips)})

    def _post_watch_stop(self):
        global _watcher_active
        with _watcher_lock:
            _watcher_active = False
        print(f"\n  [map watcher] disarmed")
        self._json_resp({"status": "ok"})

    # ── /spacecal/set-anchor ─────────────────────────────────────────────────
    def _post_spacecal_set_anchor(self):
        global _spacecal_config
        body = self._read_body()
        try:
            data = json.loads(body)
            if "lh_serial" not in data or "reference_position_lh" not in data:
                raise ValueError("Missing lh_serial or reference_position_lh")
            if not SPACECAL_FILE.is_file():
                raise ValueError("No space_calibration.json — run space calibration first")
            cal = json.loads(SPACECAL_FILE.read_text())
            cal["drift_anchor"] = {
                "lh_serial":             data["lh_serial"],
                "reference_position_lh": data["reference_position_lh"],
                "set_at":                data.get("set_at", ""),
            }
            SPACECAL_FILE.write_text(json.dumps(cal, indent=2))
            _spacecal_config = cal
            if _spacecal_mode == "unify":
                _apply_anchor_config(cal)
            self._json_resp({"status": "ok"})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 400)

    # ── /spacecal/clear-anchor ────────────────────────────────────────────────
    def _post_spacecal_clear_anchor(self):
        global _spacecal_config, _anchor_active, _anchor_serial, _anchor_ref_pos, _drift_vec
        try:
            if SPACECAL_FILE.is_file():
                cal = json.loads(SPACECAL_FILE.read_text())
                cal.pop("drift_anchor", None)
                SPACECAL_FILE.write_text(json.dumps(cal, indent=2))
                _spacecal_config = cal
            _anchor_active  = False
            _anchor_serial  = None
            _anchor_ref_pos = None
            _drift_vec[0]   = _drift_vec[1] = _drift_vec[2] = 0.0
            self._json_resp({"status": "ok"})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 400)

    # ── /spacecal/current ─────────────────────────────────────────────────────
    def _get_spacecal_current(self):
        if SPACECAL_FILE.is_file():
            try:
                self._json_resp(json.loads(SPACECAL_FILE.read_text()))
                return
            except Exception:
                pass
        self._json_resp({"error": "no calibration saved"}, 404)

    # ── /spacecal/save ────────────────────────────────────────────────────────
    def _post_spacecal_save(self):
        global _spacecal_config, _spacecal_mode, _spacecal_R_quat
        body = self._read_body()
        try:
            cal = json.loads(body)
            if not isinstance(cal, dict):
                raise ValueError("Expected object")
            for key in ("rotation", "translation", "vut_serial", "lh_serial"):
                if key not in cal:
                    raise ValueError(f"Missing field: {key}")
            SPACECAL_FILE.write_text(json.dumps(cal, indent=2))
            # Hot-reload so daemon picks it up without restart if already in unify mode
            _spacecal_config = cal
            if _spacecal_mode == "unify":
                _spacecal_R_quat = _rot_mat_to_quat(cal["rotation"])
            self._json_resp({"status": "ok", "file": SPACECAL_FILE.name})
        except Exception as exc:
            self._json_resp({"status": "error", "message": str(exc)}, 400)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def _json_resp(self, obj: dict, code: int = 200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type",                "application/json")
        self.send_header("Content-Length",              len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


async def _broadcast(msg: str) -> None:
    """Push an arbitrary JSON string to every connected WebSocket client."""
    dead = set()
    for ws in list(_clients):
        try:
            await ws.send(msg)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


def _start_map_watcher() -> None:
    """Daemon thread: poll MAP_DIR_VIVE every 2 s; push WS event for new ZIPs."""
    def _run():
        while True:
            time.sleep(2.0)
            with _watcher_lock:
                if not _watcher_active:
                    continue
                baseline = set(_watcher_baseline)
            if not MAP_DIR_VIVE.exists():
                continue
            try:
                current = {str(p) for p in MAP_DIR_VIVE.rglob("*.zip")}
            except Exception:
                continue
            new = current - baseline
            if not new or _loop is None:
                continue
            with _watcher_lock:
                _watcher_baseline.update(new)
            for path_str in sorted(new):
                p = Path(path_str)
                try:
                    size = p.stat().st_size
                except Exception:
                    size = 0
                msg = json.dumps({
                    "type":       "map_file_new",
                    "name":       p.name,
                    "path":       path_str,
                    "size_bytes": size,
                    "t":          time.time(),
                })
                asyncio.run_coroutine_threadsafe(_broadcast(msg), _loop)
                print(f"\n  [map watcher] new ZIP: {p.name}  ({size // 1024} KB)")

    threading.Thread(target=_run, daemon=True, name="map-watcher").start()
    print(f"Map watcher      ->  polling {MAP_DIR_VIVE.name}/ every 2 s")


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
                    "session_index": idx,
                    "model":         model,
                    "tracker_type":  trk.get("tracker_type", get_tracker_type(serial)),
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

            # ── Apply space calibration (unify mode) ──────────────────────
            if _spacecal_mode == "unify" and _spacecal_config is not None:
                R = _spacecal_config["rotation"]
                t = _spacecal_config["translation"]
                for serial, pose in serial_poses.items():
                    if get_tracker_type(serial) != "vut":
                        continue
                    p = pose["position"]
                    px, py, pz = p["x"], p["y"], p["z"]
                    p["x"] = round(R[0][0]*px + R[0][1]*py + R[0][2]*pz + t[0], 4)
                    p["y"] = round(R[1][0]*px + R[1][1]*py + R[1][2]*pz + t[1], 4)
                    p["z"] = round(R[2][0]*px + R[2][1]*py + R[2][2]*pz + t[2], 4)
                    q = pose["rotation"]
                    qout = _quat_mul(_spacecal_R_quat, (q["w"], q["x"], q["y"], q["z"]))
                    pose["rotation"]["w"] = round(qout[0], 6)
                    pose["rotation"]["x"] = round(qout[1], 6)
                    pose["rotation"]["y"] = round(qout[2], 6)
                    pose["rotation"]["z"] = round(qout[3], 6)

            # ── Apply anchor drift correction ─────────────────────────────
            drift_mm = 0.0
            if _anchor_active and _anchor_serial and _anchor_ref_pos is not None:
                anc_pose = serial_poses.get(_anchor_serial)
                if anc_pose and anc_pose.get("position"):
                    ap = anc_pose["position"]
                    a_now = [ap["x"], ap["y"], ap["z"]]
                    _anchor_buf.append(a_now)
                    if len(_anchor_buf) > 10:
                        _anchor_buf.pop(0)
                    n_buf = len(_anchor_buf)
                    a_avg = [sum(p[k] for p in _anchor_buf) / n_buf for k in range(3)]
                    # Outlier rejection: skip if anchor jumped > 50mm (occlusion / blip)
                    jump_mm = math.sqrt(sum((a_now[k] - a_avg[k])**2 for k in range(3))) * 1000
                    if jump_mm < 50.0:
                        for k in range(3):
                            _drift_vec[k] = _anchor_ref_pos[k] - a_avg[k]
                # Anchor not in frame → hold last good _drift_vec unchanged

                for serial, pose in serial_poses.items():
                    if get_tracker_type(serial) == "vut":
                        p = pose["position"]
                        p["x"] = round(p["x"] + _drift_vec[0], 4)
                        p["y"] = round(p["y"] + _drift_vec[1], 4)
                        p["z"] = round(p["z"] + _drift_vec[2], 4)

                drift_mm = math.sqrt(sum(v * v for v in _drift_vec)) * 1000

            cal_residual = None
            if _spacecal_config:
                cal_residual = (_spacecal_config.get("quality") or {}).get("median_residual_mm")

            payload = dict(serial_poses)
            payload["meta"] = {
                "fps":                     broadcast_hz,
                "latency_ms":              latency_ms,
                "tracker_count":           len(serial_poses),
                "vut_count":               sum(1 for s in serial_poses if get_tracker_type(s) == "vut"),
                "lighthouse_count":        sum(1 for s in serial_poses if get_tracker_type(s) == "lighthouse"),
                "space_calibration":       _spacecal_mode,
                "calibration_residual_mm": cal_residual,
                "anchor_correction":       "on" if _anchor_active else "off",
                "anchor_serial":           _anchor_serial if _anchor_active else None,
                "drift_correction_mm":     round(drift_mm, 2) if _anchor_active else None,
            }
            _latest_msg = json.dumps(payload)

            # capture frame if recording (non-blocking — lock is uncontended during normal op)
            if _rec_active:
                with _rec_lock:
                    if _rec_active:
                        _rec_frames.append({
                            "timestamp": time.time(),
                            "poses":     dict(serial_poses),
                        })

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
    parser.add_argument(
        "--space-cal", choices=["off", "unify"], default=None, dest="space_cal",
        help="Space calibration mode: off (default) or unify (apply VUT→LH transform)",
    )
    parser.add_argument(
        "--anchor-correct", choices=["on", "off"], default=None, dest="anchor_correct",
        help="Anchor drift correction (default: on if drift_anchor present and unify active)",
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
            ttype      = get_tracker_type(serial)
            type_label = "LH" if ttype == "lighthouse" else "VUT" if ttype == "vut" else "???"
            print(f"  Tracker [{i}]  serial={serial}  type={type_label:<4}  model={model}")
            trackers.append({"index": i, "serial": serial, "model": model, "tracker_type": ttype})

    if not trackers:
        print("No GenericTrackers found — is SteamVR running with trackers active?")
        openvr.shutdown()
        sys.exit(1)

    global _trackers, _spacecal_config, _spacecal_mode, _spacecal_R_quat
    _trackers = trackers          # expose to HTTP handlers via module-level ref

    # Load space calibration
    _spacecal_config = _load_spacecal()
    if args.space_cal is not None:
        _spacecal_mode = args.space_cal
    elif _spacecal_config is not None:
        _spacecal_mode = "off"   # explicit opt-in required; file present but mode defaults off
    if _spacecal_mode == "unify" and _spacecal_config is not None:
        _spacecal_R_quat = _rot_mat_to_quat(_spacecal_config["rotation"])
        _apply_anchor_config(_spacecal_config)
    if args.anchor_correct == "off":
        global _anchor_active
        _anchor_active = False

    print(f"\n  {len(trackers)} tracker(s) found")
    print(f"  [OK] Broadcast rate  : {args.fps} fps (~{latency_ms}ms latency)")
    cal_status = "unify" if _spacecal_mode == "unify" else ("file present, mode=off" if _spacecal_config else "no file")
    print(f"  [OK] Space cal       : {cal_status}")
    anc_status = f"on ({_anchor_serial})" if _anchor_active else "off"
    print(f"  [OK] Anchor correct  : {anc_status}")

    _start_http()
    _start_map_watcher()

    async def _run():
        global _loop
        _loop = asyncio.get_event_loop()
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
