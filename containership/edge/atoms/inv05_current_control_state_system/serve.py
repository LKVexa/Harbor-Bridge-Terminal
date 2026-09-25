"""Production entry point: bootstrap, then serve with mTLS until SIGTERM (MC-029, MC-050-05).

    python -m inv05_current_control_state_system.serve --config base.json [--env ..] [--site ..] --secret-dir DIR
"""
from __future__ import annotations

import argparse
import json
import signal
import threading

from .bootstrap import build_service
from .config import load_layers
from .security import (MTLSAuthenticator, SecretProvider, TokenAuthenticator, check_tls_context, derive_key,
                       server_tls_context)
from .server import ControlStateHTTPServer

DEFAULT_ROLE_MAP = {"client": ["writer"], "admin": ["operator"]}


def build_server(cfg, secrets: SecretProvider, svc) -> ControlStateHTTPServer:
    role_map = DEFAULT_ROLE_MAP
    if cfg["auth.role_map_file"]:
        with open(cfg["auth.role_map_file"], encoding="utf-8") as fh:
            role_map = json.load(fh)
    ctx = None
    if cfg["tls.enabled"]:
        key_path = secrets.get(cfg["tls.key_file"]).decode()
        ctx = server_tls_context(cfg["tls.cert_file"], key_path, cfg["tls.ca_file"])
        problems = check_tls_context(ctx, server=True)
        if problems:
            raise SystemExit("TLS policy violation: " + "; ".join(problems))
    tokens = None
    if cfg["auth.allow_tokens"]:
        tokens = TokenAuthenticator({"t1": derive_key(secrets.get(cfg["auth.token_key"]), "token")}, "t1")
    return ControlStateHTTPServer((cfg["listen.host"], cfg["listen.port"]), svc,
                                  mtls=MTLSAuthenticator(cfg["auth.trust_domain"], role_map=role_map),
                                  tokens=tokens, ssl_context=ctx, idle_timeout_s=cfg["watch.idle_timeout_s"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--env")
    ap.add_argument("--site")
    ap.add_argument("--secret-dir")
    a = ap.parse_args(argv)
    layers = {"base": a.config}
    if a.env:
        layers["environment"] = a.env
    if a.site:
        layers["site"] = a.site
    cfg = load_layers(layers)
    secrets = SecretProvider(a.secret_dir)
    svc, _ = build_service(cfg, secrets)
    srv = build_server(cfg, secrets, svc)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    svc.start(checkpoint_every=cfg["storage.checkpoint_every_records"])
    srv.serve_background()
    svc.log.log("INFO", "CS1001", "service ready", port=srv.server_address[1])
    stop.wait()
    srv.graceful_shutdown(10.0)
    svc.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
