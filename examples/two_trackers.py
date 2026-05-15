"""
VUT Robotics SDK — two_trackers
=================================
Live pose from both trackers printed at 10 Hz.

Run:
  python examples/two_trackers.py
"""

import time
from vut_sdk import VUTTrackerFleet

with VUTTrackerFleet() as fleet:
    print(f"Trackers detected: {fleet.tracker_ids}")
    print("Streaming at 10 Hz — Ctrl+C to stop\n")

    try:
        while True:
            poses = fleet.get_all_poses()
            for tid, pose in poses.items():
                p = pose.pos
                e = pose.euler
                print(f"[{tid}]  pos=({p.x:+.3f}, {p.y:+.3f}, {p.z:+.3f})  "
                      f"yaw={e.yaw:.1f}°")
            print()
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
