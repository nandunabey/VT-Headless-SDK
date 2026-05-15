"""
VUT Robotics SDK — quickstart
==============================
Prerequisite: vtrackerd_openvr.py must be running
  python C:\Users\vive_\Desktop\vtrackerd_openvr.py

Then run this file:
  python examples/quickstart.py
"""

from vut_sdk import VUTTracker

with VUTTracker() as tracker:
    pose = tracker.get_pose()

print(f"Tracker  : {pose.tracker_id}")
print(f"Position : {pose.pos}")
print(f"Rotation : {pose.euler}")
print(f"Status   : {pose.status}  @  {pose.packets_per_sec:.0f} fps")
