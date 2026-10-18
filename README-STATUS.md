# Remote Status Monitor

## Overview

Remote Status Monitor is an optional addon for the [MMM-RemoteTempMonitor](README.md) MagicMirror module that provides visual status indicators for system updates on remote Raspberry Pi devices.

**Note:** This is an addon. For the full installation, use `install-full.sh`. For temperature monitoring only, the `MMM-RemoteTempMonitor` module is sufficient.

## Features

### Status Indicators

The status monitor displays two colored pulsing dots before device names:

| Color | Meaning | Use Case |
|-------|--------|----------|
| 🟡 **Yellow** | APT package updates available | When `apt-get upgrade` would install packages |
| 🔵 **Blue** | desk_display git changes detected | When the desk_display folder has unstaged/uncommitted changes |

### Visual Design

- **Pulse Timing**: 
  - Yellow dots pulse every **2000ms** 
  - Blue dots pulse every **1500ms**
  - The different timing prevents visual synchronization
- **Positioning**: Dots appear to the **left** of the device name, vertically centered
- **Spacing**: Plenty of room is allocated for dots before device name text starts
- **Device Column**: Only the device text column shifts when indicators appear; temperature columns remain fixed

### Example Display

```
┌──────────────────────────────────────────────┐
│ Device        ●● Device Name     35.2°C    │
│               ●●  (Pi 5 | 2GB)  95.8°F     │
└──────────────────────────────────────────────┘
Legend: ●● = Status dots (left of device name)
        = Temperature columns (fixed position)
```

## Git Changes Detection (Blue Dot)

### How It Works

The blue status dot is activated when the `desk_display` folder contains git changes that haven't been committed:

1. **Folder Location**: `/home/pi/desk_display`
2. **Git Check**: The status broadcaster runs `git status --porcelain -s` every check cycle
3. **Detection**: Any unstaged, uncommitted changes will trigger the blue dot

### Git Status Types Detected

The blue dot will appear when any of these git changes are detected:

| Git Symbol | Meaning | Visual |
|-----------|---------|--------|
| `M` | Modified files | Blue dot |
| `A` | Added files | Blue dot |
| `D` | Deleted files | Blue dot |
| `R` | Renamed files | Blue dot |
| `C` | Copied files | Blue dot |
| `T` | Type changed | Blue dot |
| `U` | Unmerged files | Blue dot |
| `?` | Untracked files | Blue dot |

### Important Notes

- **Folder Must Exist**: If `/home/pi/desk_display` doesn't exist, the blue dot will **never** appear
- **Staged Changes Excluded**: Files that are staged (added to index) won't trigger the blue dot
- **Committed Changes**: If changes are committed to git, the blue dot will be cleared
- **Git Must Be Installed**: The Pi must have the `git` command available

### Example Scenarios

#### Scenario 1: Desk Display with Uncommitted Changes
- **Blue Dot**: Active
- **Visual**: `● Device Name (Pi 5 | 2GB)`

#### Scenario 2: Desk Display with Committed Changes Only
- **Blue Dot**: Inactive (hidden)
- **Visual**: `Device Name (Pi 5 | 2GB)`

#### Scenario 3: No Desk Display Folder
- **Blue Dot**: Never appears
- **Visual**: `Device Name (Pi 5 | 2GB)`

#### Scenario 4: Both Yellow and Blue Dots
- **Yellow Dot**: Active (APT updates available)
- **Blue Dot**: Active (git changes in desk_display)
- **Visual**: `●● Device Name (Pi 5 | 2GB)`

## Installation

### Full Installation (Recommended)

```bash
# From the remote-service/Pi directory
sudo ./install-full.sh
```

This installs:
1. **Temperature Monitor Service** (`temp-monitor.service`)
   - Broadcasts CPU temperatures on UDP port 9876
2. **Status Monitor Service** (`status-monitor.service`)
   - Checks for apt updates every 10 minutes (configurable)
   - Checks for git changes in desk_display folder (configurable)
   - Broadcasts status to the same UDP port

### Minimal Installation

```bash
# From the remote-service/Pi directory  
sudo ./install.sh
```

This installs only the temperature monitor service.

## Configuration

Edit the appropriate environment file based on your platform:

### Raspberry Pi

- Temperature: `/etc/default/temp-monitor`
- Status: `/etc/default/temp-monitor-status`

### Windows

- Temperature: `remote-temp-monitor.ini`
- Status: `status-monitor.ini`

### Key Settings

```bash
# Temperature broadcast port (must match MagicMirror module)
TEMP_MONITOR_PORT=9876

# Status broadcast port (must match MagicMirror status module)  
STATUS_BROADCAST_PORT=9876

# Check interval for apt/git updates (seconds)
STATUS_BROADCAST_CHECK_INTERVAL=600  # Default: 10 minutes

# Shared secret for authenticated broadcasts (optional)
TEMP_MONITOR_SHARED_SECRET=your-secret
STATUS_BROADCAST_SHARED_SECRET=your-secret

# Broadcast targets (comma-separated or <broadcast>)
TEMP_MONITOR_TARGETS=192.168.1.0/24
STATUS_BROADCAST_TARGETS=192.168.1.0/24

# HTTP diagnostics ports (optional)
TEMP_MONITOR_HTTP_PORT=8080
STATUS_BROADCAST_HTTP_PORT=8080
```

