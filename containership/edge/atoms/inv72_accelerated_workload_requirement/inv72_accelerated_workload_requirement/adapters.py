"""Reference adapters for INV-72's declared neighbours (C021, C030, C083).

These are contract-level adapters: they speak the shapes the contract declares for each neighbour so the
integration seams are executable and tested.  They are **not** the neighbours themselves - GAP-02, GAP-11,
INV-68 and INV-69 are separate elements and are not in this archive.  Certification against the real
elements is an external step (waiver W-004).

* ``Gap02Publisher``   - upstream: publishes sealed PK_ACCEL_INVENTORY/1 snapshots (what discovery must emit).
* ``Gap11Scheduler``   - downstream: queues jobs, asks INV-72 to reserve, releases on completion; treats
                         ``retryable`` outcomes as requeue and ``refused``/``terminal`` as final.
* ``Inv68Packing``     - peer: packs CPU/RAM dimensions and hands INV-72 the feasible node set as
                         ``allowed_nodes`` so accelerator and non-accelerator placement agree.
* ``Inv69AgentLayer``  - downstream: model tools request accelerators with an idempotency key per tool call.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .discovery import seal
from .errors import AccelError


@dataclass
class Gap02Publisher:
    source: str
    key: bytes | None
    devices: list = field(default_factory=list)
    generation: int = 0
    clock: Callable[[], float] = time.time

    def publish(self) -> dict:
        self.generation += 1
        return seal({"schema": "PK_ACCEL_INVENTORY/1", "source": self.source, "generation": self.generation,
                     "observed_at": self.clock(), "devices": [dict(d) for d in self.devices]}, self.key)


@dataclass
class Gap11Scheduler:
    service: object
    token_fn: Callable[[], str] | None = None
    queue: list = field(default_factory=list)
    running: dict = field(default_factory=dict)
    final: dict = field(default_factory=dict)

    def submit(self, job_id: str, req: dict) -> None:
        self.queue.append((job_id, req))

    def tick(self) -> None:
        pending, self.queue = self.queue, []
        for job_id, req in pending:
            try:
                doc = self.service.request(req, token=self.token_fn() if self.token_fn else None)
            except AccelError as e:
                if e.retryable:
                    self.queue.append((job_id, req))
                else:
                    self.final[job_id] = e.code
                continue
            if doc["selected"]:
                self.running[job_id] = (doc["reservation_id"], req["tenant"])
            else:
                self.final[job_id] = doc["code"]

    def complete(self, job_id: str) -> None:
        rid, tenant = self.running.pop(job_id)
        self.service.release(rid, tenant=tenant, token=self.token_fn() if self.token_fn else None)
        self.final[job_id] = "completed"


@dataclass
class Inv68Packing:
    nodes: dict  # node -> {"cpu": free, "ram_gb": free}

    def feasible(self, cpu: int, ram_gb: float) -> list[str]:
        return sorted(n for n, r in self.nodes.items() if r["cpu"] >= cpu and r["ram_gb"] >= ram_gb)

    def constrain(self, req: dict, cpu: int, ram_gb: float) -> dict:
        nodes = self.feasible(cpu, ram_gb)
        if not nodes:
            raise AccelError("ACCEL_INSUFFICIENT_COUNT", "INV-68: no node fits the non-accelerator dimensions")
        return {**req, "allowed_nodes": nodes}


@dataclass
class Inv69AgentLayer:
    service: object
    token_fn: Callable[[], str] | None = None

    def tool_call(self, run_id: str, step: int, tenant: str, cls: str, mem_gb: float) -> dict:
        return self.service.request({"class": cls, "mem_gb": mem_gb, "tenant": tenant, "workload": run_id,
                                     "idempotency_key": f"{run_id}:{step}"},
                                    token=self.token_fn() if self.token_fn else None)
