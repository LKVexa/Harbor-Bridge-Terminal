"""Shared fixtures for runtime tests (no pk_core, no network beyond loopback)."""
from __future__ import annotations

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv55_secrets_integration.runtime.identity import HmacTokenVerifier  # noqa: E402
from inv55_secrets_integration.runtime.provider import InMemoryProvider  # noqa: E402
from inv55_secrets_integration.runtime.service import SecretsService  # noqa: E402

BASE = {
    "schema": "inv55-config/1", "environment": "test",
    "provider": {"kind": "memory"},
    "identity": {"issuer": "https://idp.test", "audience": "inv55", "max_skew_s": 5},
    "lease": {"ttl_s": 60, "max_ttl_s": 300},
    "limits": {"max_inflight": 64, "rate_per_s": 1000, "burst": 1000, "max_request_bytes": 8192},
    "cache": {"fresh_s": 5, "max_stale_s": 60, "allow_stale": False},
    "retry": {"attempts": 3, "base_s": 0.0, "cap_s": 0.0, "deadline_s": 2.0, "breaker_threshold": 3, "breaker_cooldown_s": 10},
    "telemetry": {"max_series": 500},
}
PLAINTEXT = "PLAINTEXT-canary-7f3e9b"


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def cfg(**over):
    c = copy.deepcopy(BASE)
    for k, v in over.items():
        c[k].update(v) if isinstance(v, dict) else c.__setitem__(k, v)
    return c


def make(config=None, provider=None, **kw):
    clock = Clock()
    wall = Clock(1_900_000_000.0)
    ver = HmacTokenVerifier({"k1": "test-hmac-key-0123456789abcdef"}, issuer="https://idp.test", audience="inv55")
    prov = provider or InMemoryProvider()
    svc = SecretsService(config or cfg(), prov, ver, clock=clock, wall=wall, sleep=lambda s: None, **kw)
    return svc, prov, ver, clock, wall


def token(ver, wall, tenant="acme", app="orders", roles=("secret-consumer",), **over):
    claims = {"iss": "https://idp.test", "aud": "inv55", "nbf": wall.t - 10, "exp": wall.t + 600,
              "sub": f"spiffe://example.org/tenant/{tenant}/workload/{app}", "roles": list(roles)}
    claims.update(over)
    return ver.issue(claims, "k1")


def req(name="acme/db-password", op="RESOLVE", **extra):
    r = {"versions": [f"PK_SECRET_{op}/1"], "request_id": "req-00000001", "name": name}
    r.update(extra)
    return json.dumps(r)


def seeded(**kw):
    svc, prov, ver, clock, wall = make(**kw)
    prov.write("acme/db-password", PLAINTEXT, cas=None, timeout_s=1)
    svc.policy.set_scope("acme/db-password", [("acme", "orders")])
    return svc, prov, ver, clock, wall
