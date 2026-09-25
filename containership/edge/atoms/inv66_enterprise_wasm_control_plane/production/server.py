"""Service entry point: ``python -m inv66_enterprise_wasm_control_plane.production.server``.

Reads a trust config (issuers/JWKS, audience, TLS files, dependency endpoints) and starts the HTTPS API.
The journal root must already be bootstrapped (RB-DAY0).
"""
from __future__ import annotations

import argparse
import json
import signal
import ssl
import sys
import threading
from pathlib import Path

from .adapters import HttpDeploymentManager
from .identity import Authenticator, StaticJwks
from .http_api import Server
from .policy_engine import ExternalPolicy, HttpPolicyClient
from .service import ControlPlaneService
from .telemetry import Logger


def build(cfg: dict, root: Path) -> tuple[ControlPlaneService, Server]:
    auth = Authenticator(StaticJwks(cfg["jwks"]), audience=cfg["audience"], trust_domain=cfg.get("trust_domain"),
                         spiffe_org=cfg["org"], single_use=bool(cfg.get("single_use_tokens", False)))
    dep = HttpDeploymentManager(cfg["deployment_endpoint"]) if cfg.get("deployment_endpoint") else None
    ext = None
    if cfg.get("policy_endpoint"):
        ext = ExternalPolicy(HttpPolicyClient(cfg["policy_endpoint"]), expected_version=cfg.get("policy_version"),
                             on_unavailable=cfg.get("policy_on_unavailable", "deny"))
    svc = ControlPlaneService(root, authenticator=auth, deployer=dep, external_policy=ext, logger=Logger(sys.stderr))
    tls = None
    if cfg.get("tls"):
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(cfg["tls"]["cert"], cfg["tls"]["key"])
        if cfg["tls"].get("client_ca"):
            tls.load_verify_locations(cfg["tls"]["client_ca"])
            tls.verify_mode = ssl.CERT_OPTIONAL  # tokens OR client certs; workloads present certs
    srv = Server(svc, host=cfg.get("host", "0.0.0.0"), port=int(cfg.get("port", 8443)), tls=tls)  # noqa: S104
    return svc, srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    svc, srv = build(json.loads(Path(a.config).read_text()), Path(a.root))
    if svc.config.active is None:
        print("journal not bootstrapped: run RB-DAY0", file=sys.stderr)
        return 2
    srv.start()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    srv.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
