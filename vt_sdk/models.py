from __future__ import annotations
import math
import time as _time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __repr__(self) -> str:
        return f"Vec3(x={self.x:+.4f}, y={self.y:+.4f}, z={self.z:+.4f})"

    def distance_to(self, other: Vec3) -> float:
        """Euclidean distance in metres."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

    def direction_to(self, other: Vec3) -> float:
        """Horizontal bearing from self to other in degrees (0=+Z axis, clockwise).

        Uses the XZ plane — SteamVR coordinate system (Y is up).
        Returns a value in [0, 360).
        """
        dx = other.x - self.x
        dz = other.z - self.z
        angle = math.degrees(math.atan2(dx, dz))
        return angle % 360.0

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class EulerAngles:
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def __repr__(self) -> str:
        return f"EulerAngles(roll={self.roll:.1f}°, pitch={self.pitch:.1f}°, yaw={self.yaw:.1f}°)"

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.roll, self.pitch, self.yaw)


@dataclass
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __repr__(self) -> str:
        return f"Quaternion(w={self.w:.6f}, x={self.x:.6f}, y={self.y:.6f}, z={self.z:.6f})"

    def to_euler(self) -> EulerAngles:
        """Convert to Euler angles. SteamVR right-handed coordinate system."""
        sinr_cosp = 2 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1 - 2 * (self.x**2 + self.y**2)
        roll = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

        # clamp avoids asin domain error from floating-point drift past ±1
        sinp = max(-1.0, min(1.0, 2 * (self.w * self.y - self.z * self.x)))
        pitch = math.degrees(math.asin(sinp))

        siny_cosp = 2 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1 - 2 * (self.y**2 + self.z**2)
        yaw = math.degrees(math.atan2(siny_cosp, cosy_cosp))

        return EulerAngles(roll=roll, pitch=pitch, yaw=yaw)

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.w, self.x, self.y, self.z)


@dataclass
class PoseData:
    tracker_id: str
    pos: Vec3
    rot: Quaternion
    timestamp_ms: int
    frame_id: int
    valid: bool
    trajectory: List[Vec3] = field(default_factory=list)
    packets_per_sec: float = 0.0
    status: str = "waiting"

    @property
    def euler(self) -> EulerAngles:
        return self.rot.to_euler()

    @property
    def age_ms(self) -> int:
        """Milliseconds since this pose was captured."""
        return int(_time.time() * 1000) - self.timestamp_ms

    def is_stale(self, threshold_ms: int = 200) -> bool:
        """True if the pose is older than threshold_ms milliseconds."""
        return self.age_ms > threshold_ms

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict of this pose."""
        e = self.euler
        return {
            "tracker_id": self.tracker_id,
            "pos": {"x": self.pos.x, "y": self.pos.y, "z": self.pos.z},
            "rot": {"w": self.rot.w, "x": self.rot.x, "y": self.rot.y, "z": self.rot.z},
            "euler": {"roll": e.roll, "pitch": e.pitch, "yaw": e.yaw},
            "timestamp_ms": self.timestamp_ms,
            "frame_id": self.frame_id,
            "valid": self.valid,
            "status": self.status,
            "packets_per_sec": self.packets_per_sec,
        }

    def __repr__(self) -> str:
        e = self.euler
        return (
            f"PoseData(id={self.tracker_id!r}, pos={self.pos}, "
            f"euler={e}, valid={self.valid}, {self.packets_per_sec:.0f}fps)"
        )

    @classmethod
    def from_ws_multi(cls, tracker_d: dict, msg: dict) -> PoseData:
        """Build from a tracker entry inside a pose_multi WebSocket message."""
        tid = tracker_d["id"]
        pos = Vec3(tracker_d["pos"]["x"], tracker_d["pos"]["y"], tracker_d["pos"]["z"])
        r = tracker_d["rot"]
        rot = Quaternion(r["w"], r["x"], r["y"], r["z"])
        traj_raw = msg.get("trajectories", {}).get(tid, [])
        traj = [Vec3(p["x"], p["y"], p["z"]) for p in traj_raw]
        stats = msg.get("stats", {})
        return cls(
            tracker_id=tid,
            pos=pos,
            rot=rot,
            timestamp_ms=msg.get("timestamp", 0),
            frame_id=msg.get("frame_id", 0),
            valid=tracker_d.get("valid", False),
            trajectory=traj,
            packets_per_sec=stats.get("packets_per_sec", 0.0),
            status="tracking" if tracker_d.get("valid") else "waiting",
        )

    @classmethod
    def from_ws_single(cls, msg: dict) -> PoseData:
        """Build from a backwards-compat single-tracker 'pose' WebSocket message."""
        pos = Vec3(msg["pos"]["x"], msg["pos"]["y"], msg["pos"]["z"])
        r = msg["rot"]
        rot = Quaternion(r["w"], r["x"], r["y"], r["z"])
        traj = [Vec3(p["x"], p["y"], p["z"]) for p in msg.get("trajectory", [])]
        stats = msg.get("stats", {})
        return cls(
            tracker_id=stats.get("tracker_id", "unknown"),
            pos=pos,
            rot=rot,
            timestamp_ms=msg.get("timestamp", 0),
            frame_id=msg.get("frame_id", 0),
            valid=stats.get("status") == "tracking",
            trajectory=traj,
            packets_per_sec=stats.get("packets_per_sec", 0.0),
            status=stats.get("status", "waiting"),
        )
