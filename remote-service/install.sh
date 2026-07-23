#!/usr/bin/env bash
# Dispatcher for installing a remote temperature broadcaster.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" == "Linux" ]] && [[ -r /proc/device-tree/model ]] && tr -d '\0' < /proc/device-tree/model | grep -qi 'Raspberry Pi'; then
    exec "${SCRIPT_DIR}/Pi/install.sh" "$@"
fi

cat >&2 <<'MSG'
No automatic broadcaster installer was selected for this platform.

Choose the installer for the device that will broadcast temperatures:
  Raspberry Pi: cd remote-service/Pi && sudo ./install.sh
  macOS:        cd remote-service/Mac && sudo ./install.sh
  Windows:      Run remote-service/Windows/install.ps1 as Administrator
MSG
exit 1
