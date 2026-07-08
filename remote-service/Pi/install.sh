#!/usr/bin/env python3
"""
Installation script for Remote Temperature Monitor Service.

This script installs and configures the temperature broadcaster on Raspberry Pi.
It intentionally keeps the historical install.sh filename, but runs with Python 3
so both `sudo ./install.sh` and `sudo python3 install.sh` work.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"

INSTALL_DIR = Path("/opt/remote-temp-monitor")
SERVICE_FILE = "temp-monitor.service"
SERVICE_PATH = Path("/etc/systemd/system") / SERVICE_FILE
SCRIPT_NAME = "temp_broadcaster.py"
ENV_TEMPLATE = "temp-monitor.env"
ENV_TARGET = Path("/etc/default/temp-monitor")
THERMAL_SENSOR = Path("/sys/class/thermal/thermal_zone0/temp")


def print_green(message: str = "") -> None:
    print(f"{GREEN}{message}{NC}" if message else "")


def print_yellow(message: str) -> None:
    print(f"{YELLOW}{message}{NC}")


def print_red(message: str) -> None:
    print(f"{RED}{message}{NC}")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    script_dir = Path(__file__).resolve().parent

    print_green("================================")
    print_green("Remote Temperature Monitor")
    print_green("Installation Script")
    print_green("================================")
    print()

    if os.geteuid() != 0:
        print_red("ERROR: Please run as root (use sudo)")
        return 1

    if not THERMAL_SENSOR.exists():
        print_yellow(f"WARNING: Temperature sensor not found at {THERMAL_SENSOR}")
        print_yellow("This script is designed for Raspberry Pi. Continue anyway? (y/n)")
        response = input().strip()
        if response.lower() != "y":
            print("Installation cancelled.")
            return 0

    print_green("Creating installation directory...")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    print_green("Installing temperature broadcaster script...")
    shutil.copy2(script_dir / SCRIPT_NAME, INSTALL_DIR / SCRIPT_NAME)
    (INSTALL_DIR / SCRIPT_NAME).chmod(0o755)

    print_green("Installing systemd service...")
    shutil.copy2(script_dir / SERVICE_FILE, SERVICE_PATH)

    if not ENV_TARGET.exists():
        print_green("Installing environment file template...")
        shutil.copy2(script_dir / ENV_TEMPLATE, ENV_TARGET)
        ENV_TARGET.chmod(0o644)

    print_green("Reloading systemd daemon...")
    run(["systemctl", "daemon-reload"])

    print_green("Enabling service to start on boot...")
    run(["systemctl", "enable", SERVICE_FILE])

    print_green("Starting temperature monitor service...")
    run(["systemctl", "start", SERVICE_FILE])

    print()
    print_green("================================")
    print_green("Installation Complete!")
    print_green("================================")
    print()
    print("Service Status:")
    subprocess.run(["systemctl", "status", SERVICE_FILE, "--no-pager"], check=False)
    print()
    print_green("Useful commands:")
    print(f"  - View status:  sudo systemctl status {SERVICE_FILE}")
    print(f"  - View logs:    sudo journalctl -u {SERVICE_FILE} -f")
    print(f"  - Stop service: sudo systemctl stop {SERVICE_FILE}")
    print(f"  - Start service: sudo systemctl start {SERVICE_FILE}")
    print(f"  - Restart service: sudo systemctl restart {SERVICE_FILE}")
    print()
    print_green("The service is now broadcasting temperature data on UDP port 9876")
    return 0


if __name__ == "__main__":
    sys.exit(main())
