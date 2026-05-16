#!/usr/bin/env python3
"""
probe_tracker_identity.py

Standalone probe — dumps every identity, role, and input-binding property
available from OpenVR for each GenericTracker device found in SteamVR.

Requires: SteamVR running  +  pip install openvr
Run:      python probe_tracker_identity.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import openvr


# ── helpers ──────────────────────────────────────────────────────────────────

def _str_prop(vr, idx, prop):
    try:
        return vr.getStringTrackedDeviceProperty(idx, prop)
    except Exception as exc:
        return f"<{exc}>"

def _int_prop(vr, idx, prop):
    try:
        return vr.getInt32TrackedDeviceProperty(idx, prop)
    except Exception as exc:
        return f"<{exc}>"

def _bool_prop(vr, idx, prop):
    try:
        return vr.getBoolTrackedDeviceProperty(idx, prop)
    except Exception as exc:
        return f"<{exc}>"

def _safe_const(name):
    """Return openvr constant by name, or None if the binding doesn't expose it."""
    return getattr(openvr, name, None)


# ── section 1: per-tracker property dump ─────────────────────────────────────

STRING_PROPS = [
    ("SerialNumber",          "Prop_SerialNumber_String"),
    ("ModelNumber",           "Prop_ModelNumber_String"),
    ("RenderModelName",       "Prop_RenderModelName_String"),
    ("ManufacturerName",      "Prop_ManufacturerName_String"),
    ("TrackingSystemName",    "Prop_TrackingSystemName_String"),
    ("InputProfilePath",      "Prop_InputProfilePath_String"),
    ("AttachedDeviceId",      "Prop_AttachedDeviceId_String"),
    ("ModeLabel",             "Prop_ModeLabel_String"),
]

INT_PROPS = [
    ("ControllerRoleHint",    "Prop_ControllerRoleHint_Int32"),
    ("DeviceClass",           "Prop_DeviceClass_Int32"),
]

BOOL_PROPS = [
    ("DeviceIsWireless",      "Prop_DeviceIsWireless_Bool"),
    ("DeviceCanPowerOff",     "Prop_DeviceCanPowerOff_Bool"),
]

# Map ETrackedControllerRole int → label (for readability)
ROLE_LABELS = {
    0: "Invalid",
    1: "LeftHand",
    2: "RightHand",
    3: "OptOut",
    4: "Treadmill",
    5: "Stylus",
}

def probe_trackers(vr):
    print("=" * 64)
    print("SECTION 1 — GenericTracker device properties")
    print("=" * 64)

    serials = []
    found   = 0

    for i in range(openvr.k_unMaxTrackedDeviceCount):
        if vr.getTrackedDeviceClass(i) != openvr.TrackedDeviceClass_GenericTracker:
            continue

        found += 1
        print(f"\n  Device index: {i}")
        print(f"  {'─' * 56}")

        for label, const_name in STRING_PROPS:
            const = _safe_const(const_name)
            if const is None:
                print(f"  {label:<26} <constant not in this openvr build>")
                continue
            val = _str_prop(vr, i, const)
            print(f"  {label:<26} {val}")
            if label == "SerialNumber" and not val.startswith("<"):
                serials.append((i, val))

        for label, const_name in INT_PROPS:
            const = _safe_const(const_name)
            if const is None:
                print(f"  {label:<26} <constant not in this openvr build>")
                continue
            val = _int_prop(vr, i, const)
            if label == "ControllerRoleHint" and isinstance(val, int):
                val = f"{val}  ({ROLE_LABELS.get(val, 'unknown')})"
            print(f"  {label:<26} {val}")

        for label, const_name in BOOL_PROPS:
            const = _safe_const(const_name)
            if const is None:
                print(f"  {label:<26} <constant not in this openvr build>")
                continue
            val = _bool_prop(vr, i, const)
            print(f"  {label:<26} {val}")

    if found == 0:
        print("\n  No GenericTracker devices found.")
        print("  Is SteamVR running with trackers active?")

    print(f"\n  Total GenericTrackers: {found}")
    return serials


# ── section 2: IVRSettings — tracker role assignments ────────────────────────

def probe_settings(serials):
    print("\n" + "=" * 64)
    print("SECTION 2 — IVRSettings (tracker role assignments)")
    print("=" * 64)

    try:
        s = openvr.IVRSettings()
    except Exception as exc:
        print(f"\n  IVRSettings() failed: {exc}")
        return

    # SteamVR stores tracker role assignments in the "trackers" section.
    # Keys are device paths; values are role strings ("waist", "chest", etc.)
    # Try the discovered serial numbers as well as known key patterns.
    keys_to_try = []

    for _, serial in serials:
        keys_to_try += [
            ("trackers", f"/devices/htc/vive_tracker{serial}"),
            ("trackers", f"/devices/htc/vive_trackerLHR-{serial}"),
            ("trackers", serial),
        ]

    # Also try generic section keys
    keys_to_try += [
        ("trackers",    "enabled"),
        ("steamvr",     "activateMultipleDrivers"),
        ("driver_vive", "enable"),
    ]

    print()
    for section, key in keys_to_try:
        try:
            val = s.getString(section, key)
            print(f"  [{section}]  {key}  =  {val!r}")
        except Exception as exc:
            print(f"  [{section}]  {key}  ->  <{exc}>")


# ── section 3: IVRInput — role handle enumeration ────────────────────────────

# All known VIVE tracker role paths in SteamVR's input system
TRACKER_ROLE_PATHS = [
    "/user/vive_tracker_waist",
    "/user/vive_tracker_chest",
    "/user/vive_tracker_camera",
    "/user/vive_tracker_keyboard",
    "/user/vive_tracker_left_foot",
    "/user/vive_tracker_right_foot",
    "/user/vive_tracker_left_elbow",
    "/user/vive_tracker_right_elbow",
    "/user/vive_tracker_left_knee",
    "/user/vive_tracker_right_knee",
    "/user/vive_tracker_left_shoulder",
    "/user/vive_tracker_right_shoulder",
    "/user/vive_tracker_handheld_object_left",
    "/user/vive_tracker_handheld_object_right",
]

def probe_input():
    print("\n" + "=" * 64)
    print("SECTION 3 — IVRInput (tracker role → device handle)")
    print("=" * 64)

    try:
        inp = openvr.IVRInput()
    except Exception as exc:
        print(f"\n  IVRInput() failed: {exc}")
        return

    print()
    for path in TRACKER_ROLE_PATHS:
        try:
            handle = inp.getInputSourceHandle(path)
            # Try to resolve handle back to a tracked device index
            try:
                info = inp.getOriginTrackedDeviceInfo(handle, 0)
                device_idx = getattr(info, "trackedDeviceIndex", "?")
                extra = f"  device_index={device_idx}"
            except Exception as detail:
                extra = f"  (getOriginTrackedDeviceInfo: {detail})"
            print(f"  {path}")
            print(f"    handle={handle:#018x}{extra}")
        except Exception as exc:
            print(f"  {path}")
            print(f"    <{exc}>")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   probe_tracker_identity.py — VUT tracker property dump      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    print("Initialising OpenVR (VRApplication_Background)...")
    try:
        vr = openvr.init(openvr.VRApplication_Background)
        print("  OK\n")
    except Exception as exc:
        print(f"  FAILED: {exc}")
        print("  Make sure SteamVR is running before running this probe.")
        sys.exit(1)

    try:
        serials = probe_trackers(vr)
        probe_settings(serials)
        probe_input()
    finally:
        openvr.shutdown()

    print("\n" + "=" * 64)
    print("Probe complete.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    main()
