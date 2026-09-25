"""Shared test fixtures and adjacent-layer fakes (PLN-07, GAP-13, PLN-02, SCH-01, GAP-09)."""
from __future__ import annotations

import importlib
import os
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
pkg = importlib.import_module(PKG_DIR.name)

from pln01_intent_plane import config, controls, errors, precedence, secret_guard, service, store, telemetry, trust, validation  # noqa: E402,F401


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def decl(node, spec=None, after=(), rid=None, **extra):
    doc = {"schema": "PK_DECLARATION/1", "operation": "declare", "node": list(node),
           "spec": spec or {}, "after": [list(a) for a in after], "request_id": rid or os.urandom(6).hex()}
    doc.update(extra)
    return doc


class SecurityPlaneFake:
    """PLN-07: identity issuer backed by the HMAC authenticator."""

    def __init__(self, clock=None):
        self.keys = trust.KeyProvider(b"k" * 32)
        self.auth = trust.HmacTokenAuthenticator(self.keys, **({"clock": clock} if clock else {}))

    def token(self, subject="op@example", kind="human", grants=(("intent:admin", "*"),), **kw):
        return self.auth.issue(subject, kind, list(grants), **kw)


class PolicyEngineFake:
    """GAP-13: denies specs carrying ``forbidden: true``."""

    def __init__(self):
        self.calls = 0

    def evaluate(self, request):
        self.calls += 1
        if request["spec"].get("forbidden"):
            return False, "policy: forbidden flag set"
        return True, "policy: allow"


class ApplicationPlaneFake:
    """PLN-02: consumes a released plan; validates schema and refuses stale plans."""

    def __init__(self, svc):
        self.svc = svc
        self.executed = []

    def consume(self, plan_doc):
        validation.validate({k: v for k, v in plan_doc.items()
                             if k in ("schema", "graph_version", "dry_run", "rollback_target", "steps", "drift", "plan_id")},
                            "PK_RECONCILIATION_PLAN/1")
        self.svc.verify_release(plan_doc["plan_id"])
        for step in plan_doc["steps"]:
            if "held" not in step:
                self.executed.append(tuple(step["node"]))
        return len(self.executed)


class PlacementFake:
    """SCH-01: reads placement intent (site attribute) from the graph projection."""

    def placements(self, graph_doc):
        return {tuple(n["node"]): n["spec"].get("site") for n in graph_doc["nodes"]}


def make_service(tmp=None, clock=None, mono=None, **kw):
    clock = clock or FakeClock()
    mono = mono or FakeClock(10.0)
    sec = SecurityPlaneFake(clock=clock)
    pol = PolicyEngineFake()
    adapter = trust.StaticPolicyAdapter(pol.evaluate)
    st = store.DurableStore(tmp, sec.keys, fsync=False, snapshot_every=1000) if tmp else None
    cfg = kw.pop("config", None) or config.build_config(
        [("test", {"sites": {"edge-1": {"context": "far-edge", "staleness_seconds": 100.0},
                             "dc-1": {"context": "datacenter"}},
                   "quotas": {"tenant_rate_per_second": 1000.0, "tenant_burst": 1000}})], author="tests")
    svc = service.IntentPlaneService(config=cfg, authenticator=sec.auth, admission_policy=adapter, store=st,
                                     clock=clock, monotonic=mono, log_sink=lambda line: None, **kw)
    return svc, sec, pol, adapter, clock
