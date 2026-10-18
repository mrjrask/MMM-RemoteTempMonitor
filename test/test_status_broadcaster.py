#!/usr/bin/env python3
"""
Unit tests for status-broadcaster.py

Tests:
- Device detection (hostname, model, RAM)
- Status checking (apt updates)
- Message creation and signing
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Pi'))

# Mock subprocess before importing status_broadcaster
from unittest.mock import Mock, patch
original_run = subprocess.run
subprocess.run = Mock(returncode=0, stdout=b"", stderr=b"")

class TestStatusBroadcaster(unittest.TestCase):
    """Test StatusBroadcaster class"""
    
    def test_status_message_structure(self):
        """Test that status messages have the correct structure"""
        from status_broadcaster import StatusBroadcaster
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        
        # Mock the device detection
        broadcaster.hostname = "test-pi"
        broadcaster.device_id = "192.168.1.100"
        broadcaster.pi_model = "5"
        broadcaster.pi_ram = "2GB"
        
        status = broadcaster.get_status()
        
        self.assertIn("hostname", status)
        self.assertIn("device_id", status)
        self.assertIn("pi_model", status)
        self.assertIn("pi_ram", status)
        self.assertIn("lastSeen", status)
        self.assertIn("statusUpdateAvailable", status)
        self.assertIn("statusClientUpdate", status)
    
    def test_status_update_available_field(self):
        """Test that statusUpdateAvailable field exists and is a boolean"""
        from status_broadcaster import StatusBroadcaster
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        broadcaster.hostname = "test-pi"
        broadcaster.device_id = "192.168.1.100"
        
        status = broadcaster.get_status()
        
        self.assertIn("statusUpdateAvailable", status)
        self.assertIsInstance(status["statusUpdateAvailable"], bool)
    
    def test_status_client_update_field(self):
        """Test that statusClientUpdate field exists and is a boolean"""
        from status_broadcaster import StatusBroadcaster
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        broadcaster.hostname = "test-pi"
        broadcaster.device_id = "192.168.1.100"
        
        status = broadcaster.get_status()
        
        self.assertIn("statusClientUpdate", status)
        self.assertIsInstance(status["statusClientUpdate"], bool)
    
    def test_message_creation(self):
        """Test that status messages are properly formatted"""
        from status_broadcaster import StatusBroadcaster
        import json
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        broadcaster.hostname = "test-pi"
        broadcaster.device_id = "192.168.1.100"
        broadcaster.pi_model = "5"
        broadcaster.pi_ram = "2GB"
        
        status = broadcaster.get_status()
        message = broadcaster.create_message(status)
        
        # Verify JSON can be parsed
        parsed = json.loads(message)
        
        self.assertEqual(parsed["type"], "status")
        self.assertIn("hostname", parsed)
        self.assertIn("timestamp", parsed)
        self.assertIn("lastSeen", parsed)
        self.assertIn("pi_model", parsed)
        self.assertIn("pi_ram", parsed)
    
    def test_shared_secret(self):
        """Test that messages with shared secret include HMAC signature"""
        from status_broadcaster import StatusBroadcaster
        import json
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        broadcaster.hostname = "test-pi"
        broadcaster.shared_secret = "test-secret-key"
        broadcaster.device_id = "192.168.1.100"
        
        status = broadcaster.get_status()
        message = broadcaster.create_message(status)
        
        # Verify HMAC is present
        parsed = json.loads(message)
        self.assertIn("hmac", parsed)
        self.assertEqual(len(parsed["hmac"]), 64)  # SHA256 hex digest is 64 chars
    
    def test_magicmirror_status_message_structure(self):
        """
        Test that status messages are compatible with MagicMirror expectations.
        
        The MagicMirror status module expects these fields:
        - hostname: Device name
        - statusUpdateAvailable: Boolean (yellow dot)
        - statusClientUpdate: Boolean (blue dot)
        - lastSeen: Timestamp
        - Optional: pi_model, pi_ram
        """
        from status_broadcaster import StatusBroadcaster
        import json
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        broadcaster.hostname = "magic-monitor-pi"
        broadcaster.device_id = "mm-host"
        broadcaster.pi_model = "5"
        broadcaster.pi_ram = "2GB"
        
        # Mock get_status to return values compatible with MM status module
        def mock_get_status():
            return {
                "hostname": "magic-monitor-pi",
                "device_id": "mm-host",
                "statusUpdateAvailable": False,
                "statusClientUpdate": False,
                "lastSeen": 1234567890,
                "pi_model": "5",
                "pi_ram": "2GB"
            }
        
        broadcaster.get_status = mock_get_status
        
        message = broadcaster.create_message(status)
        
        parsed = json.loads(message)
        
        # Required fields
        self.assertEqual(parsed["hostname"], "magic-monitor-pi")
        self.assertEqual(parsed["device_id"], "mm-host")
        self.assertIn("statusUpdateAvailable", parsed)
        self.assertIn("statusClientUpdate", parsed)
        self.assertIn("lastSeen", parsed)
        
        # Optional fields that may be present
        self.assertIn("pi_model", parsed)
        self.assertIn("pi_ram", parsed)
        self.assertIn("timestamp", parsed)


if __name__ == "__main__":
    # Run with unittest
    unittest.main()