"""Shared test fixtures: fake clocks, issuer, credentials and message builders."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pln05_elasticity_plane.iam import Issuer  # noqa: E402
from pln05_elasticity_plane.keys import KeyRing  # noqa: E402
from pln05_elasticity_plane.plane import ElasticityPlane  # noqa: E402
from pln05_elasticity_plane.state import FencedSink, LeaseService  # noqa: E402

T0 = 1_790_000_000.0


class Clock:
    def __init__(self, t: float = T0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class World:
    """A plane plus everything around it (issuer, lease service, sink, clocks)."""

    def __init__(self, tmp=None, *, instance="ctl-a", ring=None, leases=None, sink=None, clock=None,
                 mono=None, persist=True) -> None:
        self.clock = clock or Clock()
        self.mono = mono or Clock(1000.0)
        self.ring = ring or KeyRing.ephemeral(self.clock(), lifetime=10 * 86400)
        self.issuer = Issuer(self.ring)
        self.leases = leases or LeaseService()
        self.sink = sink or FencedSink()
        self.tmp = pathlib.Path(tmp) if tmp else None
        kw = {}
        if self.tmp and persist:
            kw = {"state_dir": self.tmp / "state", "config_dir": self.tmp / "config",
                  "audit_path": self.tmp / "audit.jsonl"}
        self.plane = ElasticityPlane(instance_id=instance, ring=self.ring, clock=self.clock,
                                     mono=self.mono, lease_service=self.leases, sink=self.sink, **kw)
        self.seq = 0

    # credentials -------------------------------------------------------
    def token(self, actor_class="demand_reporter", *, sub=None, tenant="t1", sites=None, caps=None,
              source="r1", lifetime=300.0, ticket=None, iat=None) -> str:
        if sites is None:
            sites = ("*",) if actor_class in ("platform_operator", "emergency_admin") else ("dub",)
        if actor_class != "demand_reporter" and source == "r1":
            source = None
        return self.issuer.mint(sub=sub or f"{actor_class}-1", actor_class=actor_class, tenant=tenant,
                                sites=sites, caps=caps, source=source, now=self.clock(),
                                lifetime=lifetime, ticket=ticket, iat=iat)

    def admin(self, sub="admin-1", tenant="*"):
        return self.token("emergency_admin", sub=sub, tenant=tenant, sites=("*",), ticket="INC-1")

    # messages ----------------------------------------------------------
    def limits(self, floor=0, ceiling=8, revision=1, *, tenant="t1", site="dub", workload="w1",
               up=0.75, down=0.25, grace=3, issuer="intent_plane-1", **extra) -> bytes:
        body = {"schema": "PK_CAPACITY_LIMITS/1", "revision": revision, "tenant": tenant, "site": site,
                "workload": workload, "floor": floor, "ceiling": ceiling, "scale_up_at": up,
                "scale_down_at": down, "grace_samples": grace, "issuer": issuer,
                "issued_at": self.clock()}
        body.update(extra)
        return json.dumps(body).encode()

    def declare(self, **kw):
        return self.plane.submit_limits(self.limits(**kw), self.token("intent_plane", tenant=kw.get("tenant", "t1")))

    def demand(self, util, *, tenant="t1", site="dub", workload="w1", source="r1", seq=None,
               observed_at=None, message_id=None, **extra) -> bytes:
        self.seq += 1
        body = {"schema": "PK_DEMAND/1", "message_id": message_id or uuid.uuid4().hex, "tenant": tenant,
                "site": site, "workload": workload, "source": source,
                "seq": self.seq if seq is None else seq,
                "observed_at": self.clock() if observed_at is None else observed_at,
                "utilisation": util}
        body.update(extra)
        return json.dumps(body).encode()

    def observe(self, util, *, token=None, **kw):
        return self.plane.submit_demand(self.demand(util, **kw), token or self.token())
