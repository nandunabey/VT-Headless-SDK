"""Actionable exceptions for the VUT Robotics SDK.

Every exception tells you what went wrong and how to fix it.
"""


class VUTError(Exception):
    """Base class for all VUT SDK errors."""


class DaemonNotRunning(VUTError):
    """vtrackerd_openvr.py is not running or its WebSocket port is not open.

    Fix:
        python C:\\Users\\vive_\\Desktop\\vtrackerd_openvr.py
    or:
        from vut_sdk import VUTDaemon
        VUTDaemon().start()

    Docs: see CLAUDE.md — "How to Run"
    """


class TrackerNotFound(VUTError):
    """The requested tracker ID was not seen in the pose stream.

    Fix:
        Check available tracker IDs with:
            from vut_sdk import VUTTrackerFleet
            fleet = VUTTrackerFleet()
            fleet.connect()
            print(fleet.tracker_ids)

    Tracker IDs look like '47-A33F01412'.
    Docs: see CLAUDE.md — "Known Trackers"
    """


class SteamVRNotRunning(VUTError):
    """SteamVR (vrserver.exe) is not running.

    Fix:
        Start SteamVR before launching the daemon.
        SteamVR must be running for OpenVR to enumerate trackers.

    Docs: see CLAUDE.md — "Prerequisites"
    """


class VIVEHubNotRunning(VUTError):
    """VIVE Hub (VHConsole.exe) is not running.

    Fix:
        Launch VHConsole.exe:
            C:\\Program Files\\VIVE Hub\\VIVE Hub\\Updater\\App\\VHConsole\\VHConsole.exe

        VIVE Hub starts ViveHubServer + ViveTrackerServer which SteamVR depends on.

    Docs: see CLAUDE.md — "Prerequisites"
    """


class PoseTimeout(VUTError):
    """No valid pose was received within the timeout window.

    This usually means the tracker is not actively tracking.

    Fix:
        1. Check tracker LED is solid (not flashing)
        2. Confirm SteamVR shows the tracker as active
        3. If LED is flashing: SLAM map not loaded — run Tracking Map Setup in VIVE Hub
        4. VO mode: tracking_mode=1 must be active (requires Business+ licence)

    Docs: see CLAUDE.md — "OET OVERSPEED" and "VO mode"
    """


# Legacy aliases so old code keeps working if exception names change
VUTConnectionError = DaemonNotRunning
VUTTrackerNotFoundError = TrackerNotFound
VUTTimeoutError = PoseTimeout
VUTSteamVRNotRunningError = SteamVRNotRunning
VUTHubNotRunningError = VIVEHubNotRunning
