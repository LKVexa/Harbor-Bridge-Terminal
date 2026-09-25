"""Shared fixtures for the 4.3.0 test suites."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv55_secrets_integration.audit import AuditChain, MemoryAuditSink  # noqa: E402
from inv55_secrets_integration.config import ConfigController, load_layers  # noqa: E402
from inv55_secrets_integration.identity import HmacJwtAuthenticator, PolicyEngine, Rule  # noqa: E402
from inv55_secrets_integration.providers.base import InMemoryProvider  # noqa: E402
from inv55_secrets_integration.service import SecretsService, ServiceLimits  # noqa: E402

SECRET = "s3cr3t-VALUE-do-not-leak-7f1c"


class Clock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


class Env:
    """A fully wired service with an in-memory provider, JWT authn and a permissive tenant policy."""

    def __init__(self, provider=None, limits: ServiceLimits | None = None, state_path: str | None = None,
                 **svc_kwargs) -> None:
        self.clock = Clock()
        self.provider = provider or InMemoryProvider()
        self.sink = MemoryAuditSink()
        self.audit = AuditChain(self.sink, hmac_key=b"audit-key")
        self.authn = HmacJwtAuthenticator(b"k" * 32, "inv55-idp", "inv55", self.clock)
        self.policy = PolicyEngine()
        self.policy.replace([
            Rule("acme", "*", "*", frozenset({"resolve", "use", "rotate", "scope", "retire", "revoke"})),
            Rule("globex", "*", "*", frozenset({"resolve", "use", "rotate", "scope", "retire", "revoke"})),
        ])
        cfg = ConfigController()
        cfg.activate(load_layers(ROOT / "config", "dev"))
        self.svc = SecretsService(provider=self.provider, authenticator=self.authn, policy=self.policy,
                                  audit=self.audit, clock=self.clock, limits=limits, config=cfg,
                                  state_path=state_path, **svc_kwargs)
        self.svc.start()

    def cred(self, sub: str = "orders", tenant: str = "acme", roles=("consumer", "rotator", "secret-admin")) -> str:
        return self.authn.issue(sub, tenant, roles, ttl_s=3600)

    def seed(self, name: str = "db-password", value: str = SECRET, apps=("orders",), tenant: str = "acme",
             idem: str = "idem-seed-0001") -> dict:
        admin = self.cred("admin", tenant)
        r = self.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": admin, "name": name,
                             "value": value, "idempotency_key": idem})
        assert r["ok"], r
        s = self.svc.set_scope({"protocol": "PK_SECRET_SCOPE/1", "credential": admin, "name": name,
                                "apps": list(apps)})
        assert s["ok"], s
        return r

    def resolve(self, sub="orders", name="db-password", tenant="acme", **kw) -> dict:
        return self.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": self.cred(sub, tenant),
                                 "name": name, **kw})

    def use(self, lease_id, sub="orders", name="db-password", tenant="acme") -> dict:
        return self.svc.use({"protocol": "PK_SECRET_RESOLVE/1", "credential": self.cred(sub, tenant),
                             "name": name, "lease_id": lease_id})

    def all_diagnostics(self) -> str:
        parts = [b.decode() for b in self.sink.lines]
        parts.append(self.svc.metrics.exposition())
        parts.extend(repr(s.__dict__) for s in self.svc.tracer.finished)
        parts.extend(repr(r) for r in self.svc.ledger._d)
        parts.append(repr(self.svc.health()))
        return "\n".join(parts)
