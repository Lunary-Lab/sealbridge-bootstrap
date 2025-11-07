@echo off
REM system/windows/autostart/sealbridge-bridge.cmd: Windows autostart for the bridge.
REM This script is placed in the user's XDG autostart directory to launch the
REM home bridge translator when the user logs in.

set "PYTHONW_PATH=%USERPROFILE%\\.local\\share\\sealbridge\\.venv\\Scripts\\pythonw.exe"
set "BRIDGE_SCRIPT=%USERPROFILE%\\.local\\share\\sealbridge\\.venv\\Scripts\\sealbridge-bridge"

if not exist "%PYTHONW_PATH%" (
    echo "pythonw.exe not found in venv."
    exit /b 1
)

start "Sealbridge Bridge" /B "%PYTHONW_PATH%" "%BRIDGE_SCRIPT%"
