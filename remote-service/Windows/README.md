# Windows Remote Temperature Monitor

This installer runs a Python service that broadcasts CPU temperature over UDP for the MagicMirror module.

## Requirements

- Windows 10/11
- Python 3 installed and available in PATH
- Administrator access

## Installation

Open PowerShell as Administrator and run:

```powershell
cd MMM-RemoteTempMonitor\remote-service\Windows
.\install.ps1
```

The installer:
- Copies the broadcaster script to `%ProgramData%\RemoteTempMonitor`
- Installs required Python dependencies (`wmi`, `pywin32`)
- Registers a scheduled task that runs at startup as SYSTEM

## Temperature Sources

The script checks multiple sources for temperature data:

1. **OpenHardwareMonitor** (preferred)
   - If you run OpenHardwareMonitor, it exposes CPU temperature via WMI.
2. **ACPI Thermal Zones** (fallback)
   - Some systems expose a temperature via `MSAcpi_ThermalZoneTemperature`. This may not map to CPU temperature on all hardware.

## Uninstall

```powershell
Unregister-ScheduledTask -TaskName "RemoteTempMonitor" -Confirm:$false
Remove-Item -Recurse -Force "$env:ProgramData\RemoteTempMonitor"
```


## Optional Targets and Authentication

By default, the broadcaster sends UDP packets to the local broadcast address. To send updates to specific MagicMirror hosts or directed broadcast addresses, set a comma-separated target list before starting the service:

```bash
TEMP_MONITOR_TARGETS=10.0.0.10,192.168.1.255
```

To require authenticated packets, set the same shared secret here and in the MagicMirror module config:

```bash
TEMP_MONITOR_SHARED_SECRET=change-me
```
