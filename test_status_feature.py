#!/usr/bin/env python3
"""
Demo script to demonstrate the status broadcaster feature.

This script simulates how the status broadcaster would work and shows
the expected data structures for the MagicMirror status module.
"""

import json

# Simulated status data structure
# This is what each Raspberry Pi status broadcaster would send
SIMULATED_STATUS_DATA = [
    {
        "type": "status",
        "hostname": "living-room-pi",
        "device_id": "192.168.1.100",
        "timestamp": 1699900000,
        "statusUpdateAvailable": False,
        "statusClientUpdate": False,
        "lastSeen": 1699900000,
        "pi_model": "5",
        "pi_ram": "2GB"
    },
    {
        "type": "status",
        "hostname": "kitchen-pi",
        "device_id": "192.168.1.101",
        "timestamp": 1699900000,
        "statusUpdateAvailable": True,
        "statusClientUpdate": False,
        "lastSeen": 1699900000,
        "pi_model": "4",
        "pi_ram": "1GB"
    },
    {
        "type": "status",
        "hostname": "office-pi",
        "device_id": "192.168.1.102",
        "timestamp": 1699900000,
        "statusUpdateAvailable": True,
        "statusClientUpdate": True,
        "lastSeen": 1699900000,
        "pi_model": "5",
        "pi_ram": "4GB"
    },
    {
        "type": "status",
        "hostname": "guest-pi",
        "device_id": "192.168.1.103",
        "timestamp": 1699900000,
        "statusUpdateAvailable": False,
        "statusClientUpdate": True,
        "lastSeen": 1699900000,
        "pi_model": "0W",
        "pi_ram": "256MB"
    }
]


def generate_magic_mirror_data():
    """
    Transform status data into MagicMirror status module format.
    
    The status module expects:
    - hostname
    - device_id (or deviceId)
    - statusUpdateAvailable (yellow dot - apt updates)
    - statusClientUpdate (blue dot - client updates)
    - lastSeen
    - Optional: pi_model, pi_ram
    """
    devices = []
    
    for status in SIMULATED_STATUS_DATA:
        device = {
            "hostname": status["hostname"],
            "device_id": status["device_id"],
            "statusUpdateAvailable": status["statusUpdateAvailable"],
            "statusClientUpdate": status["statusClientUpdate"],
            "lastSeen": status["lastSeen"],
            "pi_model": status.get("pi_model"),
            "pi_ram": status.get("pi_ram")
        }
        devices.append(device)
    
    return {
        "type": "status",
        "count": len(devices),
        "updatedAt": "2026-10-17T21:00:00Z",
        "devices": devices,
        "temperatures": []  # Status monitor doesn't need this
    }


def print_status_preview(data):
    """
    Print a preview of what the status module will display.
    
    This simulates what the user will see on their MagicMirror.
    """
    print("\n" + "="*60)
    print("MAGICMIRROR STATUS MONITOR DISPLAY PREVIEW")
    print("="*60 + "\n")
    
    print("Status Indicators Legend:")
    print("  ● Yellow dot = APT package updates available")
    print("  ○ Blue dot = Client software update available")
    print("  Neither dot = All systems up to date\n")
    
    print("Device Status Table:\n")
    print(f"{'Device Name':<20} {'Status Dots':<15} {'Model/RAM':<15}")
    print("-" * 50)
    
    for device in data["devices"]:
        # Show status dots
        dots = ""
        if device["statusUpdateAvailable"]:
            dots += "● "  # Yellow dot
        if device["statusClientUpdate"]:
            dots += "○ "  # Blue dot
        
        # Format for display
        device_name = device["hostname"]
        if device["pi_model"]:
            device_name += f" ({device['pi_model']})"
        elif device["pi_ram"]:
            device_name += f" ({device['pi_ram']})"
        
        print(f"{device_name:<20} {dots:<15} {'':<15}")
    
    print("\n" + "="*60 + "\n")


def explain_status_behavior():
    """Explain how the status indicators work."""
    print("=" * 60)
    print("STATUS INDICATOR BEHAVIOR")
    print("=" * 60 + "\n")
    
    print("YELLOW DOT (APT Updates):")
    print("  ──────────────────────")
    print("  • Appears when 'apt-get upgrade' has packages to install")
    print("  • Checked using cached package lists with 'apt-get -s upgrade'")
    print("  • Dot pulses every 2000ms (2 seconds)")
    print("  • Color: Yellow (#FFFF00)")
    print("  • Only shows before device NAME, not temperature")
    print()
    
    print("BLUE DOT (CLIENT Updates):")
    print("  ───────────────────────")
    print("  • Appears when the configured local repository has uncommitted changes")
    print("  • Detected when the configured local repository has uncommitted changes")
    print("  • Dot pulses every 1500ms (1.5 seconds)")
    print("  • Color: Blue (#00FFFF)")
    print("  • Only shows before device NAME, not temperature")
    print()
    
    print("BOTH DOTS (apt AND client updates):")
    print("  ────────────────────────────────")
    print("  • Both dots appear simultaneously before device name")
    print("  • Dots pulse at DIFFERENT frequencies (2s vs 1.5s)")
    print("  • This prevents visual 'sync' - dots don't pulse together")
    print("  • Temperature column position is NOT affected")
    print()
    
    print("VISUAL EXAMPLE:")
    print("  ┌──────────────────────────────────────────────┐")
    print("  │ Device         ●● Device Name        35.2°C │")
    print("  │               ●●  (Pi 5 | 2GB)     95.8°F │")
    print("  └──────────────────────────────────────────────┘")
    print("     Legend: ● = Yellow/Blue dots on left")
    print("            = Temperature values on right (fixed)")
    print("  └──────────────────────────────────────────────┘")
    print()
    
    print("NOTES:")
    print("  • Status checks run every 10 minutes (configurable)")
    print("  • Status dots appear to the LEFT of device name")
    print("  • Device name column shifts right when dots appear")
    print("  • Temperature columns stay FIXED in position")
    print()
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60 + "\n")


def main():
    """Run the demonstration."""
    print("\n" + "=" * 60)
    print("RMM-RemoteTempMonitor STATUS FEATURE DEMO")
    print("=" * 60 + "\n")
    
    print("This demo shows how the status broadcaster feature works:")
    print("  1. Each Raspberry Pi runs a status broadcaster")
    print("  2. Status broadcasts contain: hostname, device_id,")
    print("     statusUpdateAvailable, statusClientUpdate, lastSeen")
    print("  3. MagicMirror Status Monitor displays these as:")
    print("     Device names with colored pulsing dots")
    print()
    
    # Generate and display status data
    status_data = generate_magic_mirror_data()
    print_status_preview(status_data)
    
    # Explain the behavior
    explain_status_behavior()
    
    print("The status module will:")
    print("  • Display devices with yellow/blue dots when updates are available")
    print("  • Only shift the DEVICE column - temperatures stay fixed")
    print("  • Different pulse timing prevents visual sync")
    print()
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()