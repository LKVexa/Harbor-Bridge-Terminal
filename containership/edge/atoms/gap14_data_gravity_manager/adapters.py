"""Estate adapters: GAP-13, GAP-03, GAP-05, SCH-01 (reads) and PLN-06 (handoff).

G14-P0-02..06.  Every adapter:

* calls its transport through ``call_with_resilience`` (deadline, breaker,
  retry for idempotent reads only);
* verifies the producer's signature against the trust store and expected issuer;
* validates the body strictly (schema tag, exact fields, identifier/number domains);
* enforces freshness/TTL and clock skew, and a monotonic version watermark
  (anti-rollback);
* binds the artifact to the exact request (canonical request hash / tenant /
  dataset) so a valid artifact for a different request is rejected;
* fails closed: any failure raises ``G14Error`` and no default is substituted.

``transport`` is any callable ``(request: dict, timeout_s: float) -> dict``; the
estate client (HTTP/gRPC/queue) is injected at composition time.  Test fixtures
in ``tests/fixtures/estate.py`` implement the same callables.
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .errors import G14Error
from .resilience import (CircuitBreaker, Deadline, FreshnessPolicy, RetryPolicy, StaleDataPolicy,
                         call_with_resilience)
from .trust import Clock, KeyRing, check_fresh, digest, exact_fields, ident, number

Transport = Callable[[Mapping[str, Any], float], Mapping[str, Any]]


class VersionWatermark:
    """Highest accepted version per source; lower versions are a rollback."""

    def __init__(self) -> None:
        self._hi: dict[str, int] = {}
        self._lock = threading.Lock()

    def observe(self, source: str, version: int) -> None:
        with self._lock:
            hi = self._hi.get(source, -1)
            if version < hi:
                raise G14Error("G14_VERSION_ROLLBACK", f"{source} version went backwards",
                               details={"source": source, "seen": hi, "got": version})
            self._hi[source] = version

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._hi)


@dataclass
class AdapterContext:
    keyring: KeyRing
    clock: Clock
    freshness: FreshnessPolicy = field(default_factory=FreshnessPolicy)
    stale_policy: StaleDataPolicy = field(default_factory=StaleDataPolicy)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    watermark: VersionWatermark = field(default_factory=VersionWatermark)
    timeout_cap_s: float = 0.02
    rng: random.Random = field(default_factory=lambda: random.Random(14))
    sleep: Callable[[float], None] | None = None
    on_event: Callable[[str, str, float], None] | None = None   # (dependency, outcome, seconds)


class _SignedFeed:
    dependency = "abstract"
    issuer = "abstract"
    ttl_kind = "abstract"

    def __init__(self, transport: Transport, ctx: AdapterContext, *, breaker: CircuitBreaker | None = None):
        self.transport, self.ctx = transport, ctx
        self.breaker = breaker or CircuitBreaker(self.dependency, clock=ctx.clock)

    def _fetch(self, request: Mapping[str, Any], deadline: Deadline) -> Mapping[str, Any]:
        t0 = self.ctx.clock.monotonic()
        outcome = "error"
        try:
            env = call_with_resilience(lambda timeout: self.transport(request, timeout), dependency=self.dependency,
                                       deadline=deadline, timeout_cap_s=self.ctx.timeout_cap_s, breaker=self.breaker,
                                       retry=self.ctx.retry, idempotent=True, rng=self.ctx.rng, sleep=self.ctx.sleep)
            exact_fields(env, f"{self.dependency}.envelope", ["body", "sig"])
            body = env["body"]
            if not isinstance(body, Mapping):
                raise G14Error("G14_INVALID_REQUEST", f"{self.dependency} body not an object")
            self.ctx.keyring.verify(body, env["sig"], expected_issuer=self.issuer, now=self.ctx.clock.now())
            outcome = "ok"
            return body
        except G14Error as exc:
            outcome = exc.code
            raise
        finally:
            if self.ctx.on_event:
                self.ctx.on_event(self.dependency, outcome, self.ctx.clock.monotonic() - t0)

    def _fresh(self, issued_at: Any, mode: str) -> float:
        ttl = self.ctx.freshness.ttl(self.ttl_kind)
        allowed = self.ctx.stale_policy.allowed_age(self.ttl_kind, ttl, mode)
        return check_fresh(number(issued_at, f"{self.dependency}.issued_at", maximum=1e11), allowed,
                           self.ctx.clock.now(), self.ttl_kind, skew=self.ctx.freshness.max_skew_s)


# ------------------------------------------------------------------ GAP-13 policy
POLICY_REQUEST = "PK_POLICY_REQUEST/1"
POLICY_VERDICT = "PK_POLICY_VERDICT/1"


@dataclass(frozen=True)
class PolicyVerdict:
    allow: bool
    decision_id: str
    policy_version: int
    rule_ids: tuple[str, ...]
    obligations: Mapping[str, Any]
    issuer: str
    age_s: float
    request_hash: str
    body_digest: str = ""
    issued_at: float = 0.0

    def ref(self) -> dict[str, Any]:
        return {"decision_id": self.decision_id, "policy_version": self.policy_version, "issuer": self.issuer,
                "rule_ids": list(self.rule_ids), "allow": self.allow, "request_hash": self.request_hash,
                "age_s": round(self.age_s, 3), "issued_at": self.issued_at, "body_digest": self.body_digest}


class PolicyAdapter(_SignedFeed):
    dependency, issuer, ttl_kind = "GAP-13", "gap13-policy", "policy_verdict"

    @staticmethod
    def build_request(*, tenant_id: str, workload_id: str, dataset: str, classification: str, source_site: str,
                      destination_site: str, operation: str, jurisdiction_tags: list[str], evaluated_at: float) -> dict[str, Any]:
        if operation not in ("hold", "process"):
            raise G14Error("G14_INVALID_REQUEST", "operation must be hold|process")
        return {"schema": POLICY_REQUEST, "tenant_id": tenant_id, "workload_id": workload_id, "dataset": dataset,
                "classification": classification, "source_site": source_site, "destination_site": destination_site,
                "operation": operation, "jurisdiction_tags": sorted(jurisdiction_tags), "evaluated_at": evaluated_at}

    def evaluate(self, request: Mapping[str, Any], deadline: Deadline, mode: str = "production") -> PolicyVerdict:
        req_hash = digest(request)
        b = self._fetch(request, deadline)
        exact_fields(b, "policy.verdict", ["schema", "decision_id", "request_hash", "allow", "policy_version",
                                           "rule_ids", "obligations", "issued_at", "ttl_s"])
        if b["schema"] != POLICY_VERDICT:
            raise G14Error("G14_INVALID_REQUEST", "unsupported verdict schema", details={"schema": b["schema"]})
        if b["request_hash"] != req_hash:
            raise G14Error("G14_BINDING_MISMATCH", "verdict bound to a different request")
        if not isinstance(b["allow"], bool):
            raise G14Error("G14_INVALID_REQUEST", "verdict.allow must be bool")
        version = int(number(b["policy_version"], "verdict.policy_version", maximum=2**53))
        ttl = number(b["ttl_s"], "verdict.ttl_s", maximum=86400)
        age = self._fresh(b["issued_at"], mode)
        if age > ttl:
            raise G14Error("G14_STALE_INPUT", "verdict past its own TTL", details={"age_s": age, "ttl_s": ttl})
        self.ctx.watermark.observe("GAP-13/policy", version)
        if not isinstance(b["rule_ids"], list) or not isinstance(b["obligations"], Mapping):
            raise G14Error("G14_INVALID_REQUEST", "verdict rule_ids/obligations malformed")
        return PolicyVerdict(b["allow"], ident(b["decision_id"], "verdict.decision_id"), version,
                             tuple(ident(r, "verdict.rule_id") for r in b["rule_ids"]), dict(b["obligations"]),
                             self.issuer, age, req_hash, digest(b), float(b["issued_at"]))


# --------------------------------------------------------------- GAP-03 topology
TOPOLOGY = "PK_TOPOLOGY_SNAPSHOT/1"
_ROUTE_FIELDS = ["from", "to", "available", "locality_multiplier", "egress_per_gb"]
_ROUTE_OPT = ["bandwidth_gbps", "congestion"]


@dataclass(frozen=True)
class TopologySnapshot:
    snapshot_id: str
    version: int
    age_s: float
    routes: Mapping[tuple[str, str], Mapping[str, Any]]
    body_digest: str = ""

    def ref(self) -> dict[str, Any]:
        return {"snapshot_id": self.snapshot_id, "version": self.version, "age_s": round(self.age_s, 3),
                "body_digest": self.body_digest}


class TopologyAdapter(_SignedFeed):
    dependency, issuer, ttl_kind = "GAP-03", "gap03-topology", "topology_snapshot"

    def snapshot(self, sites: list[str], deadline: Deadline, mode: str = "production") -> TopologySnapshot:
        b = self._fetch({"schema": "PK_TOPOLOGY_REQUEST/1", "sites": sorted(set(sites))}, deadline)
        exact_fields(b, "topology", ["schema", "snapshot_id", "version", "issued_at", "routes"])
        if b["schema"] != TOPOLOGY:
            raise G14Error("G14_INVALID_REQUEST", "unsupported topology schema")
        age = self._fresh(b["issued_at"], mode)
        version = int(number(b["version"], "topology.version", maximum=2**53))
        self.ctx.watermark.observe("GAP-03/topology", version)
        if not isinstance(b["routes"], list) or len(b["routes"]) > 10_000:
            raise G14Error("G14_INVALID_REQUEST", "topology.routes malformed")
        routes: dict[tuple[str, str], Mapping[str, Any]] = {}
        for r in b["routes"]:
            exact_fields(r, "topology.route", _ROUTE_FIELDS, _ROUTE_OPT)
            key = (ident(r["from"], "route.from"), ident(r["to"], "route.to"))
            if key in routes:
                raise G14Error("G14_INVALID_REQUEST", "duplicate route in topology", details={"route": list(key)})
            if not isinstance(r["available"], bool):
                raise G14Error("G14_INVALID_REQUEST", "route.available must be bool")
            routes[key] = {
                "available": r["available"],
                # a cross-site route with a zero multiplier would make movement free: reject as invalid (P0-03 A07)
                "locality_multiplier": number(r["locality_multiplier"], "route.locality_multiplier", minimum=1e-9, maximum=1e6),
                "egress_per_gb": number(r["egress_per_gb"], "route.egress_per_gb", maximum=1e6),
                "bandwidth_gbps": number(r.get("bandwidth_gbps", 1.0), "route.bandwidth_gbps", minimum=1e-6, maximum=1e5),
                "congestion": number(r.get("congestion", 0.0), "route.congestion", maximum=0.99),
            }
        return TopologySnapshot(ident(b["snapshot_id"], "topology.snapshot_id"), version, age, routes, digest(b))


# ------------------------------------------------------------ GAP-05 replication
CONVERGENCE = "PK_CONVERGENCE_PROOF/1"


@dataclass(frozen=True)
class ConvergenceProof:
    converged: bool
    dataset_version: int
    open_conflicts: int
    watermark: str
    age_s: float
    body_digest: str = ""

    def ref(self) -> dict[str, Any]:
        return {"converged": self.converged, "dataset_version": self.dataset_version,
                "open_conflicts": self.open_conflicts, "watermark": self.watermark, "age_s": round(self.age_s, 3),
                "body_digest": self.body_digest}


class ReplicationAdapter(_SignedFeed):
    dependency, issuer, ttl_kind = "GAP-05", "gap05-replication", "convergence_proof"

    def proof(self, tenant_id: str, dataset: str, deadline: Deadline, mode: str = "production") -> ConvergenceProof:
        b = self._fetch({"schema": "PK_CONVERGENCE_REQUEST/1", "tenant_id": tenant_id, "dataset": dataset}, deadline)
        exact_fields(b, "convergence", ["schema", "tenant_id", "dataset", "dataset_version", "converged",
                                        "open_conflicts", "watermark", "issued_at"])
        if b["schema"] != CONVERGENCE:
            raise G14Error("G14_INVALID_REQUEST", "unsupported convergence schema")
        if b["tenant_id"] != tenant_id or b["dataset"] != dataset:
            raise G14Error("G14_BINDING_MISMATCH", "convergence proof for a different dataset/tenant")
        age = self._fresh(b["issued_at"], mode)
        ver = int(number(b["dataset_version"], "convergence.dataset_version", maximum=2**53))
        self.ctx.watermark.observe(f"GAP-05/{tenant_id}/{dataset}", ver)
        conflicts = int(number(b["open_conflicts"], "convergence.open_conflicts", maximum=2**31))
        if not isinstance(b["converged"], bool):
            raise G14Error("G14_INVALID_REQUEST", "convergence.converged must be bool")
        # A proof that claims convergence with open conflicts is self-contradictory -> not converged.
        return ConvergenceProof(b["converged"] and conflicts == 0, ver, conflicts,
                                ident(b["watermark"], "convergence.watermark"), age, digest(b))


# --------------------------------------------------------------- SCH-01 placement
PLACEMENT = "PK_PLACEMENT_SNAPSHOT/1"
_SITE_FIELDS = ["available", "architectures", "runtimes", "free_cpu", "free_gpu", "quota_remaining_gb", "storage_free_gb"]


@dataclass(frozen=True)
class WorkloadRequirements:
    architecture: str = "x86_64"
    runtime: str = "python3.11"
    cpu: float = 1.0
    gpu: float = 0.0

    @classmethod
    def parse(cls, raw: Mapping[str, Any] | None) -> "WorkloadRequirements":
        if raw is None:
            return cls()
        exact_fields(raw, "requirements", [], ["architecture", "runtime", "cpu", "gpu"])
        return cls(ident(raw.get("architecture", "x86_64"), "requirements.architecture"),
                   ident(raw.get("runtime", "python3.11"), "requirements.runtime"),
                   number(raw.get("cpu", 1.0), "requirements.cpu", maximum=1e5),
                   number(raw.get("gpu", 0.0), "requirements.gpu", maximum=1e4))


@dataclass(frozen=True)
class PlacementSnapshot:
    snapshot_id: str
    version: int
    age_s: float
    sites: Mapping[str, Mapping[str, Any]]
    body_digest: str = ""

    def compatible(self, site: str, req: WorkloadRequirements) -> tuple[bool, str]:
        s = self.sites.get(site)
        if s is None or not s["available"]:
            return False, f"no compute capacity at {site}"
        if req.architecture not in s["architectures"]:
            return False, f"{site} lacks architecture {req.architecture}"
        if req.runtime not in s["runtimes"]:
            return False, f"{site} lacks runtime {req.runtime}"
        if s["free_cpu"] < req.cpu or s["free_gpu"] < req.gpu:
            return False, f"{site} lacks free cpu/gpu"
        return True, "ok"

    def data_quota_ok(self, site: str, size_gb: float) -> tuple[bool, str]:
        s = self.sites.get(site)
        if s is None:
            return False, f"no placement data for {site}"
        if s["quota_remaining_gb"] < size_gb or s["storage_free_gb"] < size_gb:
            return False, f"{site} quota/storage below {size_gb:g} GB"
        return True, "ok"

    def ref(self) -> dict[str, Any]:
        return {"snapshot_id": self.snapshot_id, "version": self.version, "age_s": round(self.age_s, 3),
                "body_digest": self.body_digest}


class PlacementAdapter(_SignedFeed):
    dependency, issuer, ttl_kind = "SCH-01", "sch01-placement", "placement_snapshot"

    def snapshot(self, tenant_id: str, sites: list[str], deadline: Deadline, mode: str = "production") -> PlacementSnapshot:
        b = self._fetch({"schema": "PK_PLACEMENT_REQUEST/1", "tenant_id": tenant_id, "sites": sorted(set(sites))}, deadline)
        exact_fields(b, "placement", ["schema", "snapshot_id", "version", "tenant_id", "issued_at", "sites"])
        if b["schema"] != PLACEMENT:
            raise G14Error("G14_INVALID_REQUEST", "unsupported placement schema")
        if b["tenant_id"] != tenant_id:
            raise G14Error("G14_BINDING_MISMATCH", "placement snapshot for a different tenant")
        age = self._fresh(b["issued_at"], mode)
        version = int(number(b["version"], "placement.version", maximum=2**53))
        self.ctx.watermark.observe(f"SCH-01/{tenant_id}", version)
        if not isinstance(b["sites"], Mapping):
            raise G14Error("G14_INVALID_REQUEST", "placement.sites malformed")
        sites: dict[str, Mapping[str, Any]] = {}
        for name, s in b["sites"].items():
            exact_fields(s, "placement.site", _SITE_FIELDS)
            sites[ident(name, "placement.site")] = {
                "available": bool(s["available"]) if isinstance(s["available"], bool) else _bad("available"),
                "architectures": frozenset(ident(a, "site.architecture") for a in s["architectures"]),
                "runtimes": frozenset(ident(r, "site.runtime") for r in s["runtimes"]),
                "free_cpu": number(s["free_cpu"], "site.free_cpu", maximum=1e7),
                "free_gpu": number(s["free_gpu"], "site.free_gpu", maximum=1e6),
                "quota_remaining_gb": number(s["quota_remaining_gb"], "site.quota_remaining_gb"),
                "storage_free_gb": number(s["storage_free_gb"], "site.storage_free_gb"),
            }
        return PlacementSnapshot(ident(b["snapshot_id"], "placement.snapshot_id"), version, age, sites, digest(b))


def _bad(name: str) -> Any:
    raise G14Error("G14_INVALID_REQUEST", f"site.{name} malformed")


# ------------------------------------------------------------ PLN-06 data plane
HANDOFF = "PK_DATA_MOVE_HANDOFF/1"
HANDOFF_ACK = "PK_DATA_MOVE_ACK/1"


class DataPlaneHandoff:
    """Signed, idempotent handoff of an approved move-data decision to PLN-06.

    The handoff id is derived from the decision id, so resubmitting the same
    decision returns the original acknowledgement instead of a second move.
    Only envelopes with ``executable: true`` (production decisions) may be handed
    off; shadow/simulation artifacts are refused (G14_NOT_EXECUTABLE).
    """

    dependency, issuer = "PLN-06", "pln06-dataplane"

    def __init__(self, transport: Transport, ctx: AdapterContext, *, signing_kid: str, handoff_ttl_s: float = 300.0):
        self.transport, self.ctx, self.signing_kid, self.handoff_ttl_s = transport, ctx, signing_kid, handoff_ttl_s
        self.breaker = CircuitBreaker(self.dependency, clock=ctx.clock)
        self._acks: dict[str, Mapping[str, Any]] = {}
        self._lock = threading.Lock()

    def submit(self, envelope: Mapping[str, Any], deadline: Deadline) -> dict[str, Any]:
        rec = envelope.get("recommendation", {})
        prov = envelope.get("provenance", {})
        if envelope.get("executable") is not True or prov.get("mode") != "production":
            raise G14Error("G14_NOT_EXECUTABLE", "only production decisions may be executed")
        if rec.get("direction") not in ("move-data", "move-data-partial", "replicate"):
            raise G14Error("G14_INVALID_REQUEST", "only data-movement decisions are handed to PLN-06")
        # verify the envelope was produced by this GAP-14 (integrity of the thing we execute)
        self.ctx.keyring.verify({k: v for k, v in envelope.items() if k != "sig"}, envelope.get("sig", {}),
                                expected_issuer=None, now=self.ctx.clock.now())
        now = self.ctx.clock.now()
        check_fresh(prov["issued_at"], self.handoff_ttl_s, now, "decision envelope")
        handoff_id = "ho-" + digest({"decision_id": prov["decision_id"]})[7:39]
        with self._lock:
            if handoff_id in self._acks:
                return {**self._acks[handoff_id], "duplicate": True, "reason_code": "G14_HANDOFF_DUPLICATE"}
        body = {"schema": HANDOFF, "handoff_id": handoff_id, "decision_id": prov["decision_id"],
                "tenant_id": prov["identity"]["tenant_id"], "dataset": prov["request"]["dataset"]["name"],
                "kind": rec["direction"], "shards": rec["cost_breakdown"].get("shards"),
                "from": rec["cost_breakdown"]["from"], "to": rec["to"], "size_gb": rec["cost_breakdown"]["size_gb"],
                "obligations": prov.get("obligations", {}), "provenance_digest": prov["input_digest"],
                "not_after": now + self.handoff_ttl_s}
        signed = {"body": body, "sig": self.ctx.keyring.sign(body, self.signing_kid)}
        ack = call_with_resilience(lambda t: self.transport(signed, t), dependency=self.dependency, deadline=deadline,
                                   timeout_cap_s=self.ctx.timeout_cap_s, breaker=self.breaker, retry=self.ctx.retry,
                                   idempotent=True,  # safe: idempotency key makes resubmission a no-op at PLN-06
                                   rng=self.ctx.rng, sleep=self.ctx.sleep)
        exact_fields(ack, "handoff.ack", ["body", "sig"])
        self.ctx.keyring.verify(ack["body"], ack["sig"], expected_issuer=self.issuer, now=now)
        a = exact_fields(ack["body"], "handoff.ack.body", ["schema", "handoff_id", "accepted", "status"])
        if a["schema"] != HANDOFF_ACK or a["handoff_id"] != handoff_id:
            raise G14Error("G14_BINDING_MISMATCH", "ack does not match handoff")
        if a["accepted"] is not True:
            raise G14Error("G14_HANDOFF_REJECTED", "PLN-06 rejected handoff", details={"status": str(a["status"])[:64]})
        result = {"handoff_id": handoff_id, "accepted": True, "status": str(a["status"])[:64], "duplicate": False}
        with self._lock:
            self._acks.setdefault(handoff_id, result)
        return result
