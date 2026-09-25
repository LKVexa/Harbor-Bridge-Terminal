"""TopologyService — the authenticated, authorised, bounded boundary for the
three PK_TOPO_* interfaces (MC-012 .. MC-018, MC-036, MC-044 .. MC-049,
MC-061 .. MC-068).

Request pipeline (every step fails closed):

    decode(size/depth/dup-key/NaN guards) -> negotiate version -> schema
    -> readiness -> admission (per-tenant bucket + in-flight bound)
    -> authenticate (PKT1, replay for mutations) -> authorise (default deny,
    tenant scope, node binding) -> idempotency -> mode gate -> deadline
    -> dispatch -> [mutations: clone, apply, CAS, WAL fsync, swap] -> audit
    -> metrics/log/trace -> response (schema-validated)
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections.abc import Callable

from ..topology import CapacityExceeded, NoCoordinatorCandidate, Topology, TopologyError, TopologyLimits, UnknownNode, UnknownSite
from . import auth, errors, lifecycle, policy, wire
from .audit import AuditTrail
from .config import ConfigStore, Generation, SecretProvider
from .election import LeaseAuthority
from .health import HealthPolicy, LinkHealth
from .lifecycle import LinkState, Machine, Mode, SITE_TRANSITIONS, SiteState
from .persistence import StateStore
from .resilience import Admission, CircuitBreaker, Deadline, IdempotencyStore
from .telemetry import Logger, Metrics, Tracer

VERSION = "4.3.0"

def release_lineage() -> dict[str, str]:
    """Release identity attached to every decision, log line and audit record (MC-068)."""
    here = Path(__file__).resolve().parents[1]
    manifest = here / "RELEASE_MANIFEST.json"
    digest = os.environ.get("INV62_ARTIFACT_DIGEST", "")
    commit = os.environ.get("INV62_SOURCE_COMMIT", "")
    if manifest.exists() and not digest:
        try:
            data = json.loads(manifest.read_text())
            digest, commit = data.get("tree_digest", ""), commit or data.get("source_commit", "")
        except ValueError:
            digest = "manifest-unreadable"
    return {"version": VERSION, "artifact_digest": digest or "unreleased", "source_commit": commit or "unknown"}


@dataclass
class TenantState:
    topo: Topology
    health: dict[frozenset, LinkHealth] = field(default_factory=dict)
    quarantined: set[str] = field(default_factory=set)
    sites: dict[str, Machine] = field(default_factory=dict)
    reach_cache: tuple[int, str, frozenset[str]] | None = None


class TopologyService:
    def __init__(self, secrets: SecretProvider, *, state_dir: str | os.PathLike[str] | None = None,
                 clock: Callable[[], float] = time.time, mono: Callable[[], float] = time.monotonic,
                 log_sink: Any = None):
        self.clock, self.mono = clock, mono
        self.release = release_lineage()
        self.metrics = Metrics()
        self.logger = Logger(sink=log_sink, release=self.release["version"], clock=clock)
        self.tracer = Tracer()
        self.decisions = policy.DecisionLog()
        self.idempotency = IdempotencyStore(clock=mono)
        self.breaker = CircuitBreaker(clock=mono)
        self.state_dir = Path(state_dir) if state_dir else None
        self.tenants: dict[str, TenantState] = {}
        self.frozen = False
        self._lock = threading.RLock()
        self._ready = False
        self.clock_source = auth.Clock(clock)
        self.keyring = auth.KeyRing()
        self.authn = auth.Authenticator(self.keyring, self.clock_source)
        self.authz = auth.Authorizer()
        self.audit: AuditTrail | None = None
        self.store: StateStore | None = None
        self.leases = LeaseAuthority(ttl_s=10.0)
        self.leases._persist = self._persist_term
        self.admission: Admission | None = None
        self.cfg: dict[str, Any] = {}
        self.config = ConfigStore(secrets, clock=clock, on_activate=self._on_activate,
                                  directory=(self.state_dir / "config") if self.state_dir else None)

    # ------------------------------------------------------------ activation
    def _on_activate(self, gen: Generation) -> None:
        """Build every runtime object from the candidate first; only then swap
        (MC-027).  Any exception leaves the previous generation serving."""
        r = gen.resolved
        cfg = r.config
        keyring = auth.KeyRing()
        for kid, secret in r.token_keys.items():
            keyring.add(kid, secret)
        keyring.rotate_to(r.active_token_key)
        lim = cfg["limits"]
        limits = TopologyLimits(lim["max_nodes"], lim["max_links"], lim["max_degree"], lim["max_caps_per_node"])
        adm = cfg["admission"]
        admission = Admission(rate_per_s=adm["rate_per_s"], burst=adm["burst"], max_in_flight=adm["max_in_flight"],
                              max_tenants=lim["max_tenants"], clock=self.mono)
        audit = self.audit
        store = self.store
        if self.state_dir is not None and store is None:
            store = StateStore(self.state_dir / "state", r.state_key or r.audit_key,
                               encrypt=cfg["security"]["encrypt_at_rest"], fsync=cfg["security"]["audit_fsync"])
        if audit is None:
            path = (self.state_dir / "audit.jsonl") if self.state_dir else None
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
            audit = AuditTrail(r.audit_key, path, fsync=cfg["security"]["audit_fsync"])
        for t, ts in self.tenants.items():
            if len(ts.topo.nodes) > limits.max_nodes or len(ts.topo.links) > limits.max_links:
                raise errors.TopoError(errors.INVALID_REQUEST, "new limits are below current graph size",
                                       {"tenant": t, "nodes": len(ts.topo.nodes), "links": len(ts.topo.links)})
        if len(self.tenants) > lim["max_tenants"]:
            raise errors.TopoError(errors.INVALID_REQUEST, "new max_tenants below current tenant count")
        with self._lock:
            self.keyring = keyring
            previous = self.authn
            self.authn = auth.Authenticator(keyring, self.clock_source, previous.replay, previous.revoked_subjects)
            self.authn.on_spend = previous.on_spend
            self.admission = admission
            self.audit = audit
            first_store = store is not None and self.store is None
            self.store = store
            self.cfg = cfg
            self.leases.ttl_s = cfg["election"]["lease_ttl_s"]
            self.logger.level = {"debug": 10, "info": 20, "warning": 30, "error": 40}[cfg["telemetry"]["log_level"]]
            self.logger.expose = cfg["telemetry"]["expose_node_names"]
            self.metrics.max_label_values = cfg["telemetry"]["max_label_values"]
            self.tracer.sample_rate = cfg["telemetry"]["trace_sample_rate"]
            for ts in self.tenants.values():
                ts.topo.limits = limits
            self._limits = limits
            if first_store:
                self._recover()
                self.authn.on_spend = self._persist_nonce
            self._ready = True
        audit.append("config.activated", ts=self.clock(), config_generation=gen.provenance.generation,
                     reason=gen.provenance.source, subject=gen.provenance.author, release=self.release["version"])

    def activate_config(self, config: dict[str, Any], *, author: str, source: str,
                        expected_generation: int | None, signature: str | None = None):
        return self.config.activate(config, author=author, source=source,
                                    expected_generation=expected_generation, signature=signature)

    # ---------------------------------------------------------------- state
    def _tenant(self, tenant: str, create: bool) -> TenantState:
        ts = self.tenants.get(tenant)
        if ts is None:
            if not create:
                raise errors.TopoError(errors.UNKNOWN_NODE, "tenant has no topology")
            if len(self.tenants) >= self.cfg["limits"]["max_tenants"]:
                raise errors.TopoError(errors.QUOTA_EXCEEDED, "tenant table full")
            ts = self.tenants[tenant] = TenantState(Topology(limits=self._limits))
        return ts

    def _persist(self, kind: str, tenant: str | None, payload: Any) -> None:
        if self.store is None:
            return
        self.breaker.before()
        try:
            self.store.append(kind, tenant, payload)
        except OSError:
            self.breaker.failure()
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "state store write failed",
                                   {"dependency": "state"}) from None
        self.breaker.success()

    def _persist_nonce(self, key: str, expires_at: float) -> None:
        """Spent mutating nonces are durable before the request proceeds, so a
        captured credential cannot be replayed after a restart (T03)."""
        self._persist("nonce", None, {"k": key, "exp": expires_at})

    def _persist_term(self, key: str, term: int) -> None:
        tenant, _, site = key.partition("/")
        self._persist("term", tenant, {"site": site, "term": term})

    def checkpoint(self) -> None:
        """Snapshot full state and truncate the WAL (MC-047/MC-084)."""
        if self.store is None:
            return
        with self._lock:
            self.store.write_snapshot(self.export_state())

    WAL_COMPACT_BYTES = 4 * 1024 * 1024

    def _maybe_compact(self) -> None:
        """Bound WAL growth (including nonce records of refused requests) by
        checkpointing once the log exceeds WAL_COMPACT_BYTES."""
        if self.store is None:
            return
        try:
            size = self.store.wal.stat().st_size
        except OSError:
            return
        if size > self.WAL_COMPACT_BYTES:
            try:
                self.checkpoint()
            except OSError:
                self.logger.log("error", "state.compaction_failed")

    def export_state(self) -> dict[str, Any]:
        self.authn.replay.prune(self.clock())
        with self._lock:
            return {"format": "inv62-state/1", "release": self.release,
                    "tenants": {t: {"graph": ts.topo.snapshot(), "revision": ts.topo.revision,
                                    "quarantined": sorted(ts.quarantined),
                                    "health": {"|".join(sorted(k)): lh.to_dict() for k, lh in sorted(ts.health.items(), key=lambda kv: sorted(kv[0]))}}
                                for t, ts in sorted(self.tenants.items())},
                    "terms": dict(sorted(self.leases._terms.items())), "frozen": self.frozen,
                    "nonces": sorted([k, e] for k, e in self.authn.replay.entries())}

    def import_state(self, state: dict[str, Any]) -> None:
        """Validated reconstruction used by recovery and restore (MC-084)."""
        if state.get("format") != "inv62-state/1":
            raise errors.TopoError(errors.INVALID_REQUEST, "unknown state format")
        tenants = {}
        for t, data in state["tenants"].items():
            topo = Topology.from_snapshot(data["graph"], limits=self._limits)
            topo.revision = int(data["revision"])
            hp = HealthPolicy.from_config(self.cfg["health"]) if self.cfg else HealthPolicy()
            health = {}
            for pair, h in data.get("health", {}).items():
                a, _, b = pair.partition("|")
                if frozenset((a, b)) not in topo.links:
                    raise errors.TopoError(errors.INVALID_REQUEST, "health record for unknown link")
                health[frozenset((a, b))] = LinkHealth.from_dict(hp, h)
            tenants[t] = TenantState(topo, health=health, quarantined=set(data.get("quarantined", [])))
        terms = {k: int(v) for k, v in state.get("terms", {}).items()}
        with self._lock:
            self.tenants = tenants
            for k, v in terms.items():
                self.leases._terms[k] = max(v, self.leases._terms.get(k, 0))
            self.frozen = bool(state.get("frozen", False))
            self.authn.replay.restore([(str(k), float(e)) for k, e in state.get("nonces", [])], self.clock())

    def _recover(self) -> None:
        """Rebuild state from snapshot + WAL.  Replay uses maximal limits and no
        wall-clock checks so history always replays identically; the configured
        limits then apply to *future* growth only."""
        if self.store is None:  # pragma: no cover - guarded by caller
            return
        configured = self._limits
        self._limits = TopologyLimits(10**9, 10**9, 10**9, 10**6)
        try:
            self._replay()
        finally:
            self._limits = configured
            for ts in self.tenants.values():
                ts.topo.limits = configured

    def _replay(self) -> None:
        assert self.store is not None
        snapshot, records = self.store.load()
        if snapshot:
            self.import_state(snapshot)
        for rec in records:
            p = rec["payload"]
            if rec["kind"] == "apply":
                ts = self._tenant(rec["tenant"], create=True)
                new = ts.topo.clone()
                self._apply_mutations(ts, new, p["mutations"], check_time=False)
                removed = set(ts.topo.nodes) - set(new.nodes)
                ts.topo = new
                self._revoke_leases(rec["tenant"], removed)
            elif rec["kind"] == "term":
                key = f"{rec['tenant']}/{p['site']}"
                self.leases._terms[key] = max(p["term"], self.leases._terms.get(key, 0))
            elif rec["kind"] == "quarantine":
                ts = self._tenant(rec["tenant"], create=True)
                (ts.quarantined.add if p["on"] else ts.quarantined.discard)(p["node"])
            elif rec["kind"] == "freeze":
                self.frozen = p["on"]
            elif rec["kind"] == "nonce":
                self.authn.replay.restore([(p["k"], p["exp"])], self.clock())
        self.logger.log("info", "state.recovered", detail={"wal_records": len(records), "snapshot": snapshot is not None})

    # --------------------------------------------------------------- admin
    def admin(self, credential: str, action: str, **kw: Any) -> dict[str, Any]:
        """Operator controls: freeze/unfreeze, quarantine/release, rollback (MC-049, MC-028)."""
        principal = self.authn.authenticate(credential, mutating=True)
        tenant: str = kw.get("tenant") or ""
        if action in ("freeze", "unfreeze"):
            self.authz.require(principal, auth.ADMIN_FREEZE)
            with self._lock:
                self._persist("freeze", None, {"on": action == "freeze"})
                self.frozen = action == "freeze"
        elif action in ("quarantine", "release"):
            if not tenant:
                raise errors.TopoError(errors.INVALID_REQUEST, "tenant is required")
            self.authz.require(principal, auth.ADMIN_QUARANTINE, tenant)
            with self._lock:
                ts = self._tenant(tenant, create=False)
                node = kw["node"]
                if node not in ts.topo.nodes:
                    raise errors.TopoError(errors.UNKNOWN_NODE, "unknown node")
                self._persist("quarantine", tenant, {"node": node, "on": action == "quarantine"})
                (ts.quarantined.add if action == "quarantine" else ts.quarantined.discard)(node)
                if action == "quarantine":
                    self._revoke_leases(tenant, {node})
        elif action == "rollback_config":
            self.authz.require(principal, auth.CONFIG_ACTIVATE)
            prov = self.config.rollback(to_generation=kw.get("to_generation"), author=principal.subject,
                                        reason=kw.get("reason", "operator"))
            return {"generation": prov.generation, "digest": prov.digest}
        else:
            raise errors.TopoError(errors.INVALID_REQUEST, "unknown admin action")
        assert self.audit is not None
        self.audit.append(f"admin.{action}", ts=self.clock(), subject=principal.subject, role=principal.role,
                          tenant=tenant, target=kw.get("node"), outcome="success", release=self.release["version"])
        self.metrics.inc("inv62_admin_actions", action=action)
        return {"ok": True, "frozen": self.frozen}

    def _revoke_leases(self, tenant: str, holders: set[str]) -> None:
        if not holders:
            return
        for key, lease in list(self.leases._leases.items()):
            if key.startswith(f"{tenant}/") and lease.holder in holders:
                self.leases.revoke(key)

    def _check_holder(self, ts: TenantState, tenant: str, site: str, holder: str) -> None:
        """A lease is only valid while its holder is still an eligible, unquarantined site member."""
        node = ts.topo.nodes.get(holder)
        if node is None or node.site != site or self.cfg["coordinator_capability"] not in node.caps or holder in ts.quarantined:
            self.leases.revoke(f"{tenant}/{site}")
            raise errors.TopoError(errors.STALE_LEADER, "lease holder is no longer an eligible site member")

    def explain(self, credential: str, decision_id: str) -> str:
        principal = self.authn.authenticate(credential, mutating=False)
        self.authz.require(principal, auth.READ_GRAPH)
        d = self.decisions.get(decision_id)
        if d is None or d.tenant not in principal.tenants:  # same answer: no cross-tenant existence oracle
            raise errors.TopoError(errors.INVALID_REQUEST, "unknown decision")
        return policy.explain(d)

    # ------------------------------------------------------ health/readiness
    def health(self) -> dict[str, Any]:
        """Liveness + readiness + status surface (MC-061).  Contains no
        tenant topology, secrets or node names."""
        deps = {
            "config": self._ready,
            "keys": self.keyring.available,
            "policy": self.authz.available,
            "time": self.clock_source.healthy,
            "state_store": self.breaker.state != "open",
            "audit": self.audit is not None,
        }
        gen = self.config.active
        now = self.clock()
        oldest = None
        links_down = 0
        tiers: dict[str, int] = {}
        for ts in self.tenants.values():
            for link in ts.topo.links.values():
                links_down += 0 if link.up else 1
                if link.measured_at is not None:
                    age = now - link.measured_at
                    oldest = age if oldest is None else max(oldest, age)
            for n in ts.topo.nodes.values():
                tiers[n.tier] = tiers.get(n.tier, 0) + 1
        for tier, count in tiers.items():
            self.metrics.set("inv62_nodes", count, tier=tier)
        self.metrics.set("inv62_links_down", links_down)
        ready = all(deps.values())
        self.metrics.set("inv62_ready", 1.0 if ready else 0.0)
        return {
            "live": True,
            "ready": ready,
            "dependencies": deps,
            "mode": (Mode.NOT_READY if not self._ready else Mode.FROZEN if self.frozen else Mode.NORMAL).value,
            "release": self.release,
            "config": None if gen is None else {"generation": gen.provenance.generation, "digest": gen.provenance.digest},
            "tenants": len(self.tenants),
            "links_down": links_down,
            "oldest_measurement_age_s": oldest,
            "circuit": self.breaker.state,
            "in_flight": self.admission.in_flight if self.admission else 0,
            "protocols": {k: list(v) for k, v in wire.SUPPORTED.items()},
        }

    # --------------------------------------------------------------- handle
    def handle(self, raw: bytes) -> bytes:
        t0 = time.perf_counter()
        request_id, family, op, tenant, principal = "unknown", "?", "?", None, None
        span = None
        entered = False
        try:
            req = wire.decode(raw)
            rid = req.get("request_id")
            if isinstance(rid, str) and len(rid) <= 64:
                request_id = rid
            family, version = wire.validate_request(req)
            op, tenant = req["op"], req["tenant"]
            span = self.tracer.start(f"{family}.{op}", req.get("traceparent"))
            if not self._ready or self.admission is None:
                raise errors.TopoError(errors.NOT_READY, "no active configuration", retry_after_ms=1000)
            deadline = Deadline(req.get("deadline_ms", wire.DEFAULT_DEADLINE_MS), self.mono)
            mutating = (family, op) in auth.MUTATING
            principal = self.authn.authenticate(req["credential"], mutating=False)
            target = req["body"].get("candidate") if family == "PK_TOPO_PARTITION" else None
            self.authz.authorize(principal, family, op, tenant, target_node=target)
            self.admission.enter(tenant)  # after authz: an anonymous flood cannot drain a victim tenant's bucket
            entered = True
            if mutating:
                self.authn.spend(principal)
            idem_key = req.get("idempotency_key")
            fp = IdempotencyStore.fingerprint({"f": family, "o": op, "b": req["body"], "s": principal.subject})
            if idem_key:
                cached = self.idempotency.lookup(tenant, idem_key, fp)
                if cached is not None:
                    self.metrics.inc("inv62_idempotent_replays", family=family)
                    return wire.encode(cached)
            short = f"{family.split('_')[-1].lower()}.{op}"
            mode = Mode.FROZEN if self.frozen else Mode.NORMAL
            if short not in lifecycle.ALLOWED[mode]:
                raise errors.TopoError(errors.FROZEN, "automated decisions are frozen", retry_after_ms=5000)
            deadline.check()
            with self._lock:
                result, revision, outcome, extra = self._dispatch(family, op, tenant, req["body"], principal, deadline)
            resp: dict[str, Any] = {"protocol": f"{family}/{version}", "request_id": request_id,
                                    "outcome": outcome.value, "result": result, **extra}
            if revision is not None:
                resp["revision"] = revision
            if span:
                resp["traceparent"] = span.traceparent
            wire.validate_response(resp)
            if idem_key and mutating:
                self.idempotency.store(tenant, idem_key, fp, resp)
            self._observe(family, op, tenant, outcome.value, None, t0, request_id, principal, span, extra)
            return wire.encode(resp)
        except errors.TopoError as exc:
            return self._error(exc, request_id, family, op, tenant, principal, span, t0)
        except Exception as exc:  # defect: never leak internals
            self.logger.log("error", "internal.defect", request_id=request_id, detail={"type": type(exc).__name__})
            return self._error(errors.TopoError(errors.INTERNAL, "internal error"), request_id, family, op, tenant,
                               principal, span, t0)
        finally:
            if entered and self.admission:
                self.admission.leave()
            if principal is not None and (family, op) in auth.MUTATING:
                self._maybe_compact()

    def _error(self, exc: errors.TopoError, request_id: str, family: str, op: str, tenant: str | None,
               principal: auth.Principal | None, span: Any, t0: float) -> bytes:
        resp = {"protocol": family if family != "?" else "PK_TOPO", "request_id": request_id,
                "outcome": exc.outcome.value, "error": exc.to_wire(request_id)}
        if exc.code in (errors.UNAUTHENTICATED.code, errors.REPLAYED.code, errors.FORBIDDEN.code) and self.audit:
            self.audit.append("security.denied", ts=self.clock(), op=f"{family}.{op}", code=exc.code,
                              tenant=tenant, subject=principal.subject if principal else None,
                              request_id=request_id, release=self.release["version"])
        self._observe(family, op, tenant, exc.outcome.value, exc.code, t0, request_id, principal, span, {})
        return wire.encode(resp)

    def _observe(self, family: str, op: str, tenant: str | None, outcome: str, code: str | None, t0: float,
                 request_id: str, principal: Any, span: Any, extra: dict) -> None:
        ms = (time.perf_counter() - t0) * 1000
        self.metrics.inc("inv62_requests", family=family, op=op, outcome=outcome)
        if code:
            self.metrics.inc("inv62_errors", code=code)
        self.metrics.observe("inv62_request_latency_ms", ms, family=family)
        gen = self.config.active
        self.logger.log("info" if code is None else "warning", "request", op=f"{family}.{op}", tenant=tenant,
                        outcome=outcome, code=code, request_id=request_id, duration_ms=round(ms, 4),
                        trace_id=span.trace_id if span else None, span_id=span.span_id if span else None,
                        decision_id=extra.get("decision_id"), mode=extra.get("degraded_mode"),
                        config_generation=gen.provenance.generation if gen else None)
        if span:
            self.tracer.finish(span, outcome=outcome, code=code)

    # ------------------------------------------------------------- dispatch
    def _dispatch(self, family: str, op: str, tenant: str, body: dict, principal: auth.Principal,
                  deadline: Deadline) -> tuple[dict, int | None, errors.Outcome, dict]:
        if family == "PK_TOPO_GRAPH":
            if op == "get":
                ts = self._tenant(tenant, create=False)
                snap = ts.topo.snapshot()
                if not body.get("include_links", True):
                    snap.pop("links")
                snap["quarantined"] = sorted(ts.quarantined)
                return snap, ts.topo.revision, errors.Outcome.SUCCESS, {}
            return self._apply(tenant, body, principal, deadline)
        if family == "PK_TOPO_NEAREST":
            return self._resolve(tenant, body, deadline)
        return self._partition(op, tenant, body, principal)

    def _apply_mutations(self, ts: TenantState, topo: Topology, mutations: list[dict], *, check_time: bool = True) -> None:
        """Apply a batch to ``topo``/``ts`` (both are the caller's private copies).
        Health trackers are copied on first touch so a rejected batch never
        changes live hysteresis state."""
        hp = HealthPolicy.from_config(self.cfg["health"]) if self.cfg else HealthPolicy()
        horizon = self.clock() + auth.CLOCK_SKEW_S
        touched: set[frozenset] = set()
        for m in mutations:
            if check_time:
                for tkey in ("at", "measured_at"):
                    if m.get(tkey) is not None and m[tkey] > horizon:
                        raise TopologyError(f"{tkey} is in the future beyond the {auth.CLOCK_SKEW_S}s skew allowance")
            k = m["kind"]
            if k == "add_node":
                topo.add(m["node"], m["tier"], m.get("site"), m.get("caps", []), parent=m.get("parent"),
                         residency=m.get("residency"))
            elif k == "remove_node":
                topo.remove(m["node"])
                ts.quarantined.discard(m["node"])
                for hk in [hk for hk in ts.health if m["node"] in hk]:
                    del ts.health[hk]
            elif k == "connect":
                topo.connect(m["a"], m["b"], m["latency_ms"], m.get("up", True), measured_at=m.get("measured_at"))
            elif k == "disconnect":
                topo.disconnect(m["a"], m["b"])
                ts.health.pop(frozenset((m["a"], m["b"])), None)
            elif k == "set_link_state":
                topo.set_link_state(m["a"], m["b"], m["up"], measured_at=m.get("measured_at"))
            elif k == "probe":
                key = frozenset((m["a"], m["b"]))
                link = topo.links.get(key)
                if link is None:
                    raise TopologyError(f"link {m['a']!r}<->{m['b']!r} is not registered")
                lh = ts.health.get(key)
                if lh is not None and key not in touched:
                    lh = ts.health[key] = lh.copy()
                touched.add(key)
                if lh is None:
                    # seed the tracker from the link's current state so hysteresis starts from reality
                    lh = ts.health[key] = LinkHealth(hp)
                    lh.machine.to(LinkState.UP if link.up else LinkState.DOWN, "seeded from registered link")
                lh.probe(m["ok"], m["at"], m.get("latency_ms"))
                latency = m.get("latency_ms", link.latency_ms) if m["ok"] else link.latency_ms
                topo.connect(m["a"], m["b"], latency if latency is not None else link.latency_ms,
                             lh.routable(), measured_at=m["at"] if m["ok"] else link.measured_at)

    def _apply(self, tenant: str, body: dict, principal: auth.Principal, deadline: Deadline):
        ts = self._tenant(tenant, create=True)
        expected = body.get("expected_revision")
        if expected is not None and expected != ts.topo.revision:
            raise errors.TopoError(errors.CONFLICT, "graph revision changed",
                                   {"expected": expected, "actual": ts.topo.revision})
        candidate = ts.topo.clone()
        shadow = TenantState(candidate, dict(ts.health), set(ts.quarantined), ts.sites)
        try:
            self._apply_mutations(shadow, candidate, body["mutations"])
        except CapacityExceeded as exc:
            raise errors.TopoError(errors.QUOTA_EXCEEDED, str(exc)) from None
        except UnknownNode as exc:
            raise errors.TopoError(errors.UNKNOWN_NODE, exc.args[0] if exc.args else "unknown node") from None
        except TopologyError as exc:
            raise errors.TopoError(errors.INVALID_TOPOLOGY, str(exc)) from None
        deadline.check()  # abort before commit: nothing persisted, nothing swapped
        self._persist("apply", tenant, {"mutations": body["mutations"], "revision": candidate.revision})
        removed = set(ts.topo.nodes) - set(candidate.nodes)
        ts.topo, ts.health, ts.quarantined = candidate, shadow.health, shadow.quarantined
        self._revoke_leases(tenant, removed)
        assert self.audit is not None
        self.audit.append("graph.applied", ts=self.clock(), subject=principal.subject, role=principal.role,
                          tenant=tenant, revision=candidate.revision, outcome="success",
                          release=self.release["version"])
        return ({"applied": len(body["mutations"]), "nodes": len(candidate.nodes), "links": len(candidate.links)},
                candidate.revision, errors.Outcome.SUCCESS, {})

    def _resolve(self, tenant: str, body: dict, deadline: Deadline):
        ts = self._tenant(tenant, create=False)
        topo = ts.topo
        if body["origin"] not in topo.nodes:
            raise errors.TopoError(errors.UNKNOWN_NODE, "origin is not registered")
        c = body.get("constraints", {})
        req = policy.ResolveRequest(body["origin"], body["capability"], c.get("residency"), c.get("max_latency_ms"),
                                    c.get("exclude", []), c.get("same_site_only", False), c.get("prefer", "latency"))
        pol = self.cfg["policy"]
        res = policy.resolve(topo, req, quarantined=ts.quarantined, now=self.clock(),
                             stale_after_s=self.cfg["health"]["stale_after_s"],
                             stale_behaviour=pol["stale_link_behaviour"], residency_required=pol["residency_required"],
                             allow_cross_site_failover=pol["allow_cross_site_failover"], limit=wire.MAX_CANDIDATES)
        deadline.check()
        mode = Mode.NORMAL
        origin_site = topo.nodes[req.origin].site
        cloud = self.cfg["cloud_node"]
        if origin_site and self._site_partitioned(ts, origin_site, cloud):
            mode = Mode.PARTITIONED_LOCAL
        elif res.stale_used:
            mode = Mode.STALE_DATA
        outcome = errors.Outcome.SUCCESS if res.node and mode is Mode.NORMAL else errors.Outcome.DEGRADED
        gen = self.config.active
        dec = policy.Decision(self.decisions.new_id(), tenant, "nearest.resolve",
                              {"origin": req.origin, "capability": req.capability, "constraints": c},
                              topo.revision, gen.provenance.generation if gen else None, self.release["artifact_digest"],
                              res.considered, res.node, res.latency_ms,
                              outcome.value if res.node else errors.Outcome.TERMINAL.value, mode.value, self.clock())
        self.decisions.put(dec)
        if res.node is None:
            raise errors.TopoError(errors.NO_CAPABLE_NODE, "no reachable node satisfies capability and policy",
                                   {"decision_id": dec.decision_id,
                                    "rejected": len([r for r in res.considered if r["verdict"] == "rejected"])})
        result: dict[str, Any] = {"node": res.node, "latency_ms": res.latency_ms}
        if body.get("explain"):
            result["considered"] = res.considered
        extra = {"decision_id": dec.decision_id}
        if mode is not Mode.NORMAL:
            extra["degraded_mode"] = mode.value
        return result, topo.revision, outcome, extra

    def _partitioned_sites(self, ts: TenantState, cloud: str) -> frozenset[str]:
        """Sites with no member reachable from the designated cloud, cached per
        graph revision so the read path does not re-walk the graph (MC-056)."""
        cached = ts.reach_cache
        if cached is None or cached[0] != ts.topo.revision or cached[1] != cloud:
            node = ts.topo.nodes.get(cloud)
            if node is None or node.tier != "cloud":
                part: frozenset[str] = frozenset()
            else:
                reach = {n for _, n in ts.topo.iter_by_distance(cloud)}
                live = {ts.topo.nodes[n].site for n in reach}
                part = frozenset(set(ts.topo.sites()) - live)
            cached = ts.reach_cache = (ts.topo.revision, cloud, part)
        return cached[2]

    def _site_partitioned(self, ts: TenantState, site: str, cloud: str) -> bool:
        return site in self._partitioned_sites(ts, cloud)

    def _site_machine(self, ts: TenantState, site: str) -> Machine:
        m = ts.sites.get(site)
        if m is None:
            m = ts.sites[site] = Machine(SiteState.CONNECTED, SITE_TRANSITIONS)
        return m

    def _partition(self, op: str, tenant: str, body: dict, principal: auth.Principal):
        ts = self._tenant(tenant, create=False)
        topo = ts.topo
        site = body["site"]
        key = f"{tenant}/{site}"
        now = self.clock()
        cap = self.cfg["coordinator_capability"]
        try:
            if op == "status":
                cloud = body.get("cloud", self.cfg["cloud_node"])
                part = topo.partitioned(site, cloud)
                m = self._site_machine(ts, site)
                if part and m.state in (SiteState.CONNECTED, SiteState.SUSPECT, SiteState.RECOVERING):
                    m.to(SiteState.PARTITIONED, "designated cloud unreachable from every member")
                    self.metrics.inc("inv62_partitions")
                elif not part and m.state is SiteState.PARTITIONED:
                    m.to(SiteState.RECOVERING, "cloud reachable again")
                    self.leases.revoke(key)  # reconciliation: site-local authority ends, term fences it
                    m.to(SiteState.CONNECTED, "site lease revoked; coordination returned to cloud")
                try:
                    preferred = topo.elect(site, cap)
                except NoCoordinatorCandidate:
                    preferred = None
                lease = self.leases.current(key, now)
                return ({"site": site, "partitioned": part, "state": m.state.value,
                         "coordinator": lease.as_dict() if lease else None, "term": self.leases.term(key),
                         "preferred_candidate": preferred, "mode": Mode.PARTITIONED_LOCAL.value if part else Mode.NORMAL.value},
                        topo.revision, errors.Outcome.DEGRADED if part else errors.Outcome.SUCCESS, {})
            if op == "acquire":
                before = self.leases.term(key)
                lease = self.leases.acquire(topo, key, site, body["candidate"], now, capability=cap,
                                            excluded=ts.quarantined)
                if lease.term != before:
                    self.metrics.inc("inv62_local_elections")
                    assert self.audit is not None
                    self.audit.append("election.granted", ts=now, subject=principal.subject, tenant=tenant,
                                      target=body["candidate"], term=lease.term, release=self.release["version"])
                return {**lease.as_dict(), "site": site}, topo.revision, errors.Outcome.SUCCESS, {}
            if op == "renew":
                self._check_holder(ts, tenant, site, body["candidate"])
                lease = self.leases.renew(key, body["candidate"], body["fencing_token"], now)
                return {**lease.as_dict(), "site": site}, topo.revision, errors.Outcome.SUCCESS, {}
            lease = self.leases.validate_token(key, body["fencing_token"], now)
            self._check_holder(ts, tenant, site, lease.holder)
            return {"valid": True, "holder": lease.holder, "term": lease.term}, topo.revision, errors.Outcome.SUCCESS, {}
        except UnknownSite:
            raise errors.TopoError(errors.UNKNOWN_SITE, "site has no members") from None
        except UnknownNode:
            raise errors.TopoError(errors.UNKNOWN_NODE, "unknown cloud node") from None
        except TopologyError as exc:
            raise errors.TopoError(errors.INVALID_TOPOLOGY, str(exc)) from None
