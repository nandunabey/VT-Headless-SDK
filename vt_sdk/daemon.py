from __future__ import annotations
import argparse
import base64
import json as _json
import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

_DEFAULT_SCRIPT = Path.home() / "Desktop" / "vtrackerd_openvr.py"
_WS_PORT = 8765


class VUTDaemon:
    """Manages the vtrackerd_openvr.py daemon process lifecycle.

    Usage:
        daemon = VUTDaemon()
        daemon.start()          # blocks until WebSocket port is ready
        print(daemon.status())
        daemon.stop()
    """

    def __init__(self, script_path: Optional[Path] = None):
        self._script = Path(script_path) if script_path else _DEFAULT_SCRIPT
        self._proc: Optional[subprocess.Popen] = None

    def start(self, wait: float = 30.0) -> None:
        """Start the daemon if not already running. Waits up to wait seconds."""
        if self.is_running():
            return
        if not self._script.exists():
            raise FileNotFoundError(
                f"Daemon script not found: {self._script}\n"
                "Ensure vtrackerd_openvr.py is on the Desktop or pass script_path=."
            )
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        self._proc = subprocess.Popen(
            [sys.executable, str(self._script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            if self._port_open():
                return
            if self._proc.poll() is not None:
                raise RuntimeError("Daemon process exited unexpectedly. Check SteamVR and VHConsole are running.")
            time.sleep(0.5)
        raise TimeoutError(
            f"Daemon started but port {_WS_PORT} not open after {wait}s.\n"
            "Is SteamVR running? Is VHConsole.exe running?"
        )

    def stop(self) -> None:
        """Terminate the managed daemon process."""
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def is_running(self) -> bool:
        """True if something is listening on the daemon WebSocket port."""
        return self._port_open()

    def status(self) -> Dict:
        """Return a health-check dict for all required services."""
        port_open = self._port_open()
        return {
            "daemon_port_open":    port_open,
            "daemon_ws_reachable": self._ws_reachable() if port_open else False,
            "managed_proc_alive":  self._proc is not None and self._proc.poll() is None,
            "steamvr_running":     self._proc_running("vrserver.exe"),
            "vhconsole_running":   self._proc_running("VHConsole.exe"),
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _port_open(host: str = "localhost", port: int = _WS_PORT, timeout: float = 0.5) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    @staticmethod
    def _ws_reachable(host: str = "127.0.0.1", port: int = _WS_PORT, timeout: float = 3.0) -> bool:
        """Raw TCP WebSocket upgrade handshake — no websockets library, stdlib only.

        Avoids any conflict between the bundled websockets in the PyInstaller exe
        and the websockets server running inside vtrackerd_openvr.py.
        Returns True if the server responds with 101 Switching Protocols.
        """
        try:
            key = base64.b64encode(os.urandom(16)).decode()
            handshake = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.sendall(handshake.encode())
                response = sock.recv(1024).decode(errors="ignore")
                return "101 Switching Protocols" in response
        except Exception:
            return False

    @staticmethod
    def _recv_pose_raw(
        host: str = "127.0.0.1",
        port: int = _WS_PORT,
        timeout: float = 5.0,
    ) -> Optional[dict]:
        """Raw WebSocket receive — handshake + frame parser, no websockets library.

        Returns the first pose_multi message from the daemon, or None on
        failure/timeout. Uses only stdlib: socket, struct, base64, os, json.
        """
        try:
            key = base64.b64encode(os.urandom(16)).decode()
            handshake = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.settimeout(timeout)
                sock.sendall(handshake.encode())

                # Read HTTP 101 response
                resp = bytearray()
                while b"\r\n\r\n" not in resp:
                    chunk = sock.recv(4096)
                    if not chunk:
                        return None
                    resp.extend(chunk)
                if b"101" not in resp:
                    return None

                # Any bytes received after the HTTP headers are WS frame data
                split = bytes(resp).index(b"\r\n\r\n") + 4
                buf = bytearray(resp[split:])

                def _recv_exact(n: int) -> bytes:
                    while len(buf) < n:
                        chunk = sock.recv(4096)
                        if not chunk:
                            raise ConnectionError("socket closed")
                        buf.extend(chunk)
                    data = bytes(buf[:n])
                    del buf[:n]
                    return data

                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    hdr = _recv_exact(2)
                    opcode = hdr[0] & 0x0f
                    masked = bool(hdr[1] & 0x80)
                    plen = hdr[1] & 0x7f

                    if plen == 126:
                        plen = struct.unpack(">H", _recv_exact(2))[0]
                    elif plen == 127:
                        plen = struct.unpack(">Q", _recv_exact(8))[0]

                    mask_key = _recv_exact(4) if masked else b""
                    payload = bytearray(_recv_exact(plen))
                    if masked:
                        for i in range(len(payload)):
                            payload[i] ^= mask_key[i % 4]

                    if opcode == 8:  # close frame
                        return None
                    if opcode == 1:  # text frame
                        try:
                            msg = _json.loads(payload.decode("utf-8"))
                            if msg.get("type") == "pose_multi":
                                return msg
                        except Exception:
                            pass
        except Exception:
            return None
        return None

    @staticmethod
    def _proc_running(name: str) -> bool:
        if sys.platform != "win32":
            return False
        result = subprocess.run(
            ["tasklist", "/fi", f"imagename eq {name}", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
        )
        return name.lower() in result.stdout.lower()


# ------------------------------------------------------------------
# CLI entry points
# ------------------------------------------------------------------

def cli() -> None:
    """vut-daemon: start, stop, or check the VUT daemon."""
    parser = argparse.ArgumentParser(description="VUT daemon manager.")
    parser.add_argument("command", choices=["start", "stop", "status"])
    parser.add_argument("--script", help="Path to vtrackerd_openvr.py")
    args = parser.parse_args()

    daemon = VUTDaemon(script_path=args.script)

    if args.command == "start":
        print("Starting VUT daemon...")
        try:
            daemon.start()
            print(f"  OK — daemon listening on ws://localhost:{_WS_PORT}")
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "stop":
        daemon.stop()
        print("Daemon stopped.")

    elif args.command == "status":
        info = daemon.status()
        print("VUT Daemon Status")
        for k, v in info.items():
            print(f"  {k:<25}: {'yes' if v else 'no'}")


def status_cli() -> None:
    """vut-status: full health check — services, daemon, live trackers."""
    daemon = VUTDaemon()
    info = daemon.status()

    ok  = lambda v: "OK " if v else "NO "

    print("VUT Robotics SDK — Status Check")
    print("=" * 42)
    print(f"  VIVE Hub  (VHConsole.exe)  [{ok(info['vhconsole_running'])}]")
    print(f"  SteamVR   (vrserver.exe)   [{ok(info['steamvr_running'])}]")
    print(f"  Daemon    (port 8765)      [{ok(info['daemon_ws_reachable'])}]")
    print()

    if not info["daemon_port_open"]:
        print("  Daemon not running. Start with:")
        print("    python C:\\Users\\vive_\\Desktop\\vtrackerd_openvr.py")
        print("  or:  vut-daemon start")
        sys.exit(1)

    if not info["daemon_ws_reachable"]:
        print("  Port 8765 is open but the WebSocket handshake failed or no data arrived.")
        print("  Check: SteamVR running, trackers plugged in, LEDs solid.")
        sys.exit(1)

    print("  Reading live tracker data ...")
    msg = VUTDaemon._recv_pose_raw()
    if msg is None:
        print("  Daemon is reachable but no tracker pose received within timeout.")
        print("  Check: tracker LEDs solid, SLAM/VO map loaded.")
        sys.exit(1)

    trackers = msg.get("trackers", [])
    valid = [t for t in trackers if t.get("valid")]
    stats = msg.get("stats", {})

    print(f"  Trackers: {len(valid)} active / {len(trackers)} total")
    for t in valid:
        p = t["pos"]
        r = t["rot"]
        from .models import Quaternion
        e = Quaternion(r["w"], r["x"], r["y"], r["z"]).to_euler()
        print(f"    [{t['id']}]")
        print(f"      pos  : ({p['x']:+.3f}, {p['y']:+.3f}, {p['z']:+.3f}) m")
        print(f"      euler: roll={e.roll:.1f}°  pitch={e.pitch:.1f}°  yaw={e.yaw:.1f}°")
    print(f"  Rate : {stats.get('packets_per_sec', 0):.0f} fps  |  frame {msg.get('frame_id', '?')}")
    print()
    print("  All systems operational.")
