"""Regression tests for real status collection, caching, and diagnostics."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'remote-service/Pi/status-broadcaster.py'
spec = importlib.util.spec_from_file_location('status_broadcaster', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def broadcaster():
    with patch.object(module.StatusBroadcaster, '_setup_socket'), patch.object(module.StatusBroadcaster, '_setup_http_server'), patch.dict(os.environ, {}, clear=True):
        return module.StatusBroadcaster()


class StatusTests(unittest.TestCase):
    def test_message_and_hmac(self):
        item = broadcaster()
        item.shared_secret = 'secret'
        with patch.object(item, '_check_dpkg_status', return_value={'apt_updateAvailable': False, 'apt_upgradeAvailable': True}), patch.object(item, '_check_system_updates', return_value=True):
            status = item.get_status()
        data = json.loads(item.create_message(status))
        self.assertTrue(data['statusUpdateAvailable'])
        self.assertTrue(data['statusClientUpdate'])
        self.assertEqual(len(data['hmac']), 64)
        self.assertEqual(item.status_data, status)

    def test_checks_cached_but_status_refreshed(self):
        item = broadcaster()
        with patch.object(item, '_check_dpkg_status', return_value={'apt_updateAvailable': False, 'apt_upgradeAvailable': False}) as packages, patch.object(item, '_check_system_updates', return_value=False), patch.object(module.time, 'monotonic', side_effect=[0, 60, 600]):
            item.get_status(); item.get_status(); item.get_status()
            self.assertEqual(packages.call_count, 2)

    def test_pending_apt_updates(self):
        item = broadcaster()
        outputs = [subprocess.CompletedProcess([], 0, '', ''), subprocess.CompletedProcess([], 0, 'Inst curl [1] (2 repo)\nConf curl (2 repo)\n', '')]
        with patch.object(module.subprocess, 'run', side_effect=outputs):
            result = item._check_dpkg_status()
        self.assertTrue(result['apt_upgradeAvailable'])
        self.assertEqual(result['apt_upgradeCount'], 1)

    def test_clean_apt_status(self):
        item = broadcaster()
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            result = item._check_dpkg_status()
        self.assertFalse(result['apt_upgradeAvailable'])

    def test_env_overrides(self):
        with patch.object(module.StatusBroadcaster, '_setup_socket'), patch.object(module.StatusBroadcaster, '_setup_http_server'), patch.dict(os.environ, {'STATUS_BROADCAST_CHECK_INTERVAL': '700', 'STATUS_BROADCAST_PORT': '9999', 'STATUS_BROADCAST_INTERVAL': '90', 'STATUS_BROADCAST_HTTP_PORT': '0'}):
            item = module.StatusBroadcaster()
        self.assertEqual((item.check_interval, item.port, item.interval, item.http_port), (700, 9999, 90, 0))
        self.assertEqual(module.DEFAULT_HTTP_PORT, 9878)

    def test_invalid_interval_rejected(self):
        with patch.dict(os.environ, {'STATUS_BROADCAST_CHECK_INTERVAL': '-1'}):
            with self.assertRaises(ValueError):
                module.StatusBroadcaster()

    def test_http_handler_uses_initialized_state(self):
        item = broadcaster()
        item.http_port = 9878
        server = unittest.mock.MagicMock()
        with patch.object(module, 'DiagnosticsServer', return_value=server) as factory, patch.object(module.threading, 'Thread'):
            item._setup_http_server()
        handler = factory.call_args.args[1].__new__(factory.call_args.args[1])
        handler.path = '/status'
        handler.send_response = unittest.mock.Mock()
        handler.send_header = unittest.mock.Mock()
        handler.end_headers = unittest.mock.Mock()
        handler.wfile = unittest.mock.Mock()
        handler.do_GET()
        self.assertEqual(json.loads(handler.wfile.write.call_args.args[0]), {})
        self.assertEqual(factory.call_args.args[0], ('127.0.0.1', 9878))
