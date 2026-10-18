#!/usr/bin/env bash
# Installation script for Remote Temperature Monitor Service.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we have root privileges
if [[ $EUID -ne 0 ]]; then
   echo "ERROR: This script must be run as root (use sudo)"
   exit 1
fi

# Check if running on Raspberry Pi
if [[ "$(uname -s)" == "Linux" ]] && [[ -r /proc/device-tree/model ]] && tr -d '\0' < /proc/device-tree/model | grep -qi 'Raspberry Pi'; then
    # Check for apt
    if ! command -v apt-get &> /dev/null; then
        echo "ERROR: apt-get is not installed. Please install apt first."
        exit 1
    fi

    exec "${SCRIPT_DIR}/Pi/install-full.sh" "$@"
fi

cat >&2 <<'MSG'
No automatic broadcaster installer was selected for this platform.

Choose the installer for the device that will broadcast temperatures:
  Raspberry Pi: cd remote-service/Pi && sudo ./install.sh
  macOS:        cd remote-service/Mac && sudo ./install.sh
  Windows:      Run remote-service/Windows/install.ps1 as Administrator
MSG
exit 1
<EOF>