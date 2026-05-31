@echo off
REM Robotics WS:  ws://localhost:8765
REM Robotics HTTP: http://localhost:8080
REM Skeleton WS:  ws://localhost:8766
REM Skeleton HTTP: http://localhost:8081
title VT Headless SDK Launcher
color 0B

echo.
echo  ================================================
echo   VT Headless SDK
echo   Supports: VIVE Ultimate Tracker + Vive Tracker 3.0
echo   v0.2.0-alpha -- community project
echo  ================================================
echo.

:: ── Prerequisite checks ─────────────────────────────────────────────────────

echo  Checking prerequisites...
echo.

tasklist /FI "IMAGENAME eq vrserver.exe" 2>nul | find /I "vrserver.exe" >nul
if errorlevel 1 (
    color 0C
    echo  [ERROR] SteamVR is NOT running.
    echo.
    echo  Please start SteamVR first, wait for it to fully load,
    echo  then run this launcher again.
    echo.
    pause
    exit /b 1
)
echo  [OK] SteamVR detected ^(vrserver.exe^)

set VIVE_HUB_RUNNING=0
tasklist /FI "IMAGENAME eq ViveTrackerServer.exe" 2>nul | find /I "ViveTrackerServer.exe" >nul
if not errorlevel 1 set VIVE_HUB_RUNNING=1
if %VIVE_HUB_RUNNING%==0 (
    tasklist /FI "IMAGENAME eq VHConsole.exe" 2>nul | find /I "VHConsole.exe" >nul
    if not errorlevel 1 set VIVE_HUB_RUNNING=1
)
if %VIVE_HUB_RUNNING%==1 (
    echo  [OK] VIVE Hub / ViveTrackerServer detected
) else (
    echo  [--] VIVE Hub not detected --
    echo       OK for Base Station mode
    echo       Required for VUT ^(VIVE Ultimate Tracker^) mode
)

echo.

:: ── Kill stale instances ─────────────────────────────────────────────────────

echo  Cleaning up stale Python processes...
taskkill /F /IM python.exe /T 2>nul
timeout /t 1 /nobreak >nul
echo  [OK] Clean

echo.

:: ── Ensure recordings directory exists ───────────────────────────────────────

IF NOT EXIST "%~dp0recordings\" mkdir "%~dp0recordings\"
echo  [OK] recordings\ directory ready

:: ── Space calibration ─────────────────────────────────────────────────────────

set SPACE_CAL=
IF EXIST "%~dp0space_calibration.json" (
    set SPACE_CAL=--space-cal unify
    echo  [OK] Space calibration found -- unify mode enabled
) ELSE (
    echo  [--] No space calibration -- running in raw mode
    echo       Run spacecal.html to align VUT + Lighthouse
)

:: ── Start daemon (WebSocket :8765 + HTTP :8080) ──────────────────────────────

echo  Starting tracker daemon (ws://localhost:8765 + http://localhost:8080)...
start "VUT Tracker Daemon" cmd /c "cd /d %~dp0 && python vtrackerd_openvr.py --fps 60 %SPACE_CAL%"

echo  Waiting for daemon to initialise...
timeout /t 3 /nobreak >nul
echo  [OK] Daemon started -- ws://localhost:8765 + http://localhost:8080

:: ── Open browser ────────────────────────────────────────────────────────────

echo  Opening visualiser in Chrome...
start "" "http://localhost:8080/visualiser.html"
echo  [OK] Browser opening visualiser...

REM Open setup on first run only
IF NOT EXIST "%~dp0tracker_roles.json" (
    echo [--] No tracker_roles.json found -- opening setup...
    timeout /t 1 /nobreak > nul
    start "" "http://localhost:8080/setup.html"
) ELSE (
    echo [OK] tracker_roles.json found -- skipping setup
)

:: ── Start Skeleton server ─────────────────────────────────────────────────────

echo  Starting Skeleton server on port 8081...
start "VUT Skeleton Server" /MIN cmd /c "cd /d %~dp0..\vut-skeleton && python visualiser/server.py"
echo  Waiting for skeleton server to initialise...
timeout /t 3 /nobreak >nul
echo  [OK] Skeleton server started on port 8081

echo  Opening skeleton visualiser...
start "" "http://localhost:8081/vut-skeleton/visualiser/index.html"
echo  [OK] Skeleton visualiser opening...

:: ── Status summary ───────────────────────────────────────────────────────────

echo.
echo  ================================================
echo   VT Headless SDK
echo   Supports: VIVE Ultimate Tracker + Vive Tracker 3.0
echo   v0.2.0-alpha -- community project
echo  ================================================
echo.
echo  [OK] Tracker daemon  --  ws://localhost:8765 + http://localhost:8080
echo  [OK] Visualiser      --  http://localhost:8080/visualiser.html
echo  [OK] Setup page      --  http://localhost:8080/setup.html
echo  [OK] Skeleton server  --  http://localhost:8081
echo  [OK] Skeleton WS     --  ws://localhost:8766
echo  [OK] Skeleton vis    --  http://localhost:8081/vut-skeleton/visualiser/index.html
echo.
echo  Tracker serials: see visualiser for active trackers
echo.
if %VIVE_HUB_RUNNING%==1 (
    echo  Mode: VUT ^(VIVE Ultimate Tracker^)
    echo        VIVE Hub detected -- room scan required
) else (
    echo  Mode: Base Station ^(Lighthouse / Tracker 3.0^)
    echo        Ensure trackers show solid green in SteamVR
)
IF EXIST "%~dp0space_calibration.json" (
    echo  [OK] Space calibration -- UNIFY mode active
)
echo.
echo  Daemon window:   "VUT Tracker Daemon"
echo  Skeleton window: "VUT Skeleton Server"
echo.
echo  ------------------------------------------------
echo  Press any key to STOP all services and exit...
echo  ------------------------------------------------
pause >nul

:: ── Shutdown ─────────────────────────────────────────────────────────────────

echo.
echo  Stopping services...
taskkill /F /IM python.exe /T 2>nul
echo  [OK] All Python services stopped.
echo.
