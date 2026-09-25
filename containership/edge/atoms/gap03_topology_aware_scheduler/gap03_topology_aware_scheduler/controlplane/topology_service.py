"""MC-002 - Authenticated topology mutation boundary.

Every mutation arrives as ``(credential, request)``.  The credential is an
Ed25519-signed GAP03-ID/1 token (MC-012) whose ``req`` claim binds the
canonical digest of the request (integrity across intermediaries).  The
request carries request_id, source_service, reason, expected_generation and
mutations.  Flow: verify -> integrity -> rate/size limits -> authorize (with
two-person rule) -> audit (fail closed) -> atomic CAS commit -> result.
Repeated request_ids return the original outcome.
"""
from __future__ import annotations

from . import canonical
from .admission import TokenBucket
from .authz import authorize, required_permissions
from .errors import SchedulerError, to_external
from .retry import DedupStore
from .topology_store import MAX_BATCH

AUDIENCE = "gap03.topology"
MAX_REQUEST_BYTES = 512 * 1024


class TopologyService:
    def __init__(self, store, trust, audit, *, fence_provider=lambda: 0, per_principal_rps=5.0, global_rps=50.0,
                 metrics=None, controls=None):
        self.store, self.trust, self.audit, self.fence = store, trust, audit, fence_provider
        self.per_principal_rps = per_principal_rps
        self.global_bucket = TokenBucket(global_rps, global_rps * 2)
        self.principals: dict[str, TokenBucket] = {}
        self.dedup = DedupStore()
        self.metrics, self.controls = metrics, controls

    def mutate(self, credential: str, request: dict, *, approvals: tuple[str, ...] = ()) -> dict:
        try:
            return self._mutate(credential, request, approvals)
        except SchedulerError as exc:
            if self.metrics:
                self.metrics.inc("gap03_topology_mutations_total", result=exc.code)
            return {"ok": False, "error": to_external(exc, correlation_id=str(request.get("request_id", "")))}

    def _mutate(self, credential, request, approvals):
        claims = self.trust.verify_token(credential, audience=AUDIENCE)
        body = canonical.dumps(request)
        if len(body) > MAX_REQUEST_BYTES:
            raise SchedulerError("PAYLOAD_TOO_LARGE", "request too large")
        if claims.get("req") != canonical.digest(request):
            self.audit.append(actor=claims["sub"], action="topology.integrity_failure", target="topology", result="denied",
                              request_id=str(request.get("request_id", "")))
            raise SchedulerError("UNAUTHENTICATED", "request not bound to credential")
        for f in ("request_id", "source_service", "reason", "expected_generation", "mutations"):
            if f not in request:
                raise SchedulerError("INVALID_ARGUMENT", f"missing {f}")
        hit, prior = self.dedup.get(("topo", claims["sub"], request["request_id"]))
        if hit:
            return prior
        if self.controls is not None:
            self.controls.check("topology.mutate", scope={})
        if self.global_bucket.take():
            raise SchedulerError("OVERLOADED", "global mutation rate")
        bucket = self.principals.setdefault(claims["sub"], TokenBucket(self.per_principal_rps, self.per_principal_rps * 2))
        if bucket.take():
            raise SchedulerError("OVERLOADED", "principal mutation rate")
        if len(request["mutations"]) > MAX_BATCH:
            raise SchedulerError("PAYLOAD_TOO_LARGE", "bulk limit")
        approver_claims = [self.trust.verify_token(a, audience=AUDIENCE + ".approve") for a in approvals]
        for a in approver_claims:
            if a.get("req") != canonical.digest(request):
                raise SchedulerError("PERMISSION_DENIED", "approval not bound to this request")
        needed = required_permissions(request["mutations"])
        try:
            decision = authorize(claims.get("roles", []), needed, requester=claims["sub"], approvers=approver_claims)
        except SchedulerError as exc:
            self.audit.append(actor=claims["sub"], action="topology.mutate", target="topology", result="denied",
                              reason=exc.reason, request_id=request["request_id"], generation=self.store.generation)
            raise
        before = {m["id"]: self.store.state["nodes"].get(m["id"]) for m in request["mutations"]}
        # audit BEFORE commit: a privileged mutation cannot happen unaudited (fail closed)
        self.audit.append(actor=claims["sub"], action="topology.mutate.authorized", target="topology", result="authorized",
                          reason=request["reason"], request_id=request["request_id"], generation=self.store.generation,
                          before=before, detail={"policy": decision, "source": request["source_service"],
                                                 "mutations": [m["op"] for m in request["mutations"]]})
        try:
            gen = self.store.submit({"type": "batch", "expected_generation": request["expected_generation"],
                                     "mutations": request["mutations"], "fence": self.fence()})
        except SchedulerError as exc:
            # rolled back: DurableStore applied the batch to a copy only, nothing leaked
            self.audit.append(actor=claims["sub"], action="topology.mutate.rejected", target="topology", result=exc.code,
                              reason=exc.reason, request_id=request["request_id"], generation=self.store.generation)
            raise
        after = {m["id"]: self.store.state["nodes"].get(m["id"]) for m in request["mutations"]}
        self.audit.append(actor=claims["sub"], action="topology.mutate.committed", target="topology", result="ok",
                          request_id=request["request_id"], generation=gen, before=before, after=after)
        result = {"ok": True, "generation": gen, "request_id": request["request_id"]}
        self.dedup.put(("topo", claims["sub"], request["request_id"]), result)
        if self.metrics:
            self.metrics.inc("gap03_topology_mutations_total", result="ok")
        return result
