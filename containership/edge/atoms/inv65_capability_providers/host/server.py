"""Long-lived provider host process (M04).

    python -m inv65_capability_providers.host.server --config host.json

Start-up order: verify implementation digest against the pinned catalog (M20)
-> open + recover durable store (M05) -> acquire lease (M17) -> restore links
-> bind transport (TLS/mTLS required unless insecure loopback test mode, M19)
-> ready.  SIGTERM drains then stops.
"""
from __future__ import annotations

import argparse
import json
import signal
import threading
from http.server import ThreadingHTTPServer

from ..crypto.transport import assert_bind_allowed, server_context
from ..transport.http_adapter import make_handler


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


class ProviderHost:
    def __init__(self, service, *, host="127.0.0.1", port=0, tls=None, insecure_loopback_for_tests=False):
        assert_bind_allowed(host, tls is not None, insecure_loopback_for_tests)
        self.service = service
        self.httpd = BoundedThreadingHTTPServer((host, port), make_handler(service))
        if tls is not None:
            self.httpd.socket = server_context(**tls).wrap_socket(self.httpd.socket, server_side=True)
        self._t = None

    @property
    def address(self):
        return self.httpd.server_address

    def start(self):
        if self.service.lifecycle.state == "starting":
            self.service.start()
        self._t = threading.Thread(target=self.httpd.serve_forever, name="inv65-host", daemon=True)
        self._t.start()
        return self.address

    def stop(self, drain=True):
        if drain and self.service.lifecycle.state in ("ready", "degraded"):
            self.service.drain("host stop")
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.service.lifecycle.state in ("draining", "ready", "degraded", "disabled"):
            self.service.lifecycle.to("stopped", "host stopped")
        self.service.dispatcher.close()


def main(argv=None) -> int:  # pragma: no cover - operator entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    from .bootstrap import build_service
    svc = build_service(cfg)
    h = ProviderHost(svc, host=cfg.get("bind", "127.0.0.1"), port=cfg.get("port", 8465), tls=cfg.get("tls"))
    h.start()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    h.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
