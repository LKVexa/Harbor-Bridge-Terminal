"""Deterministic production bootstrap (checklist #32).

``python -m inv55_secrets_integration.bootstrap --config-dir config --env prod [--site edge-1] --check``

Order is fixed and every step fails closed:
 1. load layers (base -> env -> site) and validate against config.schema.json
 2. resolve credential *references* (file:/env:) -- values never appear in config
 3. verify/resume the audit chain (divergence -> QUARANTINED, never a fresh chain)
 4. construct provider (TLS enforced), authenticator, policy, service
 5. ``service.start()`` -> READY / DEGRADED / QUARANTINED
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

from .audit import AuditChain, FileAuditSink, resume_from_file
from .config import ConfigController, load_layers
from .identity import HmacJwtAuthenticator, PolicyEngine
from .providers.base import InMemoryProvider
from .providers.vault import AppRoleAuth, KubernetesAuth, TokenAuth, VaultProvider, build_tls_context
from .secretvalue import SecretValue
from .service import SecretsService, ServiceLimits, State


def read_ref(ref: str) -> bytes:
    """Resolve ``file:/path`` or ``env:NAME`` references.  Anything else is refused."""
    if ref.startswith("file:"):
        return pathlib.Path(ref[5:]).read_bytes().strip()
    if ref.startswith("env:"):
        val = os.environ.get(ref[4:])
        if val is None:
            raise KeyError(f"environment reference {ref[4:]} not set")
        return val.encode()
    raise ValueError("credential references must be file: or env:")


def build_service(config_dir: str, environment: str, site: str | None = None, *,
                  jwt_key_ref: str = "env:INV55_JWT_KEY", clock=time.monotonic) -> SecretsService:
    ctl = ConfigController()
    active = ctl.activate(load_layers(pathlib.Path(config_dir), environment, site))
    cfg = active.data
    pc = cfg["provider"]
    if pc["kind"] == "memory":
        if cfg["environment"] == "prod":
            raise ValueError("memory provider is forbidden in prod")
        provider = InMemoryProvider()
    else:
        auth_kind = pc.get("auth", "kubernetes")
        if auth_kind == "token":
            if cfg["environment"] == "prod":
                raise ValueError("static token auth is forbidden in prod")
            auth = TokenAuth(SecretValue(read_ref(pc["auth_ref"])))
        elif auth_kind == "approle":
            role_id, secret_id = read_ref(pc["auth_ref"]).decode().split(":", 1)
            auth = AppRoleAuth(role_id, SecretValue(secret_id))
        else:
            auth = KubernetesAuth(role="inv55", jwt_path=pc.get("auth_ref", KubernetesAuth.jwt_path))
        ctx = build_tls_context(pc.get("ca_file")) if pc["address"].startswith("https") else None
        provider = VaultProvider(pc["address"], auth, mount=pc.get("mount", "secret"),
                                 kv_version=pc.get("kv_version", 2), namespace=pc.get("namespace"),
                                 timeout_s=pc.get("timeout_s", 2.0), ssl_context=ctx,
                                 allow_insecure_http=cfg["environment"] in ("dev", "test"), clock=clock)
    ac = cfg["audit"]
    hkey = read_ref(ac["hmac_key_ref"]) if ac.get("hmac_key_ref") else None
    sink = FileAuditSink(ac["path"], fsync=ac.get("fsync", True))
    quarantine_reason = None
    try:
        chain = resume_from_file(ac["path"], sink, hkey)
    except ValueError as exc:
        chain, quarantine_reason = AuditChain(sink, hkey), str(exc)
    lim = cfg.get("limits", {})
    limits = ServiceLimits(**{k: v for k, v in lim.items() if k in ServiceLimits.__dataclass_fields__})
    authn = HmacJwtAuthenticator(read_ref(jwt_key_ref), issuer="inv55-idp", audience="inv55", clock=time.time)
    svc = SecretsService(provider=provider, authenticator=authn, policy=PolicyEngine(), audit=chain,
                         clock=clock, limits=limits, config=ctl,
                         state_path=str(pathlib.Path(ac["path"]).with_suffix(".state.json")))
    if quarantine_reason:
        svc.transition(State.QUARANTINED, "audit_chain_divergence")
    return svc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv55-bootstrap")
    ap.add_argument("--config-dir", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--site")
    ap.add_argument("--check", action="store_true", help="validate config only; do not start")
    a = ap.parse_args(argv)
    if a.check:
        ctl = ConfigController()
        act = ctl.activate(load_layers(pathlib.Path(a.config_dir), a.env, a.site))
        print(json.dumps(ctl.provenance(), indent=1))
        return 0 if act else 1
    svc = build_service(a.config_dir, a.env, a.site)
    state = svc.start() if svc.state is State.STARTING else svc.state
    print(json.dumps(svc.health(), indent=1, default=str))
    return 0 if state in (State.READY, State.DEGRADED) else 2


if __name__ == "__main__":
    sys.exit(main())
