"""Bounded HTTP workers, command timeout, and relocatable wrapper tests."""
import importlib.util
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'remote-service'))
from broadcaster_common import DiagnosticsServer
from http.server import ThreadingHTTPServer


class RuntimeSafetyTests(unittest.TestCase):
    def test_http_concurrency_is_bounded(self):
        server = DiagnosticsServer.__new__(DiagnosticsServer)
        server._slots = threading.BoundedSemaphore(8)
        with patch.object(ThreadingHTTPServer, 'process_request') as dispatch, patch.object(server, 'shutdown_request') as reject:
            for index in range(9): server.process_request(Mock(), ('127.0.0.1', index))
            self.assertEqual(dispatch.call_count, 8)
            self.assertEqual(reject.call_count, 1)
        with patch.object(ThreadingHTTPServer, 'process_request_thread'):
            server.process_request_thread(Mock(), ('127.0.0.1', 1))
        self.assertTrue(server._slots.acquire(blocking=False))
        self.assertFalse(server._slots.acquire(blocking=False))

    def test_http_connections_have_timeout(self):
        connection = Mock()
        with patch.object(ThreadingHTTPServer, 'get_request', return_value=(connection, ('127.0.0.1', 1))):
            DiagnosticsServer.__new__(DiagnosticsServer).get_request()
        connection.settimeout.assert_called_once_with(5)

    def test_mac_temperature_command_timeout(self):
        spec = importlib.util.spec_from_file_location('mac_broadcaster', ROOT/'remote-service/Mac/temp_broadcaster_mac.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        item = module.TemperatureBroadcaster.__new__(module.TemperatureBroadcaster)
        with patch.object(module.Path, 'exists', return_value=True), patch.object(module.subprocess, 'run', side_effect=subprocess.TimeoutExpired('powermetrics', 15)) as run:
            self.assertIsNone(item.get_cpu_temperature())
            self.assertEqual(run.call_args.kwargs['timeout'], 15)

    def test_pi_wrappers_resolve_source_from_any_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            python = folder/'python3'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            python.chmod(0o755)
            env = {**os.environ, 'PATH': str(folder) + os.pathsep + os.environ['PATH']}
            for name, args in [('install.sh', []), ('update.sh', ['--update'])]:
                result = subprocess.run(['bash', str(ROOT/'remote-service/Pi'/name)], cwd=folder, env=env, capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.splitlines(), [str(ROOT/'remote-service/Pi/install-full.sh'), *args])
