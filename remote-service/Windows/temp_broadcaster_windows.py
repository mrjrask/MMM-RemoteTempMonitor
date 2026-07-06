#!/usr/bin/env python3
"""
Remote Temperature Monitor - Windows Broadcaster Service
Broadcasts CPU temperature over UDP for MagicMirror module
"""

import json
import logging
import os
import platform
import socket
import time

try:
    import wmi
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: wmi. Please run install.ps1 or 'pip install wmi pywin32'."
    ) from exc

# Configuration
BROADCAST_PORT = 9876
BROADCAST_INTERVAL = 5  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TempBroadcaster')


class TemperatureBroadcaster:
    """Broadcasts CPU temperature over UDP"""

    def __init__(self, port=BROADCAST_PORT, interval=BROADCAST_INTERVAL):
        self.port = port
        self.interval = interval
        self.hostname = platform.node()
        self.shared_secret = os.getenv("TEMP_MONITOR_SHARED_SECRET", "").strip()
        self.cpu_arch = platform.machine()
        self.sock = None
        self.targets = self._get_targets()
        self._setup_socket()

    def _get_targets(self):
        """Determine target addresses for temperature updates."""
        targets_raw = os.getenv("TEMP_MONITOR_TARGETS", "").strip()
        if not targets_raw:
            return ["<broadcast>"]

        targets = [target.strip() for target in targets_raw.split(",") if target.strip()]
        if not targets:
            return ["<broadcast>"]

        return targets

    def _setup_socket(self):
        """Setup UDP broadcast socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info(f"UDP socket created for broadcast on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to create socket: {e}")
            raise

    def _read_acpi_temperature(self):
        """Read temperature via ACPI thermal zones (may not be CPU)."""
        try:
            wmi_client = wmi.WMI(namespace="root\\wmi")
            temps = wmi_client.MSAcpi_ThermalZoneTemperature()
            if not temps:
                return None
            temp_c = (temps[0].CurrentTemperature / 10.0) - 273.15
            return round(temp_c, 1)
        except Exception:
            return None

    def _read_openhardwaremonitor_temperature(self):
        """Read temperature via OpenHardwareMonitor if available."""
        try:
            wmi_client = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            sensors = wmi_client.Sensor()
            cpu_temps = [
                sensor for sensor in sensors
                if sensor.SensorType == "Temperature" and "CPU" in sensor.Name
            ]
            if not cpu_temps:
                return None
            cpu_temps.sort(key=lambda s: s.Name)
            return round(float(cpu_temps[0].Value), 1)
        except Exception:
            return None

    def get_cpu_temperature(self):
        """Read CPU temperature from available sources."""
        temp = self._read_openhardwaremonitor_temperature()
        if temp is not None:
            return temp
        return self._read_acpi_temperature()

    def create_message(self, temp_celsius):
        """Create JSON message with temperature data"""
        if temp_celsius is None:
            return None

        temp_fahrenheit = round((temp_celsius * 9 / 5) + 32, 1)

        message = {
            "type": "temperature",
            "hostname": self.hostname,
            "temperature": {
                "celsius": temp_celsius,
                "fahrenheit": temp_fahrenheit,
            },
            "platform": "Windows",
            "cpu_arch": self.cpu_arch,
            "timestamp": int(time.time()),
        }

        if self.shared_secret:
            message["auth_token"] = self.shared_secret

        return json.dumps(message)

    def broadcast(self, message):
        """Send message via UDP broadcast or unicast targets"""
        success = True
        for target in self.targets:
            try:
                self.sock.sendto(message.encode('utf-8'), (target, self.port))
                logger.debug(f"Broadcasted to {target}: {message}")
            except Exception as e:
                logger.error(f"Broadcast to {target} failed: {e}")
                success = False
        return success

    def run(self):
        """Main loop - read temperature and broadcast"""
        logger.info(f"Starting temperature broadcaster for '{self.hostname}'")
        logger.info(
            f"Broadcasting on port {self.port} every {self.interval} seconds"
        )

        try:
            while True:
                temp = self.get_cpu_temperature()

                if temp is not None:
                    message = self.create_message(temp)
                    if message and self.broadcast(message):
                        logger.info(
                            f"Broadcast: {self.hostname} - {temp}°C ({(temp * 9/5) + 32:.1f}°F)"
                        )
                else:
                    logger.warning("No temperature data available")

                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("Broadcaster stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            if self.sock:
                self.sock.close()
                logger.info("Socket closed")


def main():
    """Entry point"""
    broadcaster = TemperatureBroadcaster()
    broadcaster.run()


if __name__ == "__main__":
    main()
