"""``inv66`` command line (MC-028 bootstrap, MC-064 day-2 operations).

    inv66 validate-config CONFIG.json
    inv66 serve --config CONFIG.json --store DIR --node-id ID --org ORG [--host H --port P]
                [--tls-cert C --tls-key K --tls-client-ca CA] [--policy-url URL --policy-version V]
                [--deploy-url URL] [--anchor-worm PATH]
    inv66 verify --store DIR               # chain + anchors (offline, read-only)
    inv66 backup --store DIR --dest DIR
    inv66 restore --backup DIR --store DIR

Secrets are never passed on the command line: the anchor MAC key and identity
issuer keys are resolved from the configuration's ``secrets`` references
(``env://`` / ``file://``) via :mod:`secrets_provider`.
"""
from __future__ import annotations

import argparse
import json
import signal
import ssl
import sys
import threading

from . import __version__
from .adapters import FileWormSink, HttpDeploymentManager, HttpPolicyEngine, RulePolicyEngine
from .config import build_policy, load_file
from .errors import ControlPlaneError
from .identity import Authenticator, Issuer
from .secrets_provider import LocalSecretProvider


def _anchor_key(doc):
    ref = doc.get("secrets", {}).get("anchor_key")
    if not ref:
        raise SystemExit("config.secrets.anchor_key reference is required")
    return LocalSecretProvider().resolve(ref).reveal()


def _authenticator(doc):
    sp = LocalSecretProvider()
    issuers = {}
    for name, spec in doc.get("identity", {}).get("issuers", {}).items():
        keys = {}
        for kid, ref in spec["keys"].items():
            raw = sp.resolve(ref).reveal() if ref.startswith(("env://", "file://")) else bytes.fromhex(ref)
            keys[kid] = raw if spec["algorithm"] == "HS256" else bytes.fromhex(raw.decode()) if len(raw) == 64 else raw
        issuers[name] = Issuer(name, frozenset({spec["algorithm"]}), keys)
    if not issuers:
        raise SystemExit("config.identity.issuers must configure at least one trusted issuer")
    return Authenticator(issuers, audience=doc.get("identity", {}).get("audience", "inv66-control-plane"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv66", description=f"INV-66 enterprise Wasm control plane {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate-config"); v.add_argument("config")
    s = sub.add_parser("serve")
    for a in ("--config", "--store", "--node-id", "--org"):
        s.add_argument(a, required=True)
    s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8466)
    for a in ("--tls-cert", "--tls-key", "--tls-client-ca", "--policy-url", "--policy-version", "--deploy-url", "--anchor-worm"):
        s.add_argument(a)
    s.add_argument("--maintenance-interval", type=float, default=1.0)
    ve = sub.add_parser("verify"); ve.add_argument("--store", required=True); ve.add_argument("--config", required=True)
    b = sub.add_parser("backup"); b.add_argument("--store", required=True); b.add_argument("--dest", required=True); b.add_argument("--config", required=True)
    r = sub.add_parser("restore"); r.add_argument("--backup", required=True); r.add_argument("--store", required=True); r.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate-config":
            pol = build_policy(load_file(a.config))
            print(json.dumps({"valid": True, "version": pol.version, "digest": pol.digest}))
            return 0
        doc = load_file(a.config)
        if a.cmd == "verify":
            from .store import JournalStore
            st = JournalStore(a.store, "verifier", anchor_key=_anchor_key(doc))
            ok, d = st.verify_all(); aok, ad = st.verify_anchors()
            print(json.dumps({"chain": d, "chain_ok": ok, "anchors": ad, "anchors_ok": aok}))
            return 0 if ok and aok else 2
        if a.cmd == "backup":
            from .backup import backup
            print(json.dumps(backup(a.store, a.dest, _anchor_key(doc))["head_sequence"]))
            return 0
        if a.cmd == "restore":
            from .backup import restore
            print(json.dumps(restore(a.backup, a.store, _anchor_key(doc))))
            return 0
        # serve
        from .http_api import serve
        from .observability import JsonLogger, Metrics
        from .service import ControlPlaneService
        from .store import JournalStore
        ctx = None
        client_ctx = None
        if a.tls_cert:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(a.tls_cert, a.tls_key)
            if a.tls_client_ca:
                ctx.load_verify_locations(a.tls_client_ca)
                ctx.verify_mode = ssl.CERT_REQUIRED
            client_ctx = ssl.create_default_context(cafile=a.tls_client_ca)
            client_ctx.load_cert_chain(a.tls_cert, a.tls_key)
        policy = (HttpPolicyEngine(a.policy_url, a.policy_version, client_ctx) if a.policy_url
                  else RulePolicyEngine(doc.get("policy", {}).get("rules", []), doc.get("policy", {}).get("version", "embedded")))
        if not a.deploy_url:
            raise SystemExit("--deploy-url (INV-63) is required to serve")
        store = JournalStore(a.store, a.node_id, anchor_key=_anchor_key(doc),
                             anchor_sink=FileWormSink(a.anchor_worm) if a.anchor_worm else None)
        svc = ControlPlaneService(org=a.org, store=store, authenticator=_authenticator(doc), initial_config=doc,
                                  policy_engine=policy, deployer=HttpDeploymentManager(a.deploy_url, client_ctx),
                                  metrics=Metrics(), logger=JsonLogger())
        stop = svc.start_background(a.maintenance_interval)
        httpd = serve(svc, a.host, a.port, ctx)
        done = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: done.set())
        signal.signal(signal.SIGINT, lambda *_: done.set())
        svc.log.log("info", "started", version=__version__, node=a.node_id, port=a.port)
        done.wait()
        httpd.shutdown(); stop.set(); store.release()
        svc.log.log("info", "stopped", node=a.node_id)
        return 0
    except ControlPlaneError as exc:
        print(json.dumps({"error": exc.error.to_dict()}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
