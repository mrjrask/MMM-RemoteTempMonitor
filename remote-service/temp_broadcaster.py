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
import re
from pathlib import Path

# Configuration
BROADCAST_PORT = 9876
BROADCAST_INTERVAL = 5  # seconds
TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"
MODEL_FILE = "/proc/device-tree/model"
CPUINFO_FILE = "/proc/cpuinfo"
MEMINFO_FILE = "/proc/meminfo"

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
        self.pi_model = self.get_pi_model()
        self.pi_ram = self.get_pi_ram()
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

    def get_pi_model(self):
        """
        Detect Raspberry Pi model and map to simplified name
        Returns: Model string like "4", "5", "0W", "0W2", "2", "3", "CM5", or None
        """
        try:
            # Try reading from device-tree model file first
            model_file = Path(MODEL_FILE)
            if model_file.exists():
                model_str = model_file.read_text().strip().lower()
                return self._parse_pi_model(model_str)

            # Fallback to cpuinfo
            cpuinfo_file = Path(CPUINFO_FILE)
            if cpuinfo_file.exists():
                cpuinfo = cpuinfo_file.read_text().lower()
                # Look for Model line in cpuinfo
                for line in cpuinfo.split('\n'):
                    if line.startswith('model') and 'raspberry pi' in line:
                        return self._parse_pi_model(line)

            return None
        except Exception as e:
            logger.warning(f"Could not detect Pi model: {e}")
            return None

    def _parse_pi_model(self, model_str):
        """Parse model string and return simplified model name"""
        model_str = model_str.lower()

        # Pi 5
        if 'pi 5' in model_str:
            return "5"
        # Compute Module 5
        elif 'compute module 5' in model_str or 'cm5' in model_str:
            return "CM5"
        # Pi 4
        elif 'pi 4' in model_str:
            return "4"
        # Pi 3
        elif 'pi 3' in model_str:
            return "3"
        # Pi 2
        elif 'pi 2' in model_str:
            return "2"
        # Pi Zero 2 W
        elif 'zero 2' in model_str:
            return "0W2"
        # Pi Zero W (original)
        elif 'zero w' in model_str or 'zero wireless' in model_str:
            return "0W"
        # Pi Zero (non-wireless)
        elif 'zero' in model_str:
            return "0W"
        else:
            return None

    def get_pi_ram(self):
        """
        Detect total RAM and map to closest marketing value
        Returns: RAM string like "512MB", "1GB", "2GB", "4GB", "8GB", "16GB", or None
        """
        try:
            meminfo_file = Path(MEMINFO_FILE)
            if not meminfo_file.exists():
                return None

            meminfo = meminfo_file.read_text()
            # Look for MemTotal line
            for line in meminfo.split('\n'):
                if line.startswith('MemTotal:'):
                    # Extract KB value
                    match = re.search(r'(\d+)\s*kB', line)
                    if match:
                        mem_kb = int(match.group(1))
                        mem_mb = mem_kb / 1024
                        return self._map_ram_to_marketing(mem_mb)

            return None
        except Exception as e:
            logger.warning(f"Could not detect RAM: {e}")
            return None

    def _map_ram_to_marketing(self, mem_mb):
        """Map actual RAM to closest marketing value"""
        # Marketing values in MB
        marketing_values = [512, 1024, 2048, 4096, 8192, 16384]

        # Find closest value
        closest = min(marketing_values, key=lambda x: abs(x - mem_mb))

        # Format output
        if closest < 1024:
            return f"{closest}MB"
        else:
            return f"{closest // 1024}GB"

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
            "pi_model": self.pi_model,
            "pi_ram": self.pi_ram,
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
