# macOS Remote Temperature Monitor

This installer runs a lightweight Python service that broadcasts CPU temperature over UDP for the MagicMirror module.

## Requirements

- macOS 11+ (Intel or Apple Silicon)
- Python 3 installed (`/usr/bin/python3`)
- Administrator access (the temperature command requires elevated privileges)

## Installation

```bash
cd MMM-RemoteTempMonitor/remote-service/Mac
sudo ./install.sh
```

The installer:
- Copies the broadcaster script to `/usr/local/remote-temp-monitor/`
- Installs a LaunchDaemon at `/Library/LaunchDaemons/com.remote-temp-monitor.plist`
- Starts the service immediately

## How It Works

The broadcaster uses `powermetrics --samplers smc` to read the CPU temperature. This is compatible with both Intel and Apple Silicon Macs, but it requires root access. The LaunchDaemon runs as root to ensure access to the SMC sampler.

## Logs

- `/var/log/remote-temp-monitor.log`
- `/var/log/remote-temp-monitor.error.log`

## Uninstall

```bash
sudo launchctl unload /Library/LaunchDaemons/com.remote-temp-monitor.plist
sudo rm /Library/LaunchDaemons/com.remote-temp-monitor.plist
sudo rm -rf /usr/local/remote-temp-monitor
```
