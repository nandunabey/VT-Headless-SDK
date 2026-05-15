@echo off
title VUT Robotics SDK -- Stop
color 0C

echo.
echo  Stopping VUT Robotics SDK services...
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
