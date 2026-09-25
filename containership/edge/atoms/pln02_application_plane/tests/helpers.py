"""Shared fixtures for v4.3 tests (stdlib only)."""
from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pln02_application_plane.trust import KeyRing, TrustKey, issue_token  # noqa: E402
from pln02_application_plane.catalogue import sign_catalogue  # noqa: E402

KEY = b"k" * 32
OTHER = b"o" * 32


def ring() -> KeyRing:
    r = KeyRing()
    for kid, purpose in (("cat-1", "catalogue"), ("tok-1", "token"), ("aud-1", "audit"), ("art-1", "artifact")):
        r.add(TrustKey(kid, "hmac-sha256", purpose, KEY + kid.encode()))
    return r


def provider(pid, region="eu", residency=("eu",), tier="hardened", consistency="strong", slo=50, lat=3, cost=2, healthy=True):
    return {"id": pid, "region": region, "residency": list(residency), "tier": tier, "consistency": consistency,
            "slo_ms": slo, "latency_ms": lat, "cost": cost, "healthy": healthy}


def catalogue_doc(r: KeyRing, generation=1, providers=None, env="prod", site="eu-1", ttl=3600, now=None):
    now = time.time() if now is None else now
    providers = providers if providers is not None else {
        "state": [provider("redis-a", cost=3), provider("redis-b", cost=1)],
        "tracing": [provider("otel-us", region="us", residency=("us",))],
    }
    return sign_catalogue(r, "cat-1", {"environment": env, "site": site, "generation": generation,
                                       "issued_at": now, "expires_at": now + ttl, "providers": providers})


def token(r: KeyRing, tenant="acme", roles=("app-deployer",), sub="alice"):
    return issue_token(r, "tok-1", subject=sub, tenant=tenant, audience="pln-02", roles=list(roles))


APP = {
    "schema": "PK_APPLICATION/1",
    "components": [
        {"name": "api", "requires": {"state": True, "tracing": False}, "imports": {"store": "1.2"}, "exports": {}},
        {"name": "store", "requires": {"state": True}, "exports": {"store": "1.2"}, "imports": {}},
    ],
    "edges": [["store", "api", "store"]],
}

CONFIG = {
    "provenance": {"author": "test", "source": "tests/helpers.py", "version": "t1"},
    "entitlements": {"acme": ["state", "tracing"]},
    "constraints": {"platform": {"min_tier": "standard"}, "tenants": {"acme": {"residency": ["eu", "us"]}}},
}
