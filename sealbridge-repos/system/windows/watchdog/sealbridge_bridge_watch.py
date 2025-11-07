# system/windows/watchdog/sealbridge_bridge_watch.py: Windows watchdog for the bridge.
# This script is a watchdog for the 'sealbridge-bridge' process on Windows.
# It ensures that the bridge translator is automatically restarted if it exits
# unexpectedly, providing resilience for the home-machine sync process.

import subprocess
import time
import sys
import os

def main():
    """Watchdog loop for the bridge."""
    script_path = os.path.join(
        os.environ["USERPROFILE"],
        ".local", "share", "sealbridge", ".venv", "Scripts", "sealbridge-bridge"
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
