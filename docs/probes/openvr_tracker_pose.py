import openvr
import time
import math

def mat34_to_pos_rot(mat):
    """Extract position and rotation from OpenVR HmdMatrix34_t."""
    pos = (mat[0][3], mat[1][3], mat[2][3])
    # Rotation matrix to euler (yaw/pitch/roll in degrees)
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -mat[1][2]))))
    yaw   = math.degrees(math.atan2(mat[0][2], mat[2][2]))
    roll  = math.degrees(math.atan2(mat[1][0], mat[1][1]))
    return pos, (yaw, pitch, roll)

print("Initialising OpenVR...")
try:
    vr = openvr.init(openvr.VRApplication_Background)
    print(f"  OK")
except Exception as e:
    print(f"  FAILED: {e}")
    raise SystemExit(1)

# Find all tracked devices
print("\nEnumerating devices:")
found_trackers = []
for i in range(openvr.k_unMaxTrackedDeviceCount):
    cls = vr.getTrackedDeviceClass(i)
    if cls == openvr.TrackedDeviceClass_Invalid:
        continue
    role = vr.getControllerRoleForTrackedDeviceIndex(i)
    try:
        serial = vr.getStringTrackedDeviceProperty(i, openvr.Prop_SerialNumber_String)
        model  = vr.getStringTrackedDeviceProperty(i, openvr.Prop_ModelNumber_String)
    except Exception:
        serial, model = "?", "?"
    cls_name = {
        openvr.TrackedDeviceClass_HMD:        "HMD",
        openvr.TrackedDeviceClass_Controller:  "Controller",
        openvr.TrackedDeviceClass_GenericTracker: "Tracker",
        openvr.TrackedDeviceClass_TrackingReference: "Base Station",
    }.get(cls, f"class{cls}")
    print(f"  [{i}] {cls_name}  serial={serial}  model={model}")
    if cls == openvr.TrackedDeviceClass_GenericTracker:
        found_trackers.append(i)

if not found_trackers:
    print("\nNo Generic Trackers found. Waiting 10s for tracker to register...")
    deadline = time.time() + 10
    while time.time() < deadline:
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            if vr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_GenericTracker:
                if i not in found_trackers:
                    found_trackers.append(i)
                    print(f"  Tracker appeared: index {i}")
        if found_trackers:
            break
        time.sleep(0.5)

if not found_trackers:
    print("No trackers appeared. Check SteamVR and ViveTrackerServer.")
    openvr.shutdown()
    raise SystemExit(1)

idx = found_trackers[0]
print(f"\nStreaming pose for tracker index {idx} (30 seconds) ...")
print("Move the tracker around!\n")

count = 0
deadline = time.time() + 60
last_print = 0

while time.time() < deadline:
    # Use IVRSystem directly — no HMD/Compositor needed
    poses = vr.getDeviceToAbsoluteTrackingPose(
        openvr.TrackingUniverseRawAndUncalibrated, 0,
        openvr.k_unMaxTrackedDeviceCount
    )
    pose = poses[idx]

    if pose.bPoseIsValid and pose.eTrackingResult == openvr.TrackingResult_Running_OK:
        pos, rot = mat34_to_pos_rot(pose.mDeviceToAbsoluteTracking)
        count += 1
        now = time.time()
        if now - last_print >= 0.1:
            print(f"  pos=({pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:+.3f})  "
                  f"yaw={rot[0]:+.1f} pitch={rot[1]:+.1f} roll={rot[2]:+.1f}  "
                  f"[{count} samples]", end="\r")
            last_print = now
    else:
        status = {
            openvr.TrackingResult_Uninitialized: "Uninitialized",
            openvr.TrackingResult_Calibrating_InProgress: "Calibrating",
            openvr.TrackingResult_Calibrating_OutOfRange: "OutOfRange",
            openvr.TrackingResult_Running_OK: "OK",
            openvr.TrackingResult_Running_OutOfRange: "OutOfRange(running)",
        }.get(pose.eTrackingResult, str(pose.eTrackingResult))
        print(f"  waiting... valid={pose.bPoseIsValid} status={status}           ", end="\r")

    time.sleep(0.01)

print(f"\n\nDone. Total valid pose samples: {count}")
openvr.shutdown()
