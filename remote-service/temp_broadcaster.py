#!/usr/bin/env python3
"""
Remote Temperature Monitor - Broadcaster Service
Broadcasts Raspberry Pi CPU temperature over UDP for MagicMirror module
"""

import socket
import json
import time
import platform
import logging
from pathlib import Path

# Configuration
BROADCAST_PORT = 9876
BROADCAST_INTERVAL = 5  # seconds
TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"

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
        self.sock = None
        self._setup_socket()

    def _setup_socket(self):
        """Setup UDP broadcast socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info(f"UDP socket created for broadcast on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to create socket: {e}")
            raise

    def get_cpu_temperature(self):
        """
        Read CPU temperature from Raspberry Pi thermal zone
        Returns temperature in Celsius
        """
        try:
            temp_file = Path(TEMP_FILE)
            if temp_file.exists():
                # Temperature is in millidegrees Celsius
                temp_raw = temp_file.read_text().strip()
                temp_celsius = float(temp_raw) / 1000.0
                return round(temp_celsius, 1)
            else:
                logger.warning(f"Temperature file not found: {TEMP_FILE}")
                # Return a test value if running on non-RPi system
                return None
        except Exception as e:
            logger.error(f"Error reading temperature: {e}")
            return None

    def create_message(self, temp_celsius):
        """Create JSON message with temperature data"""
        if temp_celsius is None:
            return None

        # Calculate Fahrenheit
        temp_fahrenheit = round((temp_celsius * 9/5) + 32, 1)

        message = {
            "type": "temperature",
            "hostname": self.hostname,
            "temperature": {
                "celsius": temp_celsius,
                "fahrenheit": temp_fahrenheit
            },
            "timestamp": int(time.time())
        }

        return json.dumps(message)

    def broadcast(self, message):
        """Send message via UDP broadcast"""
        try:
            broadcast_address = ('<broadcast>', self.port)
            self.sock.sendto(message.encode('utf-8'), broadcast_address)
            logger.debug(f"Broadcasted: {message}")
            return True
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            return False

    def run(self):
        """Main loop - read temperature and broadcast"""
        logger.info(f"Starting temperature broadcaster for '{self.hostname}'")
        logger.info(f"Broadcasting on port {self.port} every {self.interval} seconds")

        try:
            while True:
                temp = self.get_cpu_temperature()

                if temp is not None:
                    message = self.create_message(temp)
                    if message and self.broadcast(message):
                        logger.info(f"Broadcast: {self.hostname} - {temp}°C ({(temp * 9/5) + 32:.1f}°F)")
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
