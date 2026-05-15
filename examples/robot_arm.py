"""
VUT Robotics SDK — robot_arm
==============================
End-effector tracking example.
Streams position and orientation of a tracker mounted on a robot arm.

Run:
  python examples/robot_arm.py --id 47-A33F01412
"""

import argparse
import sys
import time
from vut_sdk import VUTTracker, DaemonNotRunning, PoseTimeout

parser = argparse.ArgumentParser(description="Robot arm end-effector tracking.")
parser.add_argument("--id", dest="tracker_id", default=None, help="Tracker serial ID")
parser.add_argument("--hz", type=float, default=30.0, help="Streaming rate Hz")
args = parser.parse_args()

tracker = VUTTracker(tracker_id=args.tracker_id)
try:
    tracker.connect()
except DaemonNotRunning as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

print(f"End-effector tracker: {tracker.tracker_id}")
print("Streaming (Ctrl+C to stop)\n")

prev_pos = None
try:
    for pose in tracker.stream(rate_hz=args.hz):
        p = pose.pos
        e = pose.euler

        dist = ""
        if prev_pos is not None:
            d = prev_pos.distance_to(p)
            dist = f"  delta={d*1000:.1f}mm"
        prev_pos = p

        print(
            f"  pos=({p.x:+.4f}, {p.y:+.4f}, {p.z:+.4f})  "
            f"roll={e.roll:.1f}°  pitch={e.pitch:.1f}°  yaw={e.yaw:.1f}°"
            f"{dist}"
        )
except KeyboardInterrupt:
    pass
finally:
    tracker.disconnect()
