# MMM-RemoteTempMonitor

A MagicMirror² module for monitoring CPU temperatures from multiple Raspberry Pi devices on your local network.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Overview

MMM-RemoteTempMonitor displays real-time CPU temperatures from Raspberry Pi devices on your local network. Each device runs a lightweight Python service that broadcasts its temperature, and the MagicMirror module displays them with color-coded indicators.

## Features

- **Real-time monitoring** - Displays CPU temperatures from multiple Raspberry Pi devices
- **Color-coded display** - Temperature values change color from green (normal) to purple (critical)
- **Automatic discovery** - Devices are automatically detected when they broadcast
- **Hostname identification** - Each device is identified by its hostname
- **Dual temperature units** - Shows both Celsius and Fahrenheit (configurable)
- **Lightweight** - Minimal resource usage on both broadcaster and receiver
- **Easy setup** - Simple installation scripts for both components

## Color Scale

The temperature display uses an intuitive color scale:

- 🟢 **Green** (< 50°C) - Normal operating temperature
- 🟡 **Yellow-Green** (50-60°C) - Warm
- 🟠 **Orange** (60-70°C) - Hot
- 🔴 **Red** (70-80°C) - Very hot
- 🟣 **Purple** (80°C+) - Critical (with pulsing animation)

## Screenshots

```
┌─────────────────────────────────┐
│ Device          °C      °F      │
├─────────────────────────────────┤
│ raspberrypi     42.5    108.5   │  (Green)
│ pi-server       58.3    136.9   │  (Yellow)
│ pi-cluster-1    72.1    161.8   │  (Red)
└─────────────────────────────────┘
```

## Installation

### Part 1: Install the MagicMirror Module

1. Navigate to your MagicMirror's modules folder:
```bash
cd ~/MagicMirror/modules
```

2. Clone this repository:
```bash
git clone https://github.com/mrjrask/MMM-RemoteTempMonitor.git
```

3. Add the module to your MagicMirror config file (`~/MagicMirror/config/config.js`):
```javascript
{
    module: "MMM-RemoteTempMonitor",
    position: "top_right",  // Or any position you prefer
    config: {
        // See configuration options below
    }
}
```

4. Restart MagicMirror

### Part 2: Install the Remote Service on Raspberry Pi Devices

For each Raspberry Pi you want to monitor:

1. Clone this repository on the Raspberry Pi:
```bash
git clone https://github.com/mrjrask/MMM-RemoteTempMonitor.git
cd MMM-RemoteTempMonitor/remote-service
```

2. Run the installation script:
```bash
chmod +x install.sh
sudo ./install.sh
```

The service will start automatically and begin broadcasting temperature data.

## Configuration Options

Here are the configuration options for the MagicMirror module:

| Option | Description | Default |
|--------|-------------|---------|
| `port` | UDP port to listen on | `9876` |
| `updateInterval` | How often to refresh display (ms) | `5000` |
| `maxDeviceAge` | Remove devices not seen for this long (ms) | `30000` |
| `cleanupInterval` | How often to check for stale devices (ms) | `60000` |
| `showFahrenheit` | Show Fahrenheit temperature | `true` |
| `showCelsius` | Show Celsius temperature | `true` |
| `sortBy` | Sort devices by "hostname" or "temperature" | `"hostname"` |
| `tempThresholds` | Temperature thresholds for color coding (°C) | See below |

### Temperature Thresholds

The default temperature thresholds (in Celsius):

```javascript
tempThresholds: {
    normal: 50,      // Below 50°C: green
    warm: 60,        // 50-60°C: yellow-green
    hot: 70,         // 60-70°C: orange
    veryHot: 80,     // 70-80°C: red
    critical: 85     // 80°C+: purple
}
```

### Example Configuration

```javascript
{
    module: "MMM-RemoteTempMonitor",
    position: "top_right",
    config: {
        port: 9876,
        showFahrenheit: true,
        showCelsius: true,
        sortBy: "temperature",  // Show hottest first
        tempThresholds: {
            normal: 45,
            warm: 55,
            hot: 65,
            veryHot: 75,
            critical: 80
        }
    }
}
```

## How It Works

1. **Remote Service**: Each Raspberry Pi runs a Python service (`temp_broadcaster.py`) that:
   - Reads the CPU temperature from `/sys/class/thermal/thermal_zone0/temp`
   - Broadcasts the temperature and hostname via UDP every 5 seconds
   - Runs as a systemd service for automatic startup

2. **MagicMirror Module**: The module consists of:
   - `node_helper.js`: Listens for UDP broadcasts on the local network
   - `MMM-RemoteTempMonitor.js`: Displays the temperature data
   - `MMM-RemoteTempMonitor.css`: Provides color-coded styling

3. **Communication**: Data is broadcast in JSON format:
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

## Remote Service Management

On Raspberry Pi devices running the broadcaster service:

```bash
# Check status
sudo systemctl status temp-monitor

# View logs
sudo journalctl -u temp-monitor -f

# Restart service
sudo systemctl restart temp-monitor

# Stop service
sudo systemctl stop temp-monitor

# Start service
sudo systemctl start temp-monitor
```

## Troubleshooting

### Module shows "No temperature monitors found"

1. Verify the remote service is running on your Raspberry Pi:
   ```bash
   sudo systemctl status temp-monitor
   ```

2. Check that devices are on the same network

3. Verify the UDP port (9876) is not blocked by firewall

4. Check MagicMirror logs:
   ```bash
   pm2 logs MagicMirror
   ```

### Temperatures not updating

- Ensure the `maxDeviceAge` config isn't too short
- Check that the broadcast interval on the remote service matches expectations
- Verify network connectivity between devices

### Service won't start on Raspberry Pi

```bash
# Check for errors
sudo journalctl -u temp-monitor -n 50

# Verify temperature sensor exists
cat /sys/class/thermal/thermal_zone0/temp
```

## Network Security

This module broadcasts temperature data unencrypted over your local network. Only use on trusted networks. The broadcasts are limited to the local subnet.

## Customization

### Changing Broadcast Interval

Edit `/opt/remote-temp-monitor/temp_broadcaster.py` and modify:
```python
BROADCAST_INTERVAL = 5  # seconds
```

Then restart the service:
```bash
sudo systemctl restart temp-monitor
```

### Custom Styling

You can customize the appearance by editing `MMM-RemoteTempMonitor.css` in the module directory.

## Compatibility

- **MagicMirror²**: Version 2.x
- **Remote Devices**: Raspberry Pi (all models with thermal sensor)
- **Operating System**: Raspberry Pi OS (formerly Raspbian)
- **Node.js**: Version 14 or higher
- **Python**: Version 3.x

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Credits

Developed by [mrjrask](https://github.com/mrjrask)

## Support

If you encounter issues or have questions:
- Open an issue on [GitHub](https://github.com/mrjrask/MMM-RemoteTempMonitor/issues)
- Check the troubleshooting section above
- Review the logs on both the MagicMirror and remote service

## Changelog

### Version 1.0.0
- Initial release
- UDP broadcast-based temperature monitoring
- Color-coded temperature display
- Support for multiple Raspberry Pi devices
- Automatic device discovery and cleanup
