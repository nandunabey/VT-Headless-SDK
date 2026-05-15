@echo off
title VUT Robotics SDK Launcher
color 0B

echo.
echo  ================================================
echo   VIVE Ultimate Tracker -- Headless Robotics SDK
echo   PoC v0.1 -- HTC VIVE ANZ
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

tasklist /FI "IMAGENAME eq ViveTrackerServer.exe" 2>nul | find /I "ViveTrackerServer.exe" >nul
if errorlevel 1 (
    tasklist /FI "IMAGENAME eq VHConsole.exe" 2>nul | find /I "VHConsole.exe" >nul
    if errorlevel 1 (
        color 0C
        echo  [ERROR] VHConsole / ViveTrackerServer is NOT running.
        echo.
        echo  Please start VHConsole.exe first ^(VIVE Hub^),
        echo  confirm tracker LED is solid, then run again.
        echo.
        pause
        exit /b 1
    )
)
echo  [OK] VIVE Hub / ViveTrackerServer detected

echo.

:: ── Kill stale instances ─────────────────────────────────────────────────────

echo  Cleaning up stale Python processes...
taskkill /F /IM python.exe /T 2>nul
timeout /t 1 /nobreak >nul
echo  [OK] Clean

echo.

:: ── Start HTTP server ────────────────────────────────────────────────────────

echo  Starting HTTP server on port 8080...
start "VUT HTTP Server" /MIN cmd /c "cd /d C:\Users\vive_\Desktop && python -m http.server 8080"
timeout /t 2 /nobreak >nul
echo  [OK] HTTP server started on port 8080

:: ── Start WebSocket daemon ───────────────────────────────────────────────────

echo  Starting WebSocket daemon on port 8765...
start "VUT Tracker Daemon" cmd /c "cd /d C:\Users\vive_\Desktop && python vtrackerd_openvr.py"

echo  Waiting for daemon to initialise...
timeout /t 3 /nobreak >nul
echo  [OK] WebSocket daemon started on port 8765

:: ── Open browser ────────────────────────────────────────────────────────────

echo  Opening visualiser in Chrome...
start chrome "http://localhost:8080/visualiser.html"
echo  [OK] Browser opening visualiser...

:: ── Status summary ───────────────────────────────────────────────────────────

echo.
echo  ================================================
echo   VIVE Ultimate Tracker -- Headless Robotics SDK
echo   PoC v0.1 -- HTC VIVE ANZ
echo  ================================================
echo.
echo  [OK] HTTP server     --  http://localhost:8080
echo  [OK] WebSocket daemon -- ws://localhost:8765
echo  [OK] Visualiser      --  http://localhost:8080/visualiser.html
echo.
echo  Tracker serials:
echo    VUT-01: 47-A33F01412  ^(cyan^)
echo    VUT-02: FA4383B00537  ^(amber^)
echo.
echo  Daemon window: "VUT Tracker Daemon"
echo  HTTP window:   "VUT HTTP Server"
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
