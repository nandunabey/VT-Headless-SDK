# Platform Support

## Windows (confirmed)
- Windows 11 ✓
- Python 3.10+ ✓
- SteamVR required
- OpenVR (VRApplication_Background) — confirmed working headlessly
- 5x VIVE Ultimate Trackers simultaneously confirmed

## Linux (under investigation)
OpenVR path: SteamVR runs on Linux but tracker support is unverified.

OpenXR path: Probed on SteamVR/OpenXR v2.15.6 (May 2026)
- XR_HTCX_vive_tracker_interaction v3 — present ✓
- XR_MND_headless v3 — advertised but XrSession
  creation returns XR_ERROR_RUNTIME_FAILURE
- Verdict: SteamVR's headless OpenXR implementation
  is broken on this runtime

Monado (open source OpenXR runtime) is the most promising
Linux path — investigation pending.
Contributions welcome: see docs/probes/probe_openxr.py

## macOS
SteamVR does not support macOS. Not viable without
an alternative OpenXR runtime.

## Contributions
If you have Linux or Monado results, please open an issue.
