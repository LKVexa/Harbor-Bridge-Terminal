"""Test support: ``covers`` tags each test with the checklist IDs it evidences, and
``stack()`` builds a full hermetic control plane (deterministic clock, temp dirs)."""
from __future__ import annotations

import os
import secrets
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap11_control.common import ManualClock, Telemetry  # noqa: E402
from gap11_control.controller import Controller  # noqa: E402
from gap11_control.election import LeaderElector  # noqa: E402
from gap11_control.hardware import ScrubExecutor, SimScrubBackend  # noqa: E402
from gap11_control.observability import AuditLedger, Metrics  # noqa: E402
from gap11_control.scheduler import QuotaBook  # noqa: E402
from gap11_control.security import Authenticator, Keyring, Policy, SCOPES  # noqa: E402
from gap11_control.service import Service  # noqa: E402
from gap11_control.store import LeaseStore  # noqa: E402


def covers(*ids: str):
    def deco(fn):
        fn.covers = tuple(ids)
        return fn
    return deco


GPU0 = {"device": "gpu0", "generation": "gen9", "memory_gb": 24, "kind": "gpu", "features": ["fp8"],
        "partitions": [{"name": "half", "memory_gb": 12, "features": None}, {"name": "quarter", "memory_gb": 6, "features": None}],
        "topology": {"fabric": "nvl-a", "numa": 0}}
GPU1 = {"device": "gpu1", "generation": "gen9", "memory_gb": 80, "kind": "gpu", "features": ["fp8", "nvlink"],
        "partitions": [], "topology": {"fabric": "nvl-a", "numa": 0}}
GPU2 = {"device": "gpu2", "generation": "gen9", "memory_gb": 80, "kind": "gpu", "features": ["fp8", "nvlink"],
        "partitions": [], "topology": {"fabric": "nvl-b", "numa": 1}}


class Stack:
    def __init__(self, *, devices=(GPU0, GPU1, GPU2), store_dir: str | None = None, clock: ManualClock | None = None,
                 controller_id: str = "ctl-a", scrub_backend: SimScrubBackend | None = None, fault=None) -> None:
        self.clock = clock or ManualClock()
        self.dir = store_dir or tempfile.mkdtemp(prefix="gap11-")
        self.tel = Telemetry(self.clock)
        self.store = LeaseStore(os.path.join(self.dir, "store"), clock=self.clock, fault=fault, fsync=True)
        self.keyring = Keyring()
        self.keyring.add("k1", secrets.token_bytes(32))
        self.audit = AuditLedger(os.path.join(self.dir, "audit.jsonl"), self.keyring, clock=self.clock)
        self.elector = LeaderElector(self.store, controller_id, telemetry=self.tel)
        self.elector.try_acquire()   # not an assert: -O would strip it (v4.2.0 audit scar)
        self.backend = scrub_backend or SimScrubBackend(clock=self.clock)
        self.ctl = Controller(self.store, self.elector, telemetry=self.tel, audit=self.audit.append,
                              scrub_executor=ScrubExecutor(self.backend, clock=self.clock, deadline_s=5.0))
        self.n = 0
        if self.elector.is_leader():
            for d in devices:
                if self.store.get(f"dev/{d['device']}") is None:
                    self.ctl.upsert_device(dict(d), request_id=self.rid(), actor="inventory")
        self.metrics = Metrics()

    def rid(self) -> str:
        self.n += 1
        return f"req-{self.n:06d}-{secrets.token_hex(3)}"

    def service(self, *, rules=None, caps=None, max_inflight: int = 8) -> tuple[Service, Authenticator]:
        authn = Authenticator(self.keyring, clock=self.clock, telemetry=self.tel)
        rules = rules if rules is not None else [
            {"id": "R-alloc", "action": "lease:allocate", "kind": "workload"},
            {"id": "R-release", "action": "lease:release", "kind": "workload"},
            {"id": "R-inv", "action": "inventory:read"},
            {"id": "R-inv-s", "action": "inventory:read_sensitive", "kind": "operator"},
            {"id": "R-scrub", "action": "device:scrub", "kind": "operator"},
        ]
        caps = caps if caps is not None else {"t1": {"devices": 4, "memory_gb": 512}, "t2": {"devices": 4, "memory_gb": 512}}
        svc = Service(self.ctl, authn, Policy(rules, self.tel), QuotaBook(caps), max_inflight=max_inflight,
                      metrics=self.metrics, telemetry=self.tel)
        return svc, authn


def workload_token(authn: Authenticator, tenant: str = "t1", scopes=("lease:allocate", "lease:release", "inventory:read")) -> dict[str, Any]:
    return authn.issue(f"spiffe://gap11/{tenant}/w", tenant, "workload", set(scopes))


def operator_token(authn: Authenticator) -> dict[str, Any]:
    return authn.issue("spiffe://gap11/ops/alice", "ops", "operator", set(SCOPES))
