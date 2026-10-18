#!/usr/bin/env python3
"""
Installation script for Remote Temperature Monitor and Status Broadcast Service.

This script installs and configures both the temperature broadcaster and status
broadcaster services on Raspberry Pi. The status broadcaster checks for apt updates
and broadcasts status information to the MagicMirror module.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"

# Installation directories
INSTALL_DIR = Path("/opt/remote-temp-monitor")
STATUS_SERVICE_DIR = Path("/opt/remote-temp-monitor/status")

# Service files
TEMP_SERVICE_FILE = "temp-monitor.service"
STATUS_SERVICE_FILE = "status-monitor.service"
TEMP_SERVICE_PATH = Path("/etc/systemd/system") / TEMP_SERVICE_FILE
STATUS_SERVICE_PATH = Path("/etc/systemd/system") / STATUS_SERVICE_FILE

# Script files
SCRIPT_NAME = "temp_broadcaster.py"
STATUS_SCRIPT_NAME = "status-broadcaster.py"

# Environment files
ENV_TEMPLATE = "temp-monitor.env"
STATUS_ENV_TEMPLATE = "status-monitor.env"
ENV_TARGET = Path("/etc/default/temp-monitor")
STATUS_ENV_TARGET = Path("/etc/default/temp-monitor-status")


def print_green(message: str = "") -> None:
    print(f"{GREEN}{message}{NC}" if message else "")


def print_yellow(message: str) -> None:
    print(f"{YELLOW}{message}{NC}")


def print_red(message: str) -> None:
    print(f"{RED}{message}{NC}")


def run(command: list[str], check: bool = True) -> None:
    """Run a command with optional success checking."""
    result = subprocess.run(command, check=check)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}")


def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    missing = []
    
    # Check for apt-get
    if not shutil.which('apt-get'):
        missing.append('apt-get')
    
    # Check for systemctl (systemd)
    if not shutil.which('systemctl'):
        missing.append('systemctl')
    
    # Check for python3
    if not shutil.which('python3'):
        missing.append('python3')
    
    if missing:
        print_red(f"ERROR: Missing dependencies: {', '.join(missing)}")
        print_yellow("Please install the missing dependencies and try again.")
        return False
    
    return True


def install_status_broadcaster():
    """Install the status broadcaster service."""
    print_green("Installing status broadcaster script...")
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STATUS_DIR / STATUS_SCRIPT_NAME, STATUS_DIR / STATUS_SCRIPT_NAME)
    (STATUS_DIR / STATUS_SCRIPT_NAME).chmod(0o755)

    print_green("Installing systemd service for status broadcaster...")
    shutil.copy2(STATUS_DIR / STATUS_SERVICE_FILE, STATUS_SERVICE_PATH)

    if not STATUS_ENV_TARGET.exists():
        print_green("Installing status environment file template...")
        shutil.copy2(STATUS_DIR / STATUS_ENV_TEMPLATE, STATUS_ENV_TARGET)
        STATUS_ENV_TARGET.chmod(0o644)

    # Reload systemd daemon
    print_green("Reloading systemd daemon...")
    run(["systemctl", "daemon-reload"])

    # Enable status service to start on boot
    print_green("Enabling status service to start on boot...")
    run(["systemctl", "enable", STATUS_SERVICE_FILE])

    # Start status service
    print_green("Starting status monitor service...")
    run(["systemctl", "start", STATUS_SERVICE_FILE])


def install_temperature_broadcaster():
    """Install the temperature broadcaster service."""
    print_green("Creating installation directory...")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    print_green("Installing temperature broadcaster script...")
    shutil.copy2(STATUS_DIR / STATUS_SCRIPT_NAME, INSTALL_DIR / SCRIPT_NAME)
    (INSTALL_DIR / SCRIPT_NAME).chmod(0o755)

    print_green("Installing systemd service...")
    shutil.copy2(STATUS_DIR / STATUS_SERVICE_FILE, TEMP_SERVICE_PATH)

    if not ENV_TARGET.exists():
        print_green("Installing environment file template...")
        shutil.copy2(STATUS_DIR / STATUS_ENV_TEMPLATE, ENV_TARGET)
        ENV_TARGET.chmod(0o644)

    # Reload systemd daemon
    print_green("Reloading systemd daemon...")
    run(["systemctl", "daemon-reload"])

    # Enable temperature service to start on boot
    print_green("Enabling temperature service to start on boot...")
    run(["systemctl", "enable", TEMP_SERVICE_FILE])

    # Start temperature service
    print_green("Starting temperature monitor service...")
    run(["systemctl", "start", TEMP_SERVICE_FILE])


def main() -> int:
    """Main installation function."""
    script_dir = Path(__file__).resolve().parent

    print_green("=" * 50)
    print_green("Remote Temperature & Status Monitor")
    print_green("Full Installation Script")
    print_green("=" * 50)
    print()

    # Check for root privileges
    if os.geteuid() != 0:
        print_red("ERROR: Please run as root (use sudo)")
        return 1

    # Check for dependencies
    if not check_dependencies():
        return 1

    print_green("Checking for Raspberry Pi system...")
    if not os.path.exists("/proc/device-tree/model"):
        print_yellow("WARNING: /proc/device-tree/model not found")
        print_yellow("This script is designed for Raspberry Pi. Continue anyway? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("Installation cancelled.")
            return 0

    # Check for Raspberry Pi model
    try:
        model_str = Path("/proc/device-tree/model").read_text().strip().lower()
        if 'raspberry pi' not in model_str:
            print_yellow("WARNING: This does not appear to be a Raspberry Pi system")
            print_yellow("Continue installation anyway? (y/n)")
            response = input().strip().lower()
            if response != 'y':
                print("Installation cancelled.")
                return 0
    except FileNotFoundError:
        print_red("ERROR: Cannot detect Raspberry Pi system")
        return 1

    # Create status broadcaster directory
    print_green("Creating status broadcaster directory...")
    STATUS_DIR = Path(INSTALL_DIR) / "status"
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    # Install status broadcaster
    print_green("Installing status broadcaster...")
    install_status_broadcaster()

    print()
    print_green("=" * 50)
    print_green("Status Broadcaster Installed!")
    print_green("=" * 50)
    print()
    print("Service Status:")
    subprocess.run(["systemctl", "status", STATUS_SERVICE_FILE, "--no-pager"], check=False)
    print()

    # Continue with temperature broadcaster installation
    print_green("Continuing with temperature broadcaster installation...")
    print()

    # Check for temperature sensor
    THERMAL_SENSOR = Path("/sys/class/thermal/thermal_zone0/temp")
    if not THERMAL_SENSOR.exists():
        print_yellow(f"WARNING: Temperature sensor not found at {THERMAL_SENSOR}")
        print_yellow("This script is designed for Raspberry Pi. Continue anyway? (y/n)")
        response = input().strip().lower()
        if response.lower() != 'y':
            print("Installation cancelled.")
            return 0

    # Install temperature broadcaster
    print_green("Installing temperature broadcaster...")
    install_temperature_broadcaster()

    print()
    print_green("=" * 50)
    print_green("Installation Complete!")
    print_green("=" * 50)
    print()
    print("Both services are now running:")
    print("  - Temperature Monitor: UDP port 9876")
    print("  - Status Monitor: UDP port 9876")
    print()
    print("Service Status:")
    print("  Temperature: sudo systemctl status temp-monitor.service")
    print("  Status:      sudo systemctl status status-monitor.service")
    print()
    print("Logs:")
    print("  Temperature: sudo journalctl -u temp-monitor -f")
    print("  Status:      sudo journalctl -u status-monitor -f")
    print()
    print_green("Configuration files are at:")
    print(f"  {ENV_TARGET}")
    print(f"  {STATUS_ENV_TARGET}")
    print()
    print_green("The services are broadcasting:")
    print("  - Temperature data every 5 seconds (configurable)")
    print("  - Status updates every 60 seconds (configurable)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())