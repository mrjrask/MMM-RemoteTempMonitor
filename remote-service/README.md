# Remote Temperature Monitor Service

A lightweight Python service for Raspberry Pi that broadcasts CPU temperature over the local network via UDP.

## Overview

This service reads the CPU temperature from the Raspberry Pi's thermal sensor and broadcasts it over UDP on port 9876. The MagicMirror module `MMM-RemoteTempMonitor` listens for these broadcasts and displays the temperature data.

## Features

- Reads CPU temperature directly from Raspberry Pi thermal sensor
- Broadcasts temperature in both Celsius and Fahrenheit
- **Automatically detects Raspberry Pi model** (Pi 0W, 0W2, 2, 3, 4, 5, CM5)
- **Automatically detects RAM size** (512MB, 1GB, 2GB, 4GB, 8GB, 16GB)
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

## Updating the Service

If you need to update the broadcaster service with new code (e.g., to add model/RAM detection):

### Option 1: Using the update script (recommended)
```bash
cd MMM-RemoteTempMonitor/remote-service
sudo ./update.sh
```

### Option 2: Manual update
```bash
cd MMM-RemoteTempMonitor/remote-service
sudo cp temp_broadcaster.py /opt/remote-temp-monitor/
sudo systemctl restart temp-monitor.service
```

**Note:** The correct service name is `temp-monitor.service`

## Usage

The service runs automatically in the background. Here are some useful commands:

```bash
# Check service status
sudo systemctl status temp-monitor.service

# View live logs
sudo journalctl -u temp-monitor.service -f

# Stop the service
sudo systemctl stop temp-monitor.service

# Start the service
sudo systemctl start temp-monitor.service

# Restart the service
sudo systemctl restart temp-monitor.service

# Disable auto-start on boot
sudo systemctl disable temp-monitor.service
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
sudo systemctl restart temp-monitor.service
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
  "pi_model": "4",
  "pi_ram": "4GB",
  "timestamp": 1700000000
}
```

## Troubleshooting

### Model and RAM info not showing in MagicMirror
If the temperature appears but model and RAM info doesn't:
1. Make sure you've updated the service with the latest code using `update.sh`
2. Restart the service: `sudo systemctl restart temp-monitor.service`
3. Check the logs to verify model/RAM detection: `sudo journalctl -u temp-monitor.service -n 50`
4. Verify the broadcast includes model/RAM data in the logs

### Service won't start
Check the logs for errors:
```bash
sudo journalctl -u temp-monitor.service -n 50
```

### Temperature reads as null
Ensure the thermal sensor file exists:
```bash
cat /sys/class/thermal/thermal_zone0/temp
```

### Broadcasts not received
- Ensure UDP port 9876 is not blocked by firewall
- Verify devices are on the same network
- Check that the service is running: `sudo systemctl status temp-monitor.service`

## Uninstallation

To remove the service:

```bash
# Stop and disable the service
sudo systemctl stop temp-monitor.service
sudo systemctl disable temp-monitor.service

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
