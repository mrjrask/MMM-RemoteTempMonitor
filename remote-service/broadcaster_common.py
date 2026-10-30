"""Shared signing and bounded HTTP diagnostics for standalone broadcasters."""
import hashlib
import hmac
import json
import math
import threading
from http.server import ThreadingHTTPServer


def _normalize(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite value in broadcast")
        return int(value) if value.is_integer() else value
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def sign_message(message, secret):
    # Match JSON.stringify for one-decimal readings and integer timestamps.
    payload = json.dumps(_normalize(message), separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


class DiagnosticsServer(ThreadingHTTPServer):
    """Limit slow HTTP clients to eight workers and five-second socket timeouts."""
    daemon_threads = True
    block_on_close = False
    request_queue_size = 8

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()
