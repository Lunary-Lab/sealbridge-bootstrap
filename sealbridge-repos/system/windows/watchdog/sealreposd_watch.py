# system/windows/watchdog/sealreposd_watch.py: Windows watchdog for the daemon.
# This script provides a simple watchdog process for Windows, ensuring that the
# 'sealreposd' daemon is automatically restarted if it exits unexpectedly. This
# is a lightweight alternative to a full-fledged Windows service.

import subprocess
import time
import sys
import os

def main():
    """Watchdog loop for the daemon."""
    script_path = os.path.join(
        os.environ["USERPROFILE"],
        ".local", "share", "sealbridge", ".venv", "Scripts", "sealreposd"
    )
    while True:
        try:
            process = subprocess.Popen([sys.executable, script_path])
            process.wait()
            print(f"Process exited with code {process.returncode}. Restarting...")
        except Exception as e:
            print(f"An error occurred: {e}. Restarting...")
        time.sleep(10)

if __name__ == "__main__":
    main()
