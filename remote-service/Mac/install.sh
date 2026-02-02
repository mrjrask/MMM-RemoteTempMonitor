#!/bin/bash
set -euo pipefail

SERVICE_DIR="/usr/local/remote-temp-monitor"
PLIST_PATH="/Library/LaunchDaemons/com.remote-temp-monitor.plist"
SCRIPT_NAME="temp_broadcaster_mac.py"

if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./install.sh"
  exit 1
fi

mkdir -p "$SERVICE_DIR"
cp "$SCRIPT_NAME" "$SERVICE_DIR/$SCRIPT_NAME"
chmod +x "$SERVICE_DIR/$SCRIPT_NAME"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.remote-temp-monitor</string>
    <key>ProgramArguments</key>
    <array>
      <string>/usr/bin/python3</string>
      <string>${SERVICE_DIR}/${SCRIPT_NAME}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/remote-temp-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/remote-temp-monitor.error.log</string>
  </dict>
</plist>
PLIST

chmod 644 "$PLIST_PATH"

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "Installed and started remote temperature monitor."
