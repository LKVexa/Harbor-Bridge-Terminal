"""Fleet simulation and fault-injection harness (component 33).

Builds a complete, deterministic GAP-08 world — keys in separate trust
domains, enrolled devices, simulated GAP-01 supervisors behind a
fault-injectable channel, a signed GAP-07 verification, a GAP-09 evidence
minter, topology inventory, durable file store and WORM audit sink — so
tests, benchmarks, soak runs and chaos campaigns exercise the *real*
controller code paths.  Faults available: node offline, lost request, lost
ack, duplicate delivery, node-side op failure, audit-sink outage, dependency
outage, lease expiry / stale controller, clock advance, reconnect storm.
"""
from __future__ import annotations

import hashlib
import random
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .admission import AdmissionController, AdmissionLimits
from .artifact import ArtifactVerifier
from .audit_sink import FileWormSink
from .authz import ApprovalLedger, Policy, Principal
from .common import FakeClock, KeyRing, new_id, sign_envelope
from .conflicts import ConflictDetector
from .controller import Controller
from .dependencies import DependencyHealth
from .executor import CommandExecutor
from .freeze import FreezeControl
from .health import HealthGateAdapter
from .identity import DeviceRegistry
from .lease import LeaseService
from .retry import BackoffPolicy, CircuitBreaker
from .store import FileStateStore
from .telemetry import Telemetry
from .topology import BlastRadiusPolicy, Inventory, NodeInfo, TopologyEngine
from .transport import SimChannel, SimNodeSupervisor

MEAS = {"boot": "a" * 64, "runtime": "b" * 64}
COMPAT = {"python": "3.12", "arch": "x86_64", "supervisor_protocol": "PK_NODE_COMMAND/1", "node_runtime": "generic-ab-1",
          "state_schema": "PK_CONTROLLER_STATE/1"}

OPERATOR = Principal("alice", frozenset({"release-operator"}))
APPROVER = Principal("bob", frozenset({"release-approver"}))
SRE = Principal("carol", frozenset({"sre-oncall"}))
SECURITY = Principal("dave", frozenset({"security-officer"}))
GATEKEEPER = Principal("ctl-svc", frozenset({"controller"}))


@dataclass
class World:
    root: Path
    clock: FakeClock
    ring: KeyRing                 # verification side (controller trust domain; verify-only use)
    nodes: dict[str, SimNodeSupervisor]
    channel: SimChannel
    registry: DeviceRegistry
    inventory: Inventory
    store: FileStateStore
    leases: LeaseService
    sink: FileWormSink
    deps: DependencyHealth
    approvals: ApprovalLedger
    freeze: FreezeControl
    conflicts: ConflictDetector
    admission: AdmissionController
    verifier: ArtifactVerifier
    health: HealthGateAdapter
    telemetry: Telemetry
    topology: TopologyEngine
    payload: bytes = b""
    digest: str = ""
    controllers: dict[str, Controller] = field(default_factory=dict)

    # -------- controllers
    def controller(self, cid: str = "ctl-1") -> Controller:
        if cid not in self.controllers:
            ex = CommandExecutor(self.channel, self.registry, clock=self.clock,
                                 backoff=BackoffPolicy(0.1, 1.0, 3, 10.0),
                                 breaker=CircuitBreaker(clock=self.clock, failure_threshold=50),
                                 admission=self.admission,
                                 site_of={n: i.site for n, i in self.inventory.nodes.items()})
            self.controllers[cid] = Controller(
                controller_id=cid, store=self.store, leases=self.leases, conflicts=self.conflicts, sink=self.sink,
                health=self.health, verifier=self.verifier, executor=ex, topology=self.topology,
                inventory=lambda: Inventory(self.inventory.nodes, self.inventory.version, self.clock.now() - 1),
                freeze=self.freeze, approvals=self.approvals, deps=self.deps, admission=self.admission,
                telemetry=self.telemetry, clock=self.clock)
        return self.controllers[cid]

    # -------- signed inputs
    def verification(self, bundle: str = "v2", **over: Any) -> dict[str, Any]:
        now = self.clock.now()
        body = {"schema": "PK_VERIFICATION/1", "kind": "bundle", "verified": True, "subject": bundle,
                "digest": self.digest, "size": len(self.payload), "algorithm": "hmac-sha256-test",
                "verifier": "gap07-verifier-1", "verified_at": now - 1, "expires_at": now + 86400}
        body.update(over)
        return sign_envelope(self._gap07, "gap07-k1", body)

    def evidence(self, rollout_id: str, cohort: str, nodes: Iterable[str], *, healthy: bool = True,
                 applied_at: float | None = None, sample: Iterable[str] | None = None, **over: Any) -> dict[str, Any]:
        nodes = sorted(nodes)
        sampled = sorted(sample) if sample is not None else nodes
        now = self.clock.now()
        start = (applied_at if applied_at is not None else now - 120) + 60
        body = {"schema": "PK_HEALTH_EVIDENCE/1", "evidence_id": new_id("ev"), "nonce": new_id("n"),
                "source": "gap09-obs", "rollout_id": rollout_id, "cohort": cohort, "gate_class": "wave",
                "observed_at": now, "window_start": start, "window_end": max(start, now),
                "sampled_nodes": sampled, "healthy_nodes": sampled if healthy else [],
                "verdict": "healthy" if healthy else "unhealthy"}
        body.update(over)
        return sign_envelope(self._gap09, "gap09-k1", body)

    def pass_gate(self, ctl: Controller, rid: str, *, healthy: bool = True, who: Principal = GATEKEEPER,
                  settle: float = 90.0) -> dict[str, Any]:
        st = ctl.status(rid)
        p = st["pending"]
        self.clock.advance(settle)
        rec = self.store.load(rid).state["pending"]
        applied = [n for n, o in rec["outcomes"].items() if o["status"] == "ok"]
        return ctl.gate(who, rid, self.evidence(rid, p["cohort"], applied, healthy=healthy,
                                                applied_at=p["applied_at"]))

    def observed(self) -> dict[str, str]:
        return {n: s.version for n, s in self.nodes.items()}

    _gap07: KeyRing = None  # type: ignore[assignment]
    _gap09: KeyRing = None  # type: ignore[assignment]


