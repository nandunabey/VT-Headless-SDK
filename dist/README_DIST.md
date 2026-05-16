# VUT Robotics SDK — Standalone Tools

**Version:** v0.1.0-alpha
**Built by:** nandunabey — community project

---

## Prerequisites

These tools require:

- VIVE Hub installed and running ([vive.com](https://www.vive.com))
- SteamVR installed and running (via Steam)
- VIVE Ultimate Tracker(s) paired and showing green in VIVE Hub
- VIVE Business+ licence (for VO mode — no room scan required)

No Python installation required on the target machine.

---

## How to use

1. Run `START_VUT_ROBOTICS_SDK.bat` to start the tracking stack
2. Open a terminal in this folder
3. Run `vut-status.exe` to confirm everything is working

---

## Tools

### `vut-status.exe`

Full health check. Run this first whenever something isn't working.
Shows: VIVE Hub, SteamVR, daemon status, active trackers, live poses.

```
vut-status.exe
```

### `vut-daemon.exe`

Control the tracking daemon (`vtrackerd_openvr.py`).

```
vut-daemon.exe start     start daemon in a new console window
vut-daemon.exe stop      terminate managed daemon
vut-daemon.exe status    check all service states
```

### `vut-pose.exe`

Stream live 6DoF poses to the terminal.

```
vut-pose.exe                          stream first tracker at 10 Hz
vut-pose.exe --id 47-A33F01412        stream specific tracker
vut-pose.exe --hz 30                  30 Hz output
vut-pose.exe --once                   print one pose and exit
```

Stop streaming: `Ctrl+C`

---

## Support

See `README.md` in the SDK root for full documentation and API reference.

Alpha release — APIs and behaviour may change between versions.
