#!/usr/bin/env python3
"""
Remote Temperature Monitor - macOS Broadcaster Service
Broadcasts CPU temperature over UDP for MagicMirror module
"""

import hashlib
import hmac
import json
import logging
import os
import platform
import socket
import subprocess
import time
from pathlib import Path

# Configuration
BROADCAST_PORT = 9876
BROADCAST_INTERVAL = 5  # seconds
POWERMETRICS_PATH = "/usr/bin/powermetrics"

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
        self.sock = None
        self.targets = self._get_targets()
        self.cpu_arch = platform.machine()
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

    def _parse_powermetrics_output(self, output):
        """Parse powermetrics output for CPU temperature."""
        patterns = [
            "CPU die temperature:",
            "CPU temperature:",
            "E-CPU die temperature:",
            "P-CPU die temperature:",
        ]

        for line in output.splitlines():
            for pattern in patterns:
                if pattern in line:
                    try:
                        value = line.split(pattern, 1)[1].strip()
                        value = value.replace("C", "").replace("°", "").strip()
                        return round(float(value), 1)
                    except (ValueError, IndexError):
                        continue

        return None

    def get_cpu_temperature(self):
        """Read CPU temperature using powermetrics (Intel + Apple Silicon)."""
        powermetrics = Path(POWERMETRICS_PATH)
        if not powermetrics.exists():
            logger.error("powermetrics not found; cannot read CPU temperature")
            return None

        try:
            result = subprocess.run(
                [POWERMETRICS_PATH, "--samplers", "smc", "-n", "1"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = f"{result.stdout}\n{result.stderr}"
            return self._parse_powermetrics_output(output)
        except subprocess.CalledProcessError as exc:
            output = f"{exc.stdout}\n{exc.stderr}"
            logger.error(f"powermetrics failed: {output}")
            return None

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
            "platform": "macOS",
            "cpu_arch": self.cpu_arch,
            "timestamp": int(time.time()),
        }

        if self.shared_secret:
            message["hmac"] = self._sign_message(message)

        return json.dumps(message)

    def _sign_message(self, message):
        """Create an HMAC signature for a temperature message."""
        payload = json.dumps(message, separators=(",", ":"))
        return hmac.new(
            self.shared_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

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