def build_world(n_nodes: int = 12, *, sites: int = 3, racks_per_site: int = 2, root: str | Path | None = None,
                seed: int = 7, protected: Iterable[str] = (), max_fraction_per_domain: float = 0.5,
                limits: AdmissionLimits | None = None, payload: bytes | None = None,
                installers: bool = False) -> World:
    rng = random.Random(seed)
    root = Path(root or tempfile.mkdtemp(prefix="gap08-world-"))
    clock = FakeClock()
    # One shared verify ring (HMAC is symmetric; in production each domain holds its own private key
    # and the controller holds only public keys).
    ring = KeyRing()
    ring.add("gap07-k1")
    ring.add("gap09-k1")
    ring.add("sink-k1")
    payload = payload if payload is not None else bytes(rng.getrandbits(8) for _ in range(4096))
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    registry = DeviceRegistry(ring, clock=clock)
    nodes: dict[str, SimNodeSupervisor] = {}
    inv_nodes: dict[str, NodeInfo] = {}
    for i in range(1, n_nodes + 1):
        nid = f"n{i:03d}"
        kid = ring.add(f"dev-{nid}-k1")
        registry.enroll(nid, kid, MEAS)
        sup = SimNodeSupervisor(nid, ring, kid, dict(MEAS), "v1", None, clock=clock)
        if installers:
            from .installer import ABInstaller
            sup.installer = ABInstaller(root / "nodes" / nid)
            base = b"factory-image-v1"
            sup.installer.provision(base, "sha256:" + hashlib.sha256(base).hexdigest())
            sup.payloads[digest] = payload
        nodes[nid] = sup
        s = (i - 1) % sites
        r = ((i - 1) // sites) % racks_per_site
        inv_nodes[nid] = NodeInfo(f"site{s}", f"rack{r}", "edge-gw")
    inventory = Inventory(inv_nodes, 1, clock.now())
    policy = Policy()
    approvals = ApprovalLedger(policy, clock=clock)
    deps = DependencyHealth(clock=clock, stale_after_s=10 ** 9)
    deps.mark_all_ok()
    admission = AdmissionController(limits or AdmissionLimits(api_rate_per_s=1000, api_burst=1000), clock=clock)
    leases = LeaseService(clock=clock, persist_path=root / "leases.json")
    store = FileStateStore(root / "store", clock=clock, fence_check=None)
    store.fence_check = lambda rid, tok: leases.check(f"rollout/{rid}", tok)
    w = World(root=root, clock=clock, ring=ring, nodes=nodes, channel=SimChannel(nodes), registry=registry,
              inventory=inventory, store=store, leases=leases,
              sink=FileWormSink(root / "audit.log", ring, "sink-k1"), deps=deps, approvals=approvals,
              freeze=FreezeControl(approvals, clock=clock), conflicts=ConflictDetector(), admission=admission,
              verifier=ArtifactVerifier(ring, {"gap07-k1"}, clock=clock),
              health=HealthGateAdapter(ring, {"gap09-obs": {"gap09-k1"}}, clock=clock),
              telemetry=Telemetry(clock=clock),
              topology=TopologyEngine(BlastRadiusPolicy(max_fraction_per_domain=max_fraction_per_domain,
                                                        max_fraction_per_site=0.67,
                                                        protected_domains=frozenset(protected))),
              payload=payload, digest=digest)
    w._gap07 = ring
    w._gap09 = ring
    return w


def spread_waves(world: World, sizes: Iterable[int]) -> list[list[str]]:
    """Waves that interleave sites/racks so blast-radius policy admits them."""
    doms: dict[str, list[str]] = {}
    for n in sorted(world.nodes):
        doms.setdefault(world.inventory.nodes[n].fault_domain, []).append(n)
    order = [n for rank in range(max(len(v) for v in doms.values()))
             for d in sorted(doms) for n in doms[d][rank:rank + 1]]
    waves, i = [], 0
    for s in sizes:
        waves.append(order[i:i + s])
        i += s
    return waves
