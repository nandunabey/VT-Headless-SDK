@echo off
REM Robotics WS:  ws://localhost:8765
REM Robotics HTTP: http://localhost:8080
REM Skeleton WS:  ws://localhost:8766
REM Skeleton HTTP: http://localhost:8081
title VT Headless SDK -- Stop
color 0C

echo.
echo  Stopping VT Headless SDK services...
echo.

taskkill /F /IM python.exe /T 2>nul
if errorlevel 1 (
    echo  [INFO] No Python processes were running.
) else (
    echo  [OK] All Python services stopped.
)

echo.
echo  Services stopped. You can close this window.
echo.
pause
