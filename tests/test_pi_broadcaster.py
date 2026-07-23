import hashlib
import hmac
import importlib.util
import json
import threading
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'remote-service' / 'Pi' / 'temp_broadcaster.py'
spec = importlib.util.spec_from_file_location('temp_broadcaster', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PiBroadcasterParsingTests(unittest.TestCase):
    def setUp(self):
        self.broadcaster = module.TemperatureBroadcaster.__new__(module.TemperatureBroadcaster)
        self.broadcaster.hostname = 'pi-test'
        self.broadcaster.pi_model = '5'
        self.broadcaster.pi_ram = '8GB'
        self.broadcaster.shared_secret = ''
        self.broadcaster.latest_snapshot = None
        self.broadcaster.snapshot_lock = threading.Lock()


    def test_parse_http_port_handles_invalid_values(self):
        self.assertEqual(module.parse_http_port(None), 9876)
        self.assertEqual(module.parse_http_port('9877'), 9877)
        self.assertEqual(module.parse_http_port(''), 0)
        self.assertEqual(module.parse_http_port('not-a-port'), 0)
        self.assertEqual(module.parse_http_port('70000'), 0)

    def test_parse_pi_model(self):
        self.assertEqual(self.broadcaster._parse_pi_model('Raspberry Pi 5 Model B'), '5')
        self.assertEqual(self.broadcaster._parse_pi_model('Raspberry Pi Zero 2 W'), '0W2')
        self.assertEqual(self.broadcaster._parse_pi_model('Raspberry Pi Compute Module 5'), 'CM5')

    def test_map_ram_to_marketing(self):
        self.assertEqual(self.broadcaster._map_ram_to_marketing(950), '1GB')
        self.assertEqual(self.broadcaster._map_ram_to_marketing(7900), '8GB')

    def test_create_message_includes_hmac_when_configured(self):
        self.broadcaster.shared_secret = 'secret'
        message = self.broadcaster.create_message(42.5)
        data = json.loads(message)
        signature = data.pop('hmac')
        expected = hmac.new(
            b'secret',
            json.dumps(data, separators=(',', ':')).encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(signature, expected)
        self.assertNotIn('auth_token', data)
        self.assertEqual(data['temperature']['celsius'], 42.5)

    def test_http_snapshot_reports_latest_temperature(self):
        self.broadcaster.update_latest_snapshot(42.5)

        snapshot = self.broadcaster.create_http_snapshot(self.broadcaster.latest_snapshot)

        self.assertEqual(snapshot['type'], 'temperature_snapshot')
        self.assertEqual(snapshot['count'], 1)
        self.assertEqual(snapshot['devices'][0]['hostname'], 'pi-test')
        self.assertEqual(snapshot['devices'][0]['celsius'], 42.5)
        self.assertEqual(snapshot['devices'][0]['fahrenheit'], 108.5)

    def test_http_snapshot_is_empty_before_first_reading(self):
        snapshot = self.broadcaster.create_http_snapshot(None)

        self.assertEqual(snapshot['count'], 0)
        self.assertEqual(snapshot['devices'], [])
        self.assertIsNone(snapshot['updatedAt'])


if __name__ == '__main__':
    unittest.main()