### Desk Display Configuration

To enable blue dot monitoring:

1. **Create the folder** on your Raspberry Pi:
   ```bash
   mkdir -p /home/pi/desk_display
   ```

2. **Initialize git repository**:
   ```bash
   cd /home/pi/desk_display
   git init
   ```

3. **Add initial content and commit**:
   ```bash
   # Add files to track
   git add .
   git commit -m "Initial commit"
   ```

4. **Make changes** to trigger blue dot:
   ```bash
   # Edit files, add new files, etc.
   # Blue dot will appear on MagicMirror when changes are unstaged
   ```

5. **Commit changes** to clear blue dot:
   ```bash
   git add .
   git commit -m "Update desk display"
   ```

## How It Works

### APT Update Detection (Yellow Dot)

1. **Periodic Checks**: Every 10 minutes (configurable), the status broadcaster:
   - Runs `dpkg --verify` to check for broken packages
   - Runs `apt-get upgrade --dry-run` to check for upgrades
2. **Status Determination**:
   - If `dpkg --verify` returns errors → Sets `statusUpdateAvailable: true`
   - If `apt-get upgrade` would install packages → Sets `statusUpdateAvailable: true`
3. **Broadcast**: Sends status to configured UDP targets
4. **MagicMirror Display**: Shows yellow pulsing dot before affected device names

### Git Changes Detection (Blue Dot)

1. **Periodic Checks**: Every 10 minutes (configurable), the status broadcaster:
   - Checks if `/home/pi/desk_display` exists
   - Runs `git status --porcelain -s` to check for changes
2. **Status Determination**:
   - If desk_display folder exists and has unstaged changes → Sets `statusClientUpdate: true`
   - If desk_display folder doesn't exist → `statusClientUpdate: false`
3. **Broadcast**: Sends status to configured UDP targets
4. **MagicMirror Display**: Shows blue pulsing dot before affected device names

### Status Determination Flow

```
┌─────────────────────────────────┐
│   Check APT Updates (Yellow)    │
│   └─ dpkg --verify              │
│   └─ apt-get upgrade --dry-run  │
└─────────────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │statusUpdateAvailable │
        └─────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Check Git Changes (Blue)      │
│   └─ /home/pi/desk_display      │
│   └─ git status --porcelain -s  │
└─────────────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │statusClientUpdate│
        └─────────────────┘
```

### MagicMirror Display

The status monitor translates the flags into visual indicators:

| Flag | Visual Indicator | Color |
|------|------------------|-------|
| `statusUpdateAvailable: true` | ● (yellow dot) | `#FFFF00` |
| `statusClientUpdate: true` | ○ (blue dot) | `#00FFFF` |
| Both flags true | ●● (both dots) | Yellow + Blue |

## Service Management

### Check Status

```bash
# Check status
sudo systemctl status temp-monitor
sudo systemctl status status-monitor
```

### View Logs

```bash
# Temperature service logs
sudo journalctl -u temp-monitor -f

# Status service logs
sudo journalctl -u status-monitor -f
```

### Control Service

```bash
# Start
sudo systemctl start status-monitor

# Stop
sudo systemctl stop status-monitor

# Restart
sudo systemctl restart status-monitor

# Enable on boot
sudo systemctl enable status-monitor
```

## HTTP Endpoints

Each device exposes an HTTP endpoint for viewing status directly in a browser:

```
http://<raspberry-pi-ip>:9877/status
```

Response format:

```json
{
    "type": "status",
    "hostname": "raspberrypi",
    "device_id": "192.168.1.100",
    "timestamp": 1699900000,
    "statusUpdateAvailable": true,
    "statusClientUpdate": false,
    "lastSeen": 1699900000,
    "pi_model": "5",
    "pi_ram": "2GB"
}
```

## Configuration Options

### For Status Broadcaster (Edit env file)

| Option | Description | Default |
|--------|-------------|---------|
| `STATUS_BROADCAST_PORT` | UDP port for status broadcasts | `9876` |
| `STATUS_BROADCAST_HTTP_PORT` | HTTP diagnostics port | `9876` |
| `STATUS_BROADCAST_SHARED_SECRET` | HMAC shared secret | `` (empty) |
| `STATUS_BROADCAST_TARGETS` | Comma-separated broadcast targets | `<broadcast>` |
| `STATUS_BROADCAST_CHECK_INTERVAL` | How often to check for updates (seconds) | `600` (10 min) |

### For Status Monitor Module (Edit config.js)

