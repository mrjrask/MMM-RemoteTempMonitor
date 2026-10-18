# Remote Status Monitor - Status Broadcaster

This is the status broadcaster service for Raspberry Pi. It periodically checks for system updates and broadcasts status information to the MagicMirror module.

## Features

- **Yellow Dot Indicator**: Shows when `apt` updates are available
- **Blue Dot Indicator**: Shows when the MagicMirror client software needs updating
- **Random Pulse Timing**: Yellow dots pulse every 2 seconds, blue dots every 1.5 seconds (to prevent visual sync)
- **Configurable Check Interval**: Default is 10 minutes (600 seconds), adjustable via environment variables
- **Device Metadata**: Includes Pi model and RAM information

## Installation

```bash
# Run from the Pi directory
sudo ./install.sh

# Or use the full installation script
sudo ./install-full.sh
```

## Configuration

Edit `/etc/default/temp-monitor-status` to customize:

```bash
# HTTP diagnostics port (optional)
STATUS_BROADCAST_HTTP_PORT=8080

# Shared secret for authenticated UDP packets (optional)
STATUS_BROADCAST_SHARED_SECRET=your-secret-key

# Broadcast targets (comma-separated or use <broadcast> for all)
STATUS_BROADCAST_TARGETS=192.168.1.100

# How often to check for system updates (in seconds)
STATUS_BROADCAST_CHECK_INTERVAL=300  # 5 minutes
```

## Service Management

```bash
# View status
sudo systemctl status status-monitor

# View logs
sudo journalctl -u status-monitor -f

# Stop service
sudo systemctl stop status-monitor

# Start service
sudo systemctl start status-monitor

# Restart service
sudo systemctl restart status-monitor
```

## How It Works

The status broadcaster:
1. **Checks for apt updates** by running `apt-get upgrade --dry-run`
2. **Counts upgradable packages** - if any are available, sets yellow dot
3. **Broadcasts status** to all configured targets every 10 minutes (by default)
4. **MagicMirror module** displays:
   - **Yellow pulsing dot**: Device needs apt updates
   - **Blue pulsing dot**: Client software needs update
   - Both dots can appear simultaneously

## MagicMirror Configuration

In your `config.js`:

```javascript
modules: [
    {
        module: 'MMM-RemoteTempStatusMonitor',
        position: 'top_bar',
        header: 'Remote Devices Status',
        height: '60px',
        config: {
            port: 9876,                    // Same as temperature monitor
            maxDeviceAge: 30000,
            cleanupInterval: 60000,        // How often to refresh (ms)
            updatePulseDuration: 2000,    // ms for yellow pulse
            clientPulseDuration: 1500,    // ms for blue pulse
            aggregatePort: 9877,          // HTTP port for status
            aggregateEndpointPath: '/status'
        }
    }
]
```

## CSS Styling

The status monitor uses these classes:

- `.status-dot-indicator`: Container for status dots (left of device name)
- `.status-dot`: The actual dot (default: invisible)
- `.status-update-dot`: Yellow dot for apt updates (pulses at 2s intervals)
- `.status-client-dot`: Blue dot for client updates (pulses at 1.5s intervals)
- `.status-device-name`: Device hostname text
- `.status-device-meta`: Additional device info (Pi model, RAM)

## Usage Notes

1. **Dot Positioning**: Status dots appear to the **left** of the device name, not after it
2. **Pulse Timing**: Yellow and blue dots pulse at **different** frequencies to avoid visual sync
3. **Device Column**: When status dots are visible, only the device column shifts right - temperature columns stay fixed
4. **Multiple Dots**: Both yellow and blue dots can appear on the same device

## HTTP Endpoint

The status broadcaster also exposes an HTTP endpoint for viewing status directly in a browser:

```
http://<raspberry-pi-ip>:9877/status
```

Returns JSON:
```json
{
    "type": "status",
    "hostname": "pi-name",
    "device_id": "192.168.1.100",
    "timestamp": 1699900000,
    "statusUpdateAvailable": true,
    "statusClientUpdate": false,
    "lastSeen": 1699900000,
    "pi_model": "5",
    "pi_ram": "2GB"
}
```

## Security

For encrypted UDP broadcasts, set a shared secret:

```bash
sudo nano /etc/default/temp-monitor-status
```

Add:
```bash
STATUS_BROADCAST_SHARED_SECRET=my-secret-key
```

And in your MagicMirror config:
```javascript
config: {
    sharedSecret: "my-secret-key"
}
```

## Troubleshooting

**Service not starting?**
```bash
sudo systemctl status status-monitor
sudo journalctl -u status-monitor -f
```

**Port in use?**
Change `STATUS_BROADCAST_HTTP_PORT` in the env file or the broadcast port.

**Broadcast not reaching targets?**
- Check that all devices can reach the broadcast address
- Use unicast targets: `STATUS_BROADCAST_TARGETS=192.168.1.100,192.168.1.101`
- Check firewall settings on target devices

**No status updates showing?**
- Ensure the status broadcaster service is running
- Check that the device has `apt` installed
- Verify network connectivity

## Future Enhancements

- Check for specific MagicMirror package versions
- Compare against GitHub releases
- Support for other package managers (apk, pacman, etc.)
- Integration with other monitoring services