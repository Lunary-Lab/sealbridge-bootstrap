@echo off
REM system/windows/autostart/sealreposd.cmd: Windows autostart script for the daemon.
REM This script is placed in the user's XDG autostart directory to launch the
REM daemon without a visible console window when the user logs in.

set "PYTHONW_PATH=%USERPROFILE%\\.local\\share\\sealbridge\\.venv\\Scripts\\pythonw.exe"
set "DAEMON_SCRIPT=%USERPROFILE%\\.local\\share\\sealbridge\\.venv\\Scripts\\sealreposd"

if not exist "%PYTHONW_PATH%" (
    echo "pythonw.exe not found in venv."
    exit /b 1
)

start "Sealbridge Daemon" /B "%PYTHONW_PATH%" "%DAEMON_SCRIPT%"
