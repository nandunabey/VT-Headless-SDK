# Platform Support

## Windows 11 — confirmed ✓
- Python 3.10+ ✓
- SteamVR required
- OpenVR (VRApplication_Background) — headless confirmed
- 5x VIVE Ultimate Trackers simultaneously confirmed
- Standard tracking mode — no licence required
- VO mode — requires Business+ licence

## Linux — under investigation

### OpenVR path
SteamVR runs on Linux but VIVE Ultimate Tracker
support is unverified. Contributions welcome.

### OpenXR path (probed May 2026, SteamVR/OpenXR v2.15.6)
- XR_HTCX_vive_tracker_interaction v3 — present ✓
- XR_MND_headless v3 — advertised but broken
  XrSession returns XR_ERROR_RUNTIME_FAILURE
- Verdict: SteamVR headless OpenXR not viable

### Monado (most promising Linux path)
Monado is an open source OpenXR runtime with real
XR_MND_headless support. VIVE Ultimate Tracker
driver support is under investigation.
See: docs/probes/probe_openxr.py

## macOS — not viable
SteamVR does not support macOS.

