# Remote Temperature Monitor Service

A lightweight Python service for Raspberry Pi that broadcasts CPU temperature over the local network via UDP.

## Overview

This service reads the CPU temperature from the Raspberry Pi's thermal sensor and broadcasts it over UDP on port 9876. The MagicMirror module `MMM-RemoteTempMonitor` listens for these broadcasts and displays the temperature data.

## Features

- Reads CPU temperature directly from Raspberry Pi thermal sensor
- Broadcasts temperature in both Celsius and Fahrenheit
- Includes hostname for device identification
- Runs as a systemd service (auto-starts on boot)
- Lightweight and minimal resource usage
- JSON format for easy parsing

## Requirements

- Raspberry Pi (any model with thermal sensor)
- Python 3.x (pre-installed on Raspberry Pi OS)
- Root access for installation

## Installation

1. Clone or download this repository to your Raspberry Pi:
```bash
git clone https://github.com/mrjrask/MMM-RemoteTempMonitor.git
cd MMM-RemoteTempMonitor/remote-service
```

2. Run the installation script with sudo:
```bash
sudo ./install.sh
```

The installation script will:
- Copy the broadcaster script to `/opt/remote-temp-monitor/`
- Install and enable the systemd service
- Start the service automatically

## Usage

The service runs automatically in the background. Here are some useful commands:

```bash
# Check service status
sudo systemctl status temp-monitor

# View live logs
sudo journalctl -u temp-monitor -f

# Stop the service
sudo systemctl stop temp-monitor

# Start the service
sudo systemctl start temp-monitor

# Restart the service
sudo systemctl restart temp-monitor

# Disable auto-start on boot
sudo systemctl disable temp-monitor
```

## Manual Testing

To test the broadcaster manually without installing as a service:

```bash
python3 temp_broadcaster.py
```

Press Ctrl+C to stop.

## Configuration

You can modify these settings in `temp_broadcaster.py`:

- `BROADCAST_PORT` (default: 9876) - UDP port for broadcasting
- `BROADCAST_INTERVAL` (default: 5) - Seconds between broadcasts

After changing configuration, restart the service:
```bash
sudo systemctl restart temp-monitor
```

## Broadcast Format

The service broadcasts JSON messages in the following format:

```json
{
  "type": "temperature",
  "hostname": "raspberrypi",
  "temperature": {
    "celsius": 45.2,
    "fahrenheit": 113.4
  },
  "timestamp": 1700000000
}
```

## Troubleshooting

### Service won't start
Check the logs for errors:
```bash
sudo journalctl -u temp-monitor -n 50
```

### Temperature reads as null
Ensure the thermal sensor file exists:
```bash
cat /sys/class/thermal/thermal_zone0/temp
```

### Broadcasts not received
- Ensure UDP port 9876 is not blocked by firewall
- Verify devices are on the same network
- Check that the service is running: `sudo systemctl status temp-monitor`

## Uninstallation

To remove the service:

```bash
# Stop and disable the service
sudo systemctl stop temp-monitor
sudo systemctl disable temp-monitor

# Remove files
sudo rm /etc/systemd/system/temp-monitor.service
sudo rm -rf /opt/remote-temp-monitor

# Reload systemd
sudo systemctl daemon-reload
```

## Network Security

This service broadcasts temperature data unencrypted over your local network. Only use on trusted networks. The broadcast is limited to the local subnet.

## License

MIT License - See main repository for details
