#!/usr/bin/env python3
"""
probe_openxr.py

Standalone probe — determines whether VIVE Ultimate Tracker poses are
accessible via OpenXR in a headless Python process (no Unity, no HMD).

Requires: SteamVR running and set as OpenXR runtime
Install:  pip install pyopenxr
Run:      python probe_openxr.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Probe targets ─────────────────────────────────────────────────────────────

WANTED_EXTENSIONS = [
    "XR_EXT_hand_tracking",
    "XR_HTCX_vive_tracker_interaction",
    "XR_MND_headless",
]

# Known VIVE tracker role paths (XR_HTCX_vive_tracker_interaction)
TRACKER_ROLE_PATHS = [
    "/user/vive_tracker_htcx/role/waist",
    "/user/vive_tracker_htcx/role/chest",
    "/user/vive_tracker_htcx/role/camera",
    "/user/vive_tracker_htcx/role/keyboard",
    "/user/vive_tracker_htcx/role/left_foot",
    "/user/vive_tracker_htcx/role/right_foot",
    "/user/vive_tracker_htcx/role/left_elbow",
    "/user/vive_tracker_htcx/role/right_elbow",
    "/user/vive_tracker_htcx/role/left_knee",
    "/user/vive_tracker_htcx/role/right_knee",
    "/user/vive_tracker_htcx/role/left_shoulder",
    "/user/vive_tracker_htcx/role/right_shoulder",
    "/user/vive_tracker_htcx/role/handheld_object_left",
    "/user/vive_tracker_htcx/role/handheld_object_right",
]

# ── Result accumulator ────────────────────────────────────────────────────────

_results: dict = {
    "pyopenxr":  (False, "not attempted"),
    "instance":  (False, "not attempted"),
    "htcx":      (False, "not attempted"),
    "headless":  (False, "not attempted"),
    "poses":     (False, "not attempted"),
}

def _sep(title: str = "") -> None:
    if title:
        print(f"\n{'─' * 64}")
        print(f"  {title}")
        print(f"{'─' * 64}")
    else:
        print("─" * 64)

def _ok(flag: bool) -> str:
    return "[OK]  " if flag else "[FAIL]"


# ── Header ────────────────────────────────────────────────────────────────────

print()
print("╔══════════════════════════════════════════════════════════════╗")
print("║   probe_openxr.py — VIVE Ultimate Tracker OpenXR probe       ║")
print("╚══════════════════════════════════════════════════════════════╝")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Import pyopenxr
# ─────────────────────────────────────────────────────────────────────────────
_sep("STEP 1 — Import pyopenxr")

xr = None
try:
    import xr as _xr
    xr = _xr
    ver = getattr(xr, "__version__", "unknown")
    print(f"  [OK]  import xr  (pyopenxr {ver})")
    _results["pyopenxr"] = (True, f"pyopenxr {ver}")
except ImportError as exc:
    print(f"  [FAIL] import xr  →  {exc}")
    print()
    print("  pyopenxr is not installed.  Run:")
    print("    pip install pyopenxr")
    print()
    print("  Attempting auto-install...")
    try:
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyopenxr"],
            check=True, capture_output=True,
        )
        import xr as _xr
        xr = _xr
        ver = getattr(xr, "__version__", "unknown")
        print(f"  [OK]  installed and imported pyopenxr {ver}")
        _results["pyopenxr"] = (True, f"pyopenxr {ver} (auto-installed)")
    except Exception as exc2:
        print(f"  [FAIL] auto-install failed: {exc2}")
        _results["pyopenxr"] = (False, str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Enumerate available OpenXR extensions
# ─────────────────────────────────────────────────────────────────────────────

available_exts: set = set()
instance = None
session  = None

if xr is not None:
    _sep("STEP 2 — Enumerate available OpenXR extensions")

    try:
        ext_props = xr.enumerate_instance_extension_properties()
        print(f"  {len(ext_props)} extension(s) reported by runtime:\n")
        for ep in sorted(ext_props, key=lambda e: bytes(e.extension_name)):
            name = bytes(ep.extension_name).rstrip(b"\x00").decode(errors="replace")
            available_exts.add(name)
            tag  = "  ◄ probe target" if name in WANTED_EXTENSIONS else ""
            print(f"    {name}  (v{ep.extension_version}){tag}")
    except Exception as exc:
        print(f"  [FAIL] enumerate_instance_extension_properties: {exc}")
        print("         Is SteamVR running and set as the OpenXR runtime?")

    print()
    for ext in WANTED_EXTENSIONS:
        tag = "[OK] " if ext in available_exts else "[FAIL]"
        print(f"  {tag}  {ext}")

    htcx_avail     = "XR_HTCX_vive_tracker_interaction" in available_exts
    headless_avail = "XR_MND_headless"                  in available_exts
    _results["htcx"]    = (htcx_avail,     "from extension enumeration")
    _results["headless"] = (headless_avail, "from extension enumeration")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Create XrInstance
# ─────────────────────────────────────────────────────────────────────────────

if xr is not None:
    _sep("STEP 3 — Create XrInstance")

    to_enable = [e for e in WANTED_EXTENSIONS if e in available_exts]
    to_skip   = [e for e in WANTED_EXTENSIONS if e not in available_exts]
    print(f"  Enabling : {to_enable or '(none available)'}")
    print(f"  Skipping : {to_skip   or '(none)'}")
    print()

    try:
        # Force OpenXR 1.0 — SteamVR doesn't accept 1.1.x
        # pyopenxr 1.1.x requires a Version object, not a plain int
        try:
            api_ver = xr.Version(1, 0, 0)
        except (AttributeError, TypeError):
            try:
                api_ver = xr.make_version(1, 0, 0)
            except AttributeError:
                api_ver = (1 << 48)  # XR_MAKE_VERSION(1,0,0)

        create_info = xr.InstanceCreateInfo(
            application_info=xr.ApplicationInfo(
                application_name="probe_openxr",
                application_version=1,
                engine_name="",
                engine_version=0,
                api_version=api_ver,
            ),
            enabled_extension_names=to_enable,
        )
        instance = xr.create_instance(create_info)

        try:
            props   = xr.get_instance_properties(instance)
            runtime = bytes(props.runtime_name).rstrip(b"\x00").decode(errors="replace")
            print(f"  [OK]  XrInstance created")
            print(f"        Runtime : {runtime}  v{props.runtime_version}")
            _results["instance"] = (True, f"runtime={runtime}")
        except Exception as exc:
            print(f"  [OK]  XrInstance created  (get_instance_properties failed: {exc})")
            _results["instance"] = (True, "instance ok, properties unavailable")

    except Exception as exc:
        print(f"  [FAIL] create_instance: {exc}")
        _results["instance"] = (False, str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Get XrSystemId and create XrSession
# ─────────────────────────────────────────────────────────────────────────────

if instance is not None:
    _sep("STEP 4 — Get XrSystemId and create XrSession")

    system_id = None
    try:
        system_id = xr.get_system(
            instance,
            xr.SystemGetInfo(form_factor=xr.FormFactor.HEAD_MOUNTED_DISPLAY),
        )
        try:
            sp    = xr.get_system_properties(instance, system_id)
            sname = bytes(sp.system_name).rstrip(b"\x00").decode(errors="replace")
            print(f"  [OK]  XrSystemId {system_id}  ({sname})")
        except Exception:
            print(f"  [OK]  XrSystemId {system_id}")
    except Exception as exc:
        print(f"  [FAIL] get_system (HEAD_MOUNTED_DISPLAY): {exc}")
        if not headless_avail:
            print("         Note: without XR_MND_headless the runtime may require")
            print("         an HMD or display to be present.")

    if system_id is not None:
        print()
        if headless_avail:
            print("  XR_MND_headless available — attempting session without graphics binding")
        else:
            print("  XR_MND_headless NOT available — attempting session without graphics binding anyway")
            print("  (expect XR_ERROR_GRAPHICS_REQUIREMENTS_CALL_MISSING or similar)")
        print()

        try:
            session = xr.create_session(
                instance,
                xr.SessionCreateInfo(system_id=system_id),
            )
            mode = "headless" if headless_avail else "no graphics binding"
            print(f"  [OK]  XrSession created  ({mode})")
        except Exception as exc:
            print(f"  [FAIL] create_session: {exc}")
            if not headless_avail:
                print()
                print("  Without XR_MND_headless a graphics API binding is required.")
                print("  On Windows this means D3D11 (XR_KHR_D3D11_enable),")
                print("  Vulkan (XR_KHR_vulkan_enable), or OpenGL (XR_KHR_opengl_enable).")
                print("  A Python OpenXR session with graphics would require ctypes/cffi")
                print("  to construct and pass a valid HWND + device pointer.")
            session = None
else:
    if xr is not None:
        _sep("STEP 4 — Get XrSystemId and create XrSession")
        print("  Skipped — no XrInstance")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Enumerate VIVE tracker paths (XR_HTCX_vive_tracker_interaction)
# ─────────────────────────────────────────────────────────────────────────────

if xr is not None:
    _sep("STEP 5 — VIVE tracker enumeration (XR_HTCX_vive_tracker_interaction)")

    if instance is None:
        print("  Skipped — no XrInstance")
        _results["poses"] = (False, "no XrInstance")

    elif not htcx_avail:
        print("  Skipped — XR_HTCX_vive_tracker_interaction not in available extensions")
        _results["poses"] = (False, "extension not available")

    else:
        # 5a — xrEnumerateViveTrackerPathsHTCX
        print("  5a  xrEnumerateViveTrackerPathsHTCX:")
        tracker_paths_found = []
        try:
            fn = getattr(xr, "htcx_enumerate_vive_tracker_paths", None)
            if fn is None:
                # Try alternate naming
                fn = getattr(xr, "enumerate_vive_tracker_paths_htcx", None)
            if fn is None:
                raise AttributeError(
                    "Neither xr.htcx_enumerate_vive_tracker_paths nor "
                    "xr.enumerate_vive_tracker_paths_htcx found in pyopenxr. "
                    "Try: pip install --upgrade pyopenxr"
                )
            tracker_paths_found = fn(instance)
            print(f"    {len(tracker_paths_found)} tracker(s) enumerated:")
            for tp in tracker_paths_found:
                try:
                    persistent = xr.path_to_string(instance, tp.persistent_path)
                except Exception:
                    persistent = f"<path {tp.persistent_path}>"
                try:
                    role = xr.path_to_string(instance, tp.role_path) if tp.role_path else "(no role assigned)"
                except Exception:
                    role = f"<path {tp.role_path}>"
                print(f"    persistent : {persistent}")
                print(f"    role       : {role}")
                print()
            if tracker_paths_found:
                _results["poses"] = (True, f"{len(tracker_paths_found)} tracker(s) via xrEnumerateViveTrackerPathsHTCX")
            else:
                _results["poses"] = (False, "extension present but 0 trackers enumerated — are trackers connected?")
        except AttributeError as exc:
            print(f"    [FAIL] {exc}")
            _results["poses"] = (False, str(exc))
        except Exception as exc:
            print(f"    [FAIL] {exc}")
            _results["poses"] = (False, str(exc))

        # 5b — string_to_path for all known role paths
        print()
        print("  5b  xrStringToPath for known role paths:")
        for path_str in TRACKER_ROLE_PATHS:
            try:
                handle = xr.string_to_path(instance, path_str)
                print(f"    [OK]  {path_str}")
                print(f"          handle = {int(handle):#018x}")
            except Exception as exc:
                print(f"    [--]  {path_str}")
                print(f"          {exc}")

        # 5c — session-dependent pose actions (only if session created)
        print()
        if session is None:
            print("  5c  Pose action spaces: Skipped — no XrSession")
            print("      Pose data requires a live session with a begin/wait/end loop.")
        else:
            print("  5c  Attempting XrActionSet + pose action for one tracker role...")
            try:
                action_set = xr.create_action_set(
                    instance,
                    xr.ActionSetCreateInfo(
                        action_set_name=b"probe_set",
                        localized_action_set_name=b"Probe Set",
                        priority=0,
                    ),
                )
                pose_action = xr.create_action(
                    action_set,
                    xr.ActionCreateInfo(
                        action_name=b"tracker_pose",
                        action_type=xr.ActionType.POSE_INPUT,
                        localized_action_name=b"Tracker Pose",
                    ),
                )
                print(f"    [OK]  XrAction created  (pose type)")
                # Suggest interaction profile binding
                profile_path = xr.string_to_path(
                    instance,
                    "/interaction_profiles/htc/vive_tracker_htcx",
                )
                print(f"    [OK]  Interaction profile path: /interaction_profiles/htc/vive_tracker_htcx")
                print(f"          (full binding + session loop needed for live pose — out of probe scope)")
                xr.destroy_action_set(action_set)
            except Exception as exc:
                print(f"    [FAIL] {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

if session is not None:
    try:
        xr.destroy_session(session)
    except Exception:
        pass

if instance is not None:
    try:
        xr.destroy_instance(instance)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

_sep("SUMMARY")

r = _results
print(f"  {_ok(r['pyopenxr'][0])}  pyopenxr importable                  {r['pyopenxr'][1]}")
print(f"  {_ok(r['instance'][0])}  XrInstance created                   {r['instance'][1]}")
print(f"  {_ok(r['htcx'][0])}  XR_HTCX_vive_tracker_interaction available")
print(f"  {_ok(r['headless'][0])}  XR_MND_headless available")
print(f"  {_ok(r['poses'][0])}  Tracker poses accessible             {r['poses'][1]}")
print()

inst_ok     = r["instance"][0]
htcx_ok     = r["htcx"][0]
headless_ok = r["headless"][0]
poses_ok    = r["poses"][0]

if poses_ok and headless_ok:
    verdict = "VIABLE"
    detail  = "Full headless OpenXR tracker access confirmed."
elif poses_ok and not headless_ok:
    verdict = "PARTIAL"
    detail  = ("Tracker enumeration works but session requires a graphics binding. "
               "Headless Python pose streaming is not yet available without XR_MND_headless.")
elif inst_ok and htcx_ok and not poses_ok:
    verdict = "PARTIAL"
    detail  = ("Instance and HTCX extension OK, but tracker poses not yet confirmed. "
               "Session creation may need graphics context or running trackers.")
elif not inst_ok:
    verdict = "NOT VIABLE"
    detail  = "Could not create XrInstance — check SteamVR is running and set as OpenXR runtime."
else:
    verdict = "NOT VIABLE"
    detail  = "OpenXR initialised but tracker extension or poses not accessible."

print(f"  VERDICT: OpenXR headless path is {verdict}")
print(f"           {detail}")
print()
