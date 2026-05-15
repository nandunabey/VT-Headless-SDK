"""VUT Robotics SDK — Headless 6DoF spatial tracking for VIVE Ultimate Tracker.

Built by Nandun Abeywickrama, Head of Product ANZ, HTC VIVE.

Quickstart:
    from vut_sdk import VUTTracker

    with VUTTracker() as tracker:
        pose = tracker.get_pose()
        print(pose)

Fleet (all trackers):
    from vut_sdk import VUTTrackerFleet

    with VUTTrackerFleet() as fleet:
        for tid, pose in fleet.get_all_poses().items():
            print(tid, pose.pos)
"""

from .exceptions import (
    VUTError,
    DaemonNotRunning,
    TrackerNotFound,
    SteamVRNotRunning,
    VIVEHubNotRunning,
    PoseTimeout,
    # legacy aliases
    VUTConnectionError,
    VUTTrackerNotFoundError,
    VUTTimeoutError,
    VUTSteamVRNotRunningError,
    VUTHubNotRunningError,
)
from .models import EulerAngles, PoseData, Quaternion, Vec3
from .tracker import VUTTracker
from .fleet import VUTTrackerFleet
from .daemon import VUTDaemon

__version__ = "0.1.0"
__author__ = "Nandun Abeywickrama"

__all__ = [
    # Core classes
    "VUTTracker",
    "VUTTrackerFleet",
    "VUTDaemon",
    # Data models
    "PoseData",
    "Vec3",
    "Quaternion",
    "EulerAngles",
    # Exceptions
    "VUTError",
    "DaemonNotRunning",
    "TrackerNotFound",
    "SteamVRNotRunning",
    "VIVEHubNotRunning",
    "PoseTimeout",
]
