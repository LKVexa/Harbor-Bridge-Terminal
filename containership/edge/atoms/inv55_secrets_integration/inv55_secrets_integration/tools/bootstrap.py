"""Deterministic, idempotent bootstrap / readiness gate (checklist #32).

    python -m inv55_secrets_integration.tools.bootstrap CONFIG.json [OVERLAY.json ...] --author NAME --source REF

Steps (each prints PASS/FAIL, first FAIL stops, exit code = number of the failed step):
 1 merge + validate configuration (schema, credential scan, environment rules)
 2 construct provider (transport policy enforced; https only outside test)
 3 provider health (initialised, unsealed)
 4 audit sink writable and existing chain verifies
 5 readiness probe of an assembled service
Re-running on an already-bootstrapped environment performs the same checks and
changes nothing (no writes other than the audit chain's own append on step 4).
The trust roots (Vault token file / AppRole ids, IdP keys) are read from files
named by environment variables, never from the config document.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from inv55_secrets_integration.runtime import config as C  # noqa: E402
from inv55_secrets_integration.runtime.audit import AuditLog  # noqa: E402
from inv55_secrets_integration.runtime.errors import INV55Error  # noqa: E402


def build_provider(doc):
    p = doc["provider"]
    if p["kind"] == "memory":
        from inv55_secrets_integration.runtime.provider import InMemoryProvider
        return InMemoryProvider()
    from inv55_secrets_integration.runtime.vault import AppRoleAuth, StaticTokenAuth, VaultKV2Provider
    if p.get("auth") == "approle":
        auth = AppRoleAuth(pathlib.Path(os.environ["INV55_VAULT_ROLE_ID_FILE"]).read_text().strip(),
                           pathlib.Path(os.environ["INV55_VAULT_SECRET_ID_FILE"]).read_text().strip())
    else:
        auth = StaticTokenAuth(pathlib.Path(os.environ["INV55_VAULT_TOKEN_FILE"]).read_text().strip())
    return VaultKV2Provider(p["address"], mount=p.get("mount", "secret"), auth=auth, namespace=p.get("namespace"),
                            ca_file=p.get("ca_file"), allow_insecure_loopback=p.get("allow_insecure_loopback", False))


def run(files, author, source, out=print):
    steps = []
    def step(n, name, fn):
        try:
            detail = fn()
            steps.append({"step": n, "name": name, "result": "PASS", "detail": detail})
            out(f"[{n}] PASS {name} {detail or ''}")
            return True
        except (INV55Error, OSError, KeyError, ValueError, RuntimeError) as e:
            steps.append({"step": n, "name": name, "result": "FAIL", "detail": f"{type(e).__name__}: {e}"})
            out(f"[{n}] FAIL {name}: {type(e).__name__}: {e}")
            return False
    docs = [json.loads(pathlib.Path(f).read_text()) for f in files]
    cc = C.ConfigController()
    state = {}
    if not step(1, "config", lambda: cc.stage(docs[0], *docs[1:], author=author, source=source)["digest"]):
        return 1, steps
    doc = cc.staged[0]
    if not step(2, "provider", lambda: state.setdefault("prov", build_provider(doc)).name):
        return 2, steps
    def health():
        h = state["prov"].health(timeout_s=5)
        if not h.healthy:
            raise RuntimeError(f"provider not healthy: {h.detail}")
        return h.detail
    if not step(3, "provider-health", health):
        return 3, steps
    def audit():
        pth = doc["telemetry"].get("audit_path")
        if not pth:
            if doc["environment"] == "production":
                raise RuntimeError("production requires telemetry.audit_path")
            return "memory-only (non-production)"
        a = AuditLog(pth)
        a.append(op="bootstrap", actor=author, detail=source, config_digest=C.digest(doc), allowed=True, reason="bootstrap")
        return f"head={a.head[:12]} records={a.seq}"
    if not step(4, "audit-sink", audit):
        return 4, steps
    def ready():
        from inv55_secrets_integration.runtime.health import status
        from inv55_secrets_integration.runtime.identity import HmacTokenVerifier
        from inv55_secrets_integration.runtime.service import SecretsService
        svc = SecretsService(doc, state["prov"], HmacTokenVerifier({"bootstrap": os.urandom(16).hex()},
                             issuer=doc["identity"]["issuer"], audience=doc["identity"]["audience"]))
        st = status(svc)
        if not st["ready"]:
            raise RuntimeError(f"not ready: {st['checks']}")
        return "ready"
    if not step(5, "readiness", ready):
        return 5, steps
    return 0, steps


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--author", required=True)
    ap.add_argument("--source", required=True)
    a = ap.parse_args(argv)
    code, _ = run(a.files, a.author, a.source)
    return code


if __name__ == "__main__":
    sys.exit(main())