| Option | Description | Default |
|--------|-------------|---------|
| `port` | UDP port to listen on | `9876` |
| `maxDeviceAge` | Remove devices not seen for this long (ms) | `30000` |
| `cleanupInterval` | How often to refresh status display (ms) | `60000` |
| `aggregatePort` | HTTP port for status rebroadcast | `9877` |
| `aggregateEndpointPath` | HTTP path for status endpoint | `/status` |
| `updatePulseDuration` | Yellow dot pulse duration (ms) | `2000` |
| `clientPulseDuration` | Blue dot pulse duration (ms) | `1500` |
| `updateAvailableColor` | Color for update dot | `#FFFF00` |
| `updateAvailableShadow` | Shadow color for update dot | `rgba(255,255,0,0.6)` |
| `clientUpdateColor` | Color for client update dot | `#00FFFF` |
| `clientUpdateShadow` | Shadow color for client update dot | `rgba(0,255,255,0.6)` |

## Troubleshooting

### Status Monitor not showing

1. **Check status service is running:**
   ```bash
   sudo systemctl status status-monitor
   ```

2. **Check service logs:**
   ```bash
   sudo journalctl -u status-monitor -f
   ```

3. **Verify status endpoint works in browser:**
   ```
   http://<raspberry-pi-ip>:9877/status
   ```

### Status broadcasts not reaching MagicMirror

1. **Check targets configuration:**
   - Targets should include all MagicMirror hosts
   - Or use `<broadcast>` for local network
   - Verify in `/etc/default/temp-monitor-status`

2. **Check for firewall blocks:**
   ```bash
   sudo ufw status
   ```

3. **Verify same network:**
   All devices and MagicMirror must be on the same subnet

### Status checks too slow?

The status broadcaster performs system checks which can take time:
- `dpkg --verify`: ~2 seconds
- `apt-get upgrade --dry-run`: ~60 seconds
- `git status --porcelain -s`: ~5 seconds

**To slow down checks**, increase the check interval:
```bash
sudo nano /etc/default/temp-monitor-status
# Change STATUS_BROADCAST_CHECK_INTERVAL=600 to a higher value
```

**To speed up checks**, reduce the interval:
```bash
sudo nano /etc/default/temp-monitor-status  
# Change STATUS_BROADCAST_CHECK_INTERVAL=600 to a lower value
```

### Desk Display not showing in MagicMirror

1. **Check folder exists:**
   ```bash
   ls -la /home/pi/desk_display
   ```

2. **Initialize git if needed:**
   ```bash
   cd /home/pi/desk_display
   git init
   git add .
   git commit -m "Initial"
   ```

3. **Make changes:**
   ```bash
   # Edit/add files in desk_display
   ```

### Blue dot showing when it shouldn't

1. **Check git is installed:**
   ```bash
   which git
   ```

2. **Check if changes are staged:**
   ```bash
   cd /home/pi/desk_display
   git status
   ```

3. **Commit changes to clear:**
   ```bash
   git add .
   git commit -m "Update"
   ```

### Both dots pulsing together?

This shouldn't happen - the dots pulse at different frequencies:
- Yellow: Every 2000ms
- Blue: Every 1500ms

If this is occurring, check:
1. MagicMirror's CSS is overriding the animations
2. Pulse durations in config are the same (they should differ)
3. System clock is not synchronized across devices

## Security

### Shared Secret Authentication

To prevent unauthorized devices from joining the network:

1. **Set shared secret on all broadcasters:**
   ```bash
   TEMP_MONITOR_SHARED_SECRET=your-secret-123
   STATUS_BROADCAST_SHARED_SECRET=your-secret-123
   ```

2. **Set same secret in MagicMirror config:**
   ```javascript
   sharedSecret: "your-secret-123"
   ```

Broadcast messages are signed with HMAC-SHA256 using the secret key, but the secret itself is never transmitted.

### Network Security

- Only use on trusted local networks
- The module broadcasts unencrypted data
- Consider using unicast targets:
  ```bash
  STATUS_BROADCAST_TARGETS=192.168.1.100,192.168.1.101
  ```

## Compatibility

| Component | Requirement |
|-----------|-------------|
| MagicMirror | Version 2.x |
| Status Module | Requires `MMM-RemoteTempMonitor` module |
| Remote Devices | Raspberry Pi with apt and git installed |
| System | Raspberry Pi OS (recommended) |
| Node.js | Version 18 or higher |
| Python | Version 3.x |

## Comparison: Full vs Minimal Installation

| Feature | install.sh (Minimal) | install-full.sh (Full) |
|---------|---------------------|------------------------|
| Temperature Monitor | ✓ | ✓ |
| Status Monitor | ✗ | ✓ |
| APT Update Detection | ✗ | ✓ |
| Git Check (desk_display) | ✗ | ✓ |
| System Checks | Limited | Full |
| Services Running | 1 | 2 |
| CPU Impact | Low | Moderate (during checks) |

**Recommendation:** Use `install-full.sh` if you want update indicators on your MagicMirror.

## Contributing

Contributions welcome! For the status monitor specifically:

- Improve apt/package detection accuracy
- Add support for other package managers (apk, pacman, etc.)
- Add support for client update detection
- Enhance visual design
- Improve configuration options

## License

MIT License - See the main [README.md](README.md) for details.

---

## Links

- [Main README](README.md) - For temperature monitoring features
- [MMM-RemoteTempMonitor](README.md) - Temperature display module
- [Status Broadcaster](status-broadcaster.md) - Detailed status service documentation