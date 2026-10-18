#!/usr/bin/env python3
"""
Remote Status Monitor - Broadcaster Service
Checks for system updates (apt) and broadcasts status to MagicMirror

This service periodically checks for apt package updates on the Raspberry Pi
and broadcasts status information to the MagicMirror module via UDP.

The status information includes:
- statusUpdateAvailable: Yellow dot indicator for apt package updates
- statusClientUpdate: Blue dot indicator for client/software updates

By mrjrask
MIT Licensed
"""

import socket
import hashlib
import hmac
import json
import time
import platform
import logging
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

# Configuration
BROADCAST_PORT = 9876
BROADCAST_INTERVAL = 60  # seconds - base check interval
DEFAULT_HTTP_PORT = 9876
STATUS_FILE = "/tmp/remote-temp-status.json"
STATUS_CHECK_INTERVAL = 600  # Check for updates every 10 minutes (default)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('StatusBroadcaster')


def parse_status_port(raw_value):
    """Parse the optional HTTP diagnostics port without breaking UDP broadcasts."""
    if raw_value is None:
        return DEFAULT_HTTP_PORT

    raw_value = raw_value.strip()
    if raw_value == "":
        logger.warning("STATUS_BROADCAST_HTTP_PORT is empty; disabling HTTP status endpoint")
        return 0

    try:
        port = int(raw_value)
    except ValueError:
        logger.warning("STATUS_BROADCAST_HTTP_PORT must be a number; disabling HTTP status endpoint")
        return 0

    if port < 0 or port > 65535:
        logger.warning("STATUS_BROADCAST_HTTP_PORT must be between 0 and 65535; disabling HTTP status endpoint")
        return 0

    return port


