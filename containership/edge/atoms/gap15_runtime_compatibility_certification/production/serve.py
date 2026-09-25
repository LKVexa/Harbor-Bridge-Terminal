"""Service entry point used by deploy/Dockerfile and deploy/gap15.service.

Production start requires a real KMS/HSM key provider, a signed authz policy
and trust bundle. None of those can be supplied by this package, so a
production start **refuses** with ``E_KEY_PROVIDER_UNAVAILABLE`` rather than
falling back to development keys. ``--development`` starts a local instance
with ephemeral development keys for evaluation only.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time

from . import authn, authz, config as cfgmod, policy, signing, timepolicy
from .attestation import AttestationPolicy
from .http_api import ApiServer
from .service import CertificationService, ServiceConfig
from .state import CertPolicy
from .store import Store


def build_development(cfg: dict) -> CertificationService:
    kp = signing.DevelopmentKeyProvider()
    trust = signing.TrustStore()
    trust.add(signing.TrustedKey("dev-idp", "idp", kp.generate("dev-idp"),
                                 scopes=frozenset(f"token:issue:{t}" for t in authn.PRINCIPAL_TYPES)))
    trust.add(signing.TrustedKey("dev-svc", "gap15-service", kp.generate("dev-svc"), scopes=frozenset({"offline:issue"})))
    clock = timepolicy.TrustedClock([timepolicy.TimeSource("system", "rtc", lambda: int(time.time()), timepolicy.MEDIUM, 1)])
    a = authn.Authenticator(trust, audience=cfg["environment"], issuers={"idp": set(authn.PRINCIPAL_TYPES)})
    a.update_revocations(set(), set(), int(time.time()))
    z = authz.Authorizer(authz.PolicyBundle("dev:0", []))  # default deny everything until a policy is loaded
    os.makedirs(cfg.get("data_dir", "./data"), mode=0o700, exist_ok=True)
    store = Store(os.path.join(cfg.get("data_dir", "./data"), "gap15.db"))
    return CertificationService(config=ServiceConfig(cfg["environment"], frozenset(cfg["partitions"]),
                                                     CertPolicy(ttl_s=cfg.get("certification.ttl_s", 500))),
                                store=store, trust=trust, authn=a, authz=z, clock=clock, key_provider=kp,
                                service_key_id="dev-svc", policy=policy.PolicySet("dev:0", []),
                                attestation_policy=AttestationPolicy())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gap15-serve")
    ap.add_argument("--config", required=True)
    ap.add_argument("--development", action="store_true")
    args = ap.parse_args(argv)
    cfg = json.load(open(args.config))
    problems = cfgmod.validate_config(cfg, development=args.development)
    if problems:
        print(json.dumps({"ok": False, "code": "E_CONFIG", "problems": problems}))
        return 3
    if not args.development:
        print(json.dumps({"ok": False, "code": "E_KEY_PROVIDER_UNAVAILABLE",
                          "detail": f"no {cfg.get('signing.key_provider')} provider is bundled; production start refused"}))
        return 3
    svc = build_development(cfg)
    host, port = cfg.get("api.listen", "127.0.0.1:8443").rsplit(":", 1)
    srv = ApiServer(svc, host, int(port)).start()
    print(json.dumps({"ok": True, "mode": "development", "listening": srv.address}))
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    try:
        while not stop:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    print(json.dumps(srv.shutdown(10.0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
