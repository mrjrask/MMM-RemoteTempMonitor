# Remote Status Monitor

The bundled companion module displays package and repository status received by
`MMM-RemoteTempMonitor`:

- Yellow: installed-package database issues or available APT upgrades.
- Cyan: uncommitted changes in the configured local repository. This does not
  check GitHub for new commits or observe MagicMirror notifications.

## Installation

On each Raspberry Pi broadcaster host:

```bash
cd ~/MMM-RemoteTempMonitor/remote-service/Pi
sudo ./install.sh
```

This installs both broadcasters. `install.sh` is a Bash wrapper around the Python
`install-full.sh`; the latter can be run with `sudo python3 install-full.sh`.
The account invoking sudo is used for new services. Existing service accounts are
preserved. For installation directly as root, select an existing account with
`TEMP_MONITOR_SERVICE_USER` (the fallback is `pi`).

On the MagicMirror host:

```bash
cd ~/MagicMirror/modules
ln -s MMM-RemoteTempMonitor/MMM-RemoteTempStatusMonitor MMM-RemoteTempStatusMonitor
```

Enable both `MMM-RemoteTempMonitor` and `MMM-RemoteTempStatusMonitor` in MagicMirror.
The temperature module receives both packet types and forwards status to the
companion. All temperature-module instances must share helper/listener settings;
conflicting configurations are rejected without changing the active listener.

## Settings

Edit `/etc/default/temp-monitor-status`, then restart `status-monitor.service`.

| Variable | Default | Purpose |
|---|---|---|
| `STATUS_BROADCAST_PORT` | `9876` | UDP destination; match the receiver's `port` |
| `STATUS_BROADCAST_INTERVAL` | `60` | Seconds between status broadcasts |
| `STATUS_BROADCAST_CHECK_INTERVAL` | `600` | Seconds between expensive package/git checks |
| `STATUS_BROADCAST_HTTP_PORT` | `9878` | TCP diagnostics port; `0` or empty disables HTTP |
| `STATUS_BROADCAST_HTTP_HOST` | `127.0.0.1` | Diagnostics bind address |
| `STATUS_BROADCAST_TARGETS` | broadcast | Comma-separated unicast/broadcast addresses |
| `STATUS_BROADCAST_SHARED_SECRET` | empty | Same secret as receiver `sharedSecret` |
| `STATUS_BROADCAST_REPO` | service user's `~/desk_display` | Repository checked for uncommitted changes |

Checks use `dpkg --audit`, `apt-get -s upgrade`, and `git status --porcelain -s`.
APT results reflect the system's existing package lists; this service does not
run privileged `apt-get update` or install packages. Results are cached for the
check interval, but a fresh status packet is emitted every broadcast interval.

The receiver expires status devices after `statusMaxDeviceAge` (default 20 minutes).
Signed packets require synchronized clocks, a timestamp within `maxPacketAge`
(default two minutes), and a newer timestamp than the preceding accepted packet
for that device and type. Repeated packets do not refresh last-seen time.

## Diagnostics

From the broadcaster itself:

```bash
curl http://127.0.0.1:9878/status
sudo systemctl status status-monitor.service
sudo journalctl -u status-monitor.service -n 50
```

Temperature diagnostics use TCP `9876`; MagicMirror aggregate diagnostics use TCP
`9877`. Status diagnostics use TCP `9878`. Legacy status configurations specifying
HTTP port `9876` are redirected to `9878` with a warning to prevent conflicts.

HTTP diagnostics bind only to loopback by default. To allow direct browser access
from a trusted LAN, set `STATUS_BROADCAST_HTTP_HOST=0.0.0.0`. That endpoint has no
HTTP authentication; UDP signing does not protect it. HTTP workers are capped at
eight, with five-second connection timeouts.

## Updates and recovery

```bash
cd ~/MMM-RemoteTempMonitor
git pull --ff-only
sudo ./remote-service/Pi/update.sh
```

The updater works from any directory and updates the temperature service plus the
status service if installed. It validates sources first, writes replacements
atomically, checks service activity over three seconds, and restores previous
files and service state on failure. Existing environment files are preserved.
Three backups per changed file are retained. A passing startup check cannot
predict later hardware, network, or runtime failures; systemd restarts crashed
services.

## Companion appearance

`updateAvailableColor`, `updateAvailableShadow`, `clientUpdateColor`, and
`clientUpdateShadow` control dot colors. `updatePulseDuration` (2000 ms) and
`clientPulseDuration` (1500 ms) control pulse durations. The header and names remain
visible when both indicators are off.

## Tests

```bash
npm test
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s test -p 'test_*.py' -v
```
