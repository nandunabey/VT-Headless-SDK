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
from .exceptions import DaemonNotRunning, PoseTimeout, TrackerNotFound

_DEFAULT_URL = "ws://localhost:8765"


class VUTTracker:
    """Live 6DoF pose stream from a single VIVE Ultimate Tracker.

    Connects to vtrackerd_openvr.py WebSocket daemon and exposes a
    clean synchronous API backed by a daemon asyncio thread.

    Usage (one-liner):
        with VUTTracker() as tracker:
            print(tracker.get_pose())

    Usage (explicit):
        tracker = VUTTracker()
        tracker.connect()
        pose = tracker.get_pose()
        tracker.disconnect()

    Args:
        tracker_id:  Serial ID of the tracker (e.g. '47-A33F01412').
                     None = first tracker seen in the stream.
        daemon_url:  WebSocket URL of vtrackerd_openvr.py (default ws://localhost:8765).
        auto_start:  If True, attempt to start the daemon automatically when
                     connect() is called and the port is not open.
    """

    def __init__(
        self,
        tracker_id: Optional[str] = None,
        daemon_url: str = _DEFAULT_URL,
        auto_start: bool = False,
    ):
        self._tracker_id = tracker_id
        self._url = daemon_url
        self._auto_start = auto_start

        self._latest: Optional[PoseData] = None
        self._callbacks: List[Callable[[PoseData], None]] = []
        self._lock = threading.Lock()
        self._connected_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self, timeout: float = 5.0) -> VUTTracker:
        """Connect to the daemon. Raises DaemonNotRunning if unreachable."""
        if self._auto_start:
            from .daemon import VUTDaemon
            d = VUTDaemon()
            if not d.is_running():
                d.start(wait=30.0)

        self._stop_event.clear()
        self._connected_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="vut-ws")
        self._thread.start()

        if not self._connected_event.wait(timeout):
            self._stop_event.set()
            raise DaemonNotRunning(
                f"Could not connect to VUT daemon at {self._url} within {timeout}s.\n"
                "Start it:  python C:\\Users\\vive_\\Desktop\\vtrackerd_openvr.py\n"
                "or pass auto_start=True to VUTTracker()."
            )
        return self

    def disconnect(self) -> None:
        """Stop the background WebSocket thread."""
        self._stop_event.set()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=3.0)

    def get_pose(self, timeout: float = 1.0) -> PoseData:
        """Return the latest valid pose. Raises PoseTimeout if none arrives in time."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._latest is not None:
                    return self._latest
            time.sleep(0.005)
        raise PoseTimeout(
            "No pose received within timeout.\n"
            "Check: tracker LED solid, SteamVR running, SLAM/VO map loaded."
        )

    def stream(self, rate_hz: float = 30.0) -> Generator[PoseData, None, None]:
        """Yield pose at up to rate_hz frames per second until disconnect() is called."""
        interval = 1.0 / rate_hz
        while not self._stop_event.is_set():
            t0 = time.monotonic()
            with self._lock:
                if self._latest is not None:
                    yield self._latest
            sleep = interval - (time.monotonic() - t0)
            if sleep > 0:
                time.sleep(sleep)

    def on_pose(self, callback: Callable[[PoseData], None]) -> None:
        """Register a callback invoked on every new valid pose update."""
        self._callbacks.append(callback)

    def is_connected(self) -> bool:
        return self._connected_event.is_set() and not self._stop_event.is_set()

    @property
    def tracker_id(self) -> Optional[str]:
        return self._tracker_id

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> VUTTracker:
        return self.connect()

    def __exit__(self, *_) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Background WebSocket loop (asyncio in a dedicated thread)
    # ------------------------------------------------------------------

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
                        if first_attempt and self._latest is not None:
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

        pose: Optional[PoseData] = None

        if msg.get("type") == "pose_multi":
            trackers = msg.get("trackers", [])
            if not trackers:
                return
            target = None
            for t in trackers:
                if self._tracker_id is None or t["id"] == self._tracker_id:
                    target = t
                    break
            if target is None:
                ids = [t["id"] for t in trackers]
                raise TrackerNotFound(
                    f"Tracker '{self._tracker_id}' not in stream. "
                    f"Available: {ids}"
                )
            if self._tracker_id is None:
                self._tracker_id = target["id"]
            pose = PoseData.from_ws_multi(target, msg)

        elif msg.get("type") == "pose":
            tid_in_msg = msg.get("stats", {}).get("tracker_id")
            if self._tracker_id is None or tid_in_msg == self._tracker_id:
                pose = PoseData.from_ws_single(msg)
                if self._tracker_id is None:
                    self._tracker_id = pose.tracker_id

        if pose and pose.valid:
            with self._lock:
                self._latest = pose
            for cb in self._callbacks:
                try:
                    cb(pose)
                except Exception:
                    pass


# ------------------------------------------------------------------
# CLI entry point: vut-pose
# ------------------------------------------------------------------

def pose_cli() -> None:
    """vut-pose: print live pose for the first tracker (Ctrl+C to stop)."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Stream live tracker pose to stdout.")
    parser.add_argument("--id", dest="tracker_id", default=None, help="Tracker serial ID")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Daemon WebSocket URL")
    parser.add_argument("--hz", type=float, default=10.0, help="Print rate Hz (default 10)")
    parser.add_argument("--once", action="store_true", help="Print one pose and exit")
    args = parser.parse_args()

    tracker = VUTTracker(tracker_id=args.tracker_id, daemon_url=args.url)
    try:
        tracker.connect()
    except DaemonNotRunning as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Streaming tracker: {tracker.tracker_id}  (Ctrl+C to stop)")
    try:
        for pose in tracker.stream(rate_hz=args.hz):
            e = pose.euler
            print(
                f"  pos=({pose.pos.x:+.3f}, {pose.pos.y:+.3f}, {pose.pos.z:+.3f})  "
                f"euler=(r={e.roll:.1f}° p={e.pitch:.1f}° y={e.yaw:.1f}°)  "
                f"{pose.packets_per_sec:.0f}fps"
            )
            if args.once:
                break
    except KeyboardInterrupt:
        pass
    finally:
        tracker.disconnect()
