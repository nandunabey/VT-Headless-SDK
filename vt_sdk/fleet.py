from __future__ import annotations
import asyncio
import json
import threading
import time
from typing import Callable, Dict, Generator, List, Optional

try:
    import websockets
    import websockets.exceptions as _ws_exc
except ImportError:
    raise ImportError("websockets not installed — run: pip install websockets>=16.0")

from .models import PoseData
from .exceptions import DaemonNotRunning, PoseTimeout

_DEFAULT_URL = "ws://localhost:8765"


class VUTTrackerFleet:
    """Live 6DoF pose stream from all connected VIVE Ultimate Trackers simultaneously.

    Usage:
        with VUTTrackerFleet() as fleet:
            poses = fleet.get_all_poses()
            for tracker_id, pose in poses.items():
                print(tracker_id, pose.pos)
    """

    def __init__(self, daemon_url: str = _DEFAULT_URL, auto_start: bool = False):
        self._url = daemon_url
        self._auto_start = auto_start
        self._poses: Dict[str, PoseData] = {}
        self._callbacks: List[Callable[[Dict[str, PoseData]], None]] = []
        self._lock = threading.Lock()
        self._connected_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def connect(self, timeout: float = 5.0) -> VUTTrackerFleet:
        if self._auto_start:
            from .daemon import VUTDaemon
            d = VUTDaemon()
            if not d.is_running():
                d.start(wait=30.0)

        self._stop_event.clear()
        self._connected_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="vut-fleet-ws")
        self._thread.start()
        if not self._connected_event.wait(timeout):
            self._stop_event.set()
            raise DaemonNotRunning(
                f"Could not connect to VUT daemon at {self._url} within {timeout}s.\n"
                "Start it:  python C:\\Users\\vive_\\Desktop\\vtrackerd_openvr.py"
            )
        return self

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=3.0)

    def get_all_poses(self, timeout: float = 1.0) -> Dict[str, PoseData]:
        """Return {tracker_id: PoseData} for all active trackers."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._poses:
                    return dict(self._poses)
            time.sleep(0.005)
        raise PoseTimeout(
            "No pose data received from any tracker.\n"
            "Check: SteamVR running, tracker LEDs solid, daemon broadcasting."
        )

    def get_tracker(self, tracker_id: str) -> Optional[PoseData]:
        with self._lock:
            return self._poses.get(tracker_id)

    @property
    def tracker_ids(self) -> List[str]:
        with self._lock:
            return list(self._poses.keys())

    def stream_all(self, rate_hz: float = 30.0) -> Generator[Dict[str, PoseData], None, None]:
        """Yield {tracker_id: PoseData} at up to rate_hz fps until disconnect() is called."""
        interval = 1.0 / rate_hz
        while not self._stop_event.is_set():
            t0 = time.monotonic()
            with self._lock:
                if self._poses:
                    yield dict(self._poses)
            sleep = interval - (time.monotonic() - t0)
            if sleep > 0:
                time.sleep(sleep)

    def on_update(self, callback: Callable[[Dict[str, PoseData]], None]) -> None:
        """Register a callback invoked on every fleet pose update."""
        self._callbacks.append(callback)

    def is_connected(self) -> bool:
        return self._connected_event.is_set() and not self._stop_event.is_set()

    def __enter__(self) -> VUTTrackerFleet:
        return self.connect()

    def __exit__(self, *_) -> None:
        self.disconnect()

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._ws_client())
        finally:
            self._loop.close()

    async def _ws_client(self) -> None:
        first_attempt = True
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self._url, open_timeout=4.0) as ws:
                    while not self._stop_event.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        except asyncio.TimeoutError:
                            continue
                        except _ws_exc.ConnectionClosed:
                            break
                        self._handle_message(raw)
                        if first_attempt and self._poses:
                            first_attempt = False
                            self._connected_event.set()
            except (OSError, _ws_exc.WebSocketException):
                if first_attempt:
                    await asyncio.sleep(0.1)
                    continue
                if not self._stop_event.is_set():
                    await asyncio.sleep(2.0)
            except Exception:
                if first_attempt:
                    self._connected_event.set()
                return

    def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        if msg.get("type") != "pose_multi":
            return
        updated: Dict[str, PoseData] = {}
        for t in msg.get("trackers", []):
            if t.get("valid"):
                pose = PoseData.from_ws_multi(t, msg)
                updated[pose.tracker_id] = pose
        if updated:
            with self._lock:
                self._poses.update(updated)
            for cb in self._callbacks:
                try:
                    cb(dict(updated))
                except Exception:
                    pass