class StatusBroadcaster:
    """Broadcasts system update status over UDP"""

    def __init__(self, port=BROADCAST_PORT, interval=BROADCAST_INTERVAL):
        self.port = port
        self.interval = interval
        self.hostname = platform.node()
        self.shared_secret = os.getenv("STATUS_BROADCAST_SHARED_SECRET", "").strip()
        self.http_port = parse_status_port(os.getenv("STATUS_BROADCAST_HTTP_PORT"))
        self.sock = None
        self.http_server = None
        self.http_thread = None
        self.targets = self._get_targets()
        self.device_id = self.get_device_id()
        self.pi_model = self.get_pi_model()
        self.pi_ram = self.get_pi_ram()
        self._setup_socket()
        self._setup_http_server()

    def _setup_socket(self):
        """Setup UDP broadcast socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info(f"UDP socket created for broadcast on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to create socket: {e}")
            raise

    def _setup_http_server(self):
        """Start a small HTTP endpoint for direct browser diagnostics."""
        if self.http_port <= 0:
            logger.info("HTTP status endpoint disabled")
            return

        broadcaster = self

        class StatusRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path not in ("/status", "/"):
                    self.send_error(404, "Not Found")
                    return

                body = json.dumps(broadcaster.status_data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                logger.debug("HTTP %s - %s", self.address_string(), format % args)

        try:
            self.http_server = ThreadingHTTPServer(("0.0.0.0", self.http_port), StatusRequestHandler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            logger.info(f"HTTP status endpoint available at http://0.0.0.0:{self.http_port}/status")
        except Exception as e:
            logger.error(f"Failed to start HTTP endpoint on port {self.http_port}: {e}")
            self.http_server = None
            self.http_thread = None

    def _get_targets(self):
        """Determine target addresses for status updates."""
        targets_raw = os.getenv("STATUS_BROADCAST_TARGETS", "").strip()
        if not targets_raw:
            return ["<broadcast>"]

        targets = [target.strip() for target in targets_raw.split(",") if target.strip()]
        if not targets:
            return ["<broadcast>"]

        return targets

    def get_device_id(self):
        """
        Get a unique device identifier
        Returns: Device hostname or first interface address
        """
        try:
            hostname = platform.node()
            if hostname and len(hostname) > 0:
                return hostname
            
            # Fallback to first available network interface
            interfaces = subprocess.run(['ip', '-4', 'addr', 'show'], 
                                       capture_output=True, text=True, timeout=5)
            if interfaces.returncode == 0:
                # Extract first IPv4 address
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', interfaces.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            logger.warning(f"Could not determine device ID: {e}")
        
        return self.hostname

    def get_pi_model(self):
        """
        Detect Raspberry Pi model
        Returns: Model string like "4", "5", "0W", "0W2", "2", "3", "CM5", or None
        """
        try:
            model_file = Path("/proc/device-tree/model")
            if model_file.exists():
                model_str = model_file.read_text().strip().lower()
                return self._parse_pi_model(model_str)
            
            # Fallback to /proc/cpuinfo
            cpuinfo_file = Path("/proc/cpuinfo")
            if cpuinfo_file.exists():
                cpuinfo = cpuinfo_file.read_text().lower()
                for line in cpuinfo.split('\n'):
                    if line.startswith('model') and 'raspberry pi' in line:
                        return self._parse_pi_model(line)
            
            return None
        except Exception as e:
            logger.warning(f"Could not detect Pi model: {e}")
            return None

    def _parse_pi_model(self, model_str):
        """Parse model string and return simplified model name"""
        if 'pi 5' in model_str:
            return "5"
        elif 'compute module 5' in model_str or 'cm5' in model_str:
            return "CM5"
        elif 'pi 4' in model_str:
            return "4"
        elif 'pi 3' in model_str:
            return "3"
        elif 'pi 2' in model_str:
            return "2"
        elif 'zero 2' in model_str:
            return "0W2"
        elif 'zero w' in model_str or 'zero wireless' in model_str:
            return "0W"
        elif 'zero' in model_str:
            return "0W"
        else:
            return None

    def get_pi_ram(self):
        """
        Detect total RAM
        Returns: RAM string like "512MB", "1GB", "2GB", "4GB", "8GB", "16GB", or None
        """
        try:
            meminfo_file = Path("/proc/meminfo")
            if not meminfo_file.exists():
                return None

            meminfo = meminfo_file.read_text()
            for line in meminfo.split('\n'):
                if line.startswith('MemTotal:'):
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
        marketing_values = [512, 1024, 2048, 4096, 8192, 16384]
        closest = min(marketing_values, key=lambda x: abs(x - mem_mb))
        if closest < 1024:
            return f"{closest}MB"
        else:
            return f"{closest // 1024}GB"

    def _systemd_is_active(self, service_name):
        """Check if a systemd service is active"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == 'active'
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    def _check_dpkg_status(self):
        """
        Check for apt/dpkg issues
        Returns: Dictionary with update status
        """
        result = {
            "apt_updateAvailable": False,
            "apt_upgradeAvailable": False,
            "apt_upgradeCount": 0,
            "checking_time": 0
        }

        try:
            # Check for broken dependencies
            result["checking_time"] += 2
            output = subprocess.run(
                ['dpkg', '--verify'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if output.returncode != 0:
                result["apt_updateAvailable"] = True
                result["checking_time"] += 1
                logger.warning(f"dpkg --verify returned errors: {output.stdout[:100]}")

            # Check for upgradable packages
            result["checking_time"] += 2
            output = subprocess.run(
                ['apt-get', 'upgrade', '--dry-run'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if output.returncode == 0:
                # Count packages that would be upgraded/installed
                lines = output.split('\n')
                for line in lines:
                    if 'Preparing to unpack' in line:
                        result["apt_upgradeCount"] += 1
                    elif 'Would install' in line:
                        result["apt_upgradeCount"] += 1
                    elif '0 upgraded, 0 newly installed' in line:
                        break  # No upgrades available
                
                if result["apt_upgradeCount"] > 0:
                    result["apt_upgradeAvailable"] = True

            else:
                # apt-get upgrade failed, need to run apt-get update
                result["apt_updateAvailable"] = True
                result["checking_time"] += 1

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking package status for {self.hostname}")
        except FileNotFoundError:
            logger.warning("apt/dpkg not found - cannot check for updates")
        except Exception as e:
            logger.error(f"Error checking package status: {e}")

        return result

    def _check_desk_display_git_status(self):
        """
        Check for git changes in the desk_display folder.
        Returns: Boolean indicating if there are uncommitted/staged changes
        """
        desk_display_path = Path("/home/pi/desk_display")
        
        # Check if desk_display folder exists
        if not desk_display_path.exists():
            logger.debug("desk_display folder not found")
            return False
        
        # Check if there's a .git folder
        git_folder = desk_display_path / ".git"
        if not git_folder.exists():
            logger.debug("No .git folder found in desk_display")
            return False
        
        try:
            # Run git status to check for changes
            # -s check if there are staged changes
            # --porcelain get machine-readable output
            output = subprocess.run(
                ['git', '-C', str(desk_display_path), 'status', '--porcelain', '-s'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if output.returncode != 0:
                logger.warning(f"Git status check failed: {output.stderr[:100]}")
                return False
            
            # Parse porcelain git status output
            # Lines starting with " " (space) = staged changes
            # Lines starting with "M" = modified files
            # Lines starting with "A" = added files
            # Lines starting with "D" = deleted files
            # Lines starting with "R" = renamed files
            # Lines starting with "C" = copied files
            # Lines starting with "T" = type changed
            # Lines starting with "C" = copied files
            # Lines starting with "U" = unmerged files
            # Lines starting with "!" = ignored files
            # Lines starting with "?" = untracked files
            
            has_changes = False
            
            for line in output.stdout:
                line = line.strip()
                if not line:
                    continue
                
                # Skip the first line which is usually a header
                if not has_changes and (line.startswith('##') or line.startswith(' ')):
                    continue
                
                # Check for various change types
                if line.startswith('M') or \
                   line.startswith('A') or \
                   line.startswith('D') or \
                   line.startswith('R') or \
                   line.startswith('C') or \
                   line.startswith('T') or \
                   line.startswith('U') or \
                   line.startswith('?'):
                    has_changes = True
                    logger.info(f"Found git changes in desk_display: {line[:50]}")
                    break
            
            return has_changes
            
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking git status for desk_display")
        except FileNotFoundError:
            logger.warning("git command not found - cannot check desk_display")
        except Exception as e:
            logger.error(f"Error checking git status: {e}")
        
        return False

    def _check_system_updates(self):
        """
        Check for client/software updates
        This checks for changes in the desk_display folder via git
        
        Returns: Boolean indicating if there's a client update available
        """
        # Check for git changes in desk_display folder
        return self._check_desk_display_git_status()

    def broadcast(self, status):
        """Send status message via UDP broadcast or unicast targets"""
        success = True
        try:
            for target in self.targets:
                target_address = (target, self.port)
                try:
                    self.sock.sendto(status.encode('utf-8'), target_address)
                except Exception as send_error:
                    logger.error(f"Broadcast to {target} failed: {send_error}")
                    success = False
            return success
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            return False

    def run(self):
        """Main loop - check status and broadcast"""
        logger.info(f"Starting status broadcaster for '{self.hostname}'")
        logger.info(f"Broadcasting on port {self.port} every {self.interval} seconds")
        logger.info(f"Targets: {', '.join(self.targets)}")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"Pi Model: {self.pi_model}")
        logger.info(f"Pi RAM: {self.pi_ram}")

        try:
            # Initial broadcast
            status = self.get_status()
            message = self.create_message(status)
            if message and self.broadcast(message):
                logger.info(f"Initial status: {self.hostname} - "
                           f"update={status['statusUpdateAvailable']}, "
                           f"client={status['statusClientUpdate']}")

            # Main loop - broadcast every interval
            while True:
                status = self.get_status()
                message = self.create_message(status)
                
                if message and self.broadcast(message):
                    logger.debug(f"Status: {self.hostname} - "
                               f"update={status['statusUpdateAvailable']}, "
                               f"client={status['statusClientUpdate']}")

                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("Status broadcaster stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            if self.http_server:
                self.http_server.shutdown()
                self.http_server.server_close()
                logger.info("HTTP endpoint stopped")
            if self.sock:
                self.sock.close()
                logger.info("Socket closed")

    def create_message(self, status):
        """Create JSON status message"""
        message = {
            "type": "status",
            "hostname": status["hostname"],
            "device_id": status.get("device_id"),
            "timestamp": int(time.time()),
            "statusUpdateAvailable": status.get("statusUpdateAvailable", False),
            "statusClientUpdate": status.get("statusClientUpdate", False),
            "lastSeen": status["lastSeen"]
        }

        # Include device metadata
        message["pi_model"] = status.get("pi_model")
        message["pi_ram"] = status.get("pi_ram")

        if self.shared_secret:
            message["hmac"] = self._sign_message(message)

        return json.dumps(message)

    def _sign_message(self, message):
        """Create an HMAC signature for a status message."""
        payload = json.dumps(message, separators=(",", ":"))
        return hmac.new(
            self.shared_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()


def main():
    """Entry point"""
    broadcaster = StatusBroadcaster()
    broadcaster.run()


if __name__ == "__main__":
    main()