"""Production supervisor controller for GAP-01 (v5.0.0).

Wraps the dependency-free :class:`supervisor.NodeSupervisor` lifecycle model
with every production concern named in the missing-components checklist.
Request pipeline (order matters, each step fails closed)::

    size/shape -> disabled? -> authenticate (sig, skew, nonce) -> rate limit
      -> idempotency lookup -> authorize -> safety gates (emergency/partition/
      pressure) -> [lock] WAL append -> apply -> checkpoint -> audit
      -> completion record -> metrics/logs/trace

Implements components 5, 10, 12, 13, 14, 15, 20, 21, 22, 30, 34, 35, 40 and
integrates 3, 4, 7, 8, 9, 11, 24, 25, 26, 31-33, 36.
"""
from __future__ import annotations

import json
import logging
import pathlib
import socket
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable

from . import inventory
from .config import SupervisorConfig
from .errors import SupervisorError, wrap
from .health import HealthRegistry
from .observability import Metrics, SLOTracker, Tracer, get_logger, log_event, redact
from .runtime import RuntimeManager, WorkloadSpec
from .security import Authenticator, AuthorizationPolicy, RateLimiter
from .store import AuditLog, StateStore
from .supervisor import DRAIN_ORDER, TRANSITIONS, NodeSupervisor

REQUEST_SCHEMA = "PK_NODE_LIFECYCLE/1"
PARTITION_STATES = ("connected", "suspect", "partitioned", "autonomy-expired")

# Operations permitted in degraded modes (20, 30)
PARTITION_ALLOWED = {"status", "diagnostics", "report_health", "cordon", "drain", "terminate",
                     "drain_override", "emergency_enter", "emergency_exit", "disable",
                     "control_plane_heartbeat", "cordon_ack", "transition", "reload_config"}
EMERGENCY_ALLOWED = {"status", "diagnostics", "report_health", "cordon", "drain", "terminate",
                     "drain_override", "emergency_exit", "disable", "control_plane_heartbeat",
                     "cordon_ack"}
PRESSURE_BLOCKED = {"admit", "uncordon"}
READ_ONLY = {"status", "diagnostics"}


class MonotonicClock:
    """Integer-second monotonic clock; wall time is used only for request
    freshness checks and audit timestamps."""

    def __init__(self) -> None:
        self._t0 = time.monotonic()

    def now(self) -> int:
        return int(time.monotonic() - self._t0)

    @staticmethod
    def wall() -> float:
        return time.time()


@dataclass
class ManualClock:
    t: int = 0
    w: float = 1_800_000_000.0

    def now(self) -> int:
        return self.t

    def wall(self) -> float:
        return self.w + self.t

    def advance(self, s: int) -> None:
        self.t += s


@dataclass
class DrainIntent:
    requested_at: int
    deadline: int
    kill_after: int
    reason: str
    breaches: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class SupervisorController:
    def __init__(self, node: str, state_dir: str | os.PathLike, *,
                 config: SupervisorConfig | None = None,
                 runtime: RuntimeManager,
                 authenticator: Authenticator,
                 policy: AuthorizationPolicy,
                 health: HealthRegistry | None = None,
                 clock: Any = None,
                 logger: logging.Logger | None = None,
                 fsync: bool = True,
                 pressure_probe: Callable[[], dict] | None = None) -> None:
        self.cfg = config or SupervisorConfig()
        self.clock = clock or MonotonicClock()
        self.dir = pathlib.Path(state_dir)
        self.store = StateStore(self.dir, replay_window=self.cfg.replay_window, fsync=fsync)
        self.audit = AuditLog(self.dir / "audit.jsonl", retention=self.cfg.audit_retention, fsync=fsync)
        self.runtime = runtime
        self.authn = authenticator
        self.policy = policy
        self.health = health or HealthRegistry(max_signals=self.cfg.max_health_signals)
        self.limiter = RateLimiter(self.cfg.rate_per_second, self.cfg.rate_burst, self.cfg.max_queue_depth)
        self.metrics = Metrics()
        self.tracer = Tracer()
        self.slo = SLOTracker()
        self.log = logger or get_logger()
        self.pressure_probe = pressure_probe or (lambda: inventory.pressure(
            self.cfg.memory_pressure_pct, self.cfg.disk_pressure_pct, str(self.dir)))
        self.lock = threading.RLock()  # single serialization point (14)
        self.sup = NodeSupervisor(node)
        self.drain_intent: DrainIntent | None = None
        self.cordon: dict | None = None          # {generation, at, acked_at}
        self.emergency: dict | None = None       # {reason, at, by}
        self.partition = "connected"
        self.last_cp_heartbeat = self.clock.now()
        self.partition_since: int | None = None
        self.pressure: dict = {"under_pressure": False, "reasons": []}
        self.last_beat = self.clock.now()
        self.started = False
        self.recovery_report: dict = {}

    # ------------------------------------------------------------ state I/O
    @property
    def disabled(self) -> bool:
        return (self.dir / "DISABLED").exists()

    def _snapshot(self) -> dict:
        return {
            "node": self.sup.node, "state": self.sup.state, "workloads": dict(self.sup.workloads),
            "last_reason": self.sup.last_reason, "breaches": list(self.sup.breaches),
            "clock": self.sup.clock,
            "drain_intent": self.drain_intent.to_dict() if self.drain_intent else None,
            "cordon_ack": self.cordon, "emergency": self.emergency,
            "placements": dict(self.runtime.placements),
        }

    def _restore(self, body: dict) -> None:
        if body.get("node") != self.sup.node:
            raise SupervisorError("E_STATE_CORRUPT", "persisted node identity mismatch")
        self.sup = NodeSupervisor(body["node"], state=body["state"], workloads=dict(body["workloads"]),
                                  last_reason=body.get("last_reason", "restored"),
                                  breaches=list(body.get("breaches", [])), clock=0)
        di = body.get("drain_intent")
        self.drain_intent = DrainIntent(**di) if di else None
        self.cordon = body.get("cordon_ack")
        self.emergency = body.get("emergency")
        self.runtime.placements.update(body.get("placements", {}))

    # -------------------------------------------- crash reconciliation (5)
    def start(self) -> dict:
        """Recover persisted intent, replay WAL, reconcile against runtimes."""
        with self.lock:
            body, journal = self.store.load()
            if body:
                self._restore(body)
            replayed = 0
            for entry in journal:
                try:
                    self._apply(entry["op"], entry["args"], entry["caller"], replay=True)
                    replayed += 1
                except Exception as exc:  # noqa: BLE001 -- op rejected originally or now moot
                    # A WAL entry that cannot re-apply leaves state unchanged (fail closed).
                    self.store.recovery_notes.append(f"wal entry {entry.get('op')} not re-applied: "
                                                     f"{getattr(exc, 'code', type(exc).__name__)}")
            observed = self.runtime.observed()
            intended = set(self.sup.workloads)
            orphans = sorted(set(observed) - intended)      # running, not admitted
            lost = sorted(intended - set(observed))         # admitted, not running
            for name in orphans:  # fail closed: unknown workloads are terminated
                if name not in self.runtime.placements:
                    self.runtime.placements[name] = observed[name]
                self.runtime.terminate(name, grace_s=0, force=True)
            for name in lost:
                del self.sup.workloads[name]
                self.runtime.placements.pop(name, None)
            # A node recovering mid-flight never comes back placement-ready by itself.
            if self.sup.state == "ready":
                self.sup.state = "cordoned"
                self.sup.last_reason = "restart: re-establish health before uncordon"
                self.cordon = {"generation": self.store.generation + 1, "at": self.clock.now(),
                               "acked_at": None, "reason": "restart"}
            self.metrics.inc("reconcile_orphans_terminated", len(orphans))
            self.metrics.inc("reconcile_lost_workloads", len(lost))
            from . import __version__
            self.metrics.set("build_info", 1, version=__version__)
            self.recovery_report = {"version": __version__, "replayed": replayed,
                                    "orphans_terminated": orphans,
                                    "lost_workloads": lost, "notes": list(self.store.recovery_notes),
                                    "state": self.sup.state}
            self.store.checkpoint(self._snapshot())
            self.audit.append({"event": "start", "wall": self.clock.wall(), **self.recovery_report})
            log_event(self.log, "GAP01-START", "supervisor recovered", **self.recovery_report)
            self.started = True
            self.last_cp_heartbeat = self.clock.now()
            return self.recovery_report

    # ---------------------------------------------------------- pipeline
    def handle(self, raw: bytes | dict) -> dict:
        t0 = time.perf_counter()
        op, outcome, code = "other", "error", "none"
        req: dict = {}
        parse_error: Exception | None = None
        try:
            req = self._parse(raw)
        except Exception as exc:  # noqa: BLE001 -- reported inside the span below
            parse_error = exc
        with self.tracer.span("gap01.handle", traceparent=req.get("traceparent")) as sp:
            try:
                if parse_error is not None:
                    raise parse_error
                op = req["op"]
                sp["attrs"]["op"] = op
                if self.disabled and op != "status":
                    raise SupervisorError("E_DISABLED", "component disabled")
                now_w = self.clock.wall()
                caller = self.authn.authenticate(req, now_w)
                self.limiter.acquire(f"{caller}:{'read' if op in READ_ONLY else 'mutate'}", now_w)
                try:
                    key = f"{caller}:{req['request_id']}"
                    prior = self.store.completed(key)
                    if prior is not None:
                        outcome = "replayed"
                        return {**prior, "replayed": True}
                    self.policy.check(caller, op, now_w)
                    with self.lock:
                        self._gate(op)
                        if op not in READ_ONLY:
                            self.store.append_journal({"op": op, "args": req["args"], "caller": caller,
                                                       "request_id": req["request_id"]})
                        with self.tracer.span(f"gap01.apply.{op}"):
                            result = self._apply(op, req["args"], caller)
                        resp = {"ok": True, "request_id": req["request_id"], "result": result,
                                "generation": self.store.generation}
                        if op not in READ_ONLY:
                            try:
                                with self.tracer.span("gap01.persist.checkpoint"):
                                    resp["generation"] = self.store.checkpoint(self._snapshot())
                            except SupervisorError:
                                # Applied in memory but not durable: contain by failing safe.
                                self.enter_emergency("persistence failure after apply")
                                raise
                            self.audit.append({"event": op, "caller": caller, "request_id": req["request_id"],
                                               "args": redact(req["args"]), "wall": now_w,
                                               "state": self.sup.state, "generation": resp["generation"],
                                               "trace_id": sp["trace_id"]})
                            self.store.record_completion(key, resp)
                    outcome = "ok"
                    return resp
                finally:
                    self.limiter.release()
            except Exception as exc:  # noqa: BLE001 -- converted to structured error
                err = wrap(exc)
                code = err.code
                if err.code in ("E_FORBIDDEN", "E_UNAUTHENTICATED", "E_REPLAY"):
                    self.audit.append({"event": "denied", "op": op, "caller": req.get("caller"),
                                       "code": err.code, "wall": self.clock.wall()})
                log_event(self.log, "GAP01-REQ-ERR", "request rejected", logging.WARNING,
                          op=op, code=err.code, request_id=req.get("request_id"),
                          trace_id=sp["trace_id"])
                return {"ok": False, "request_id": req.get("request_id"), "error": err.to_dict()}
            finally:
                self.metrics.inc("requests", op=op, outcome=outcome, code=code)
                self.metrics.observe("request_seconds", time.perf_counter() - t0, op=op)
                self.metrics.set("state", 1, state=self.sup.state)
                self.metrics.set("resident_workloads", len(self.sup.workloads))
                self.metrics.set("in_flight_requests", self.limiter.in_flight)

    def _parse(self, raw: bytes | dict) -> dict:
        if isinstance(raw, (bytes, bytearray)):
            if len(raw) > self.cfg.max_request_bytes:
                raise SupervisorError("E_BAD_REQUEST", "request too large")
            try:
                raw = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                raise SupervisorError("E_BAD_REQUEST", "request is not JSON") from None
        from .schemas import validate
        if not isinstance(raw, dict):
            raise SupervisorError("E_BAD_REQUEST", "request must be a JSON object")
        problems = validate("request", raw)
        if problems:
            raise SupervisorError("E_BAD_REQUEST", "; ".join(problems[:5]))
        return raw

    def _gate(self, op: str) -> None:
        if self.emergency and op not in EMERGENCY_ALLOWED:
            raise SupervisorError("E_EMERGENCY", f"{op} refused in emergency mode")
        if self.partition in ("partitioned", "autonomy-expired") and op not in PARTITION_ALLOWED:
            raise SupervisorError("E_PARTITIONED", f"{op} refused while {self.partition}")
        if self.pressure.get("under_pressure") and op in PRESSURE_BLOCKED:
            raise SupervisorError("E_CAPACITY", "resource pressure: " + ", ".join(self.pressure["reasons"]))

    # -------------------------------------------------------- operations
    def _sync_health(self, now: int) -> dict:
        ev = self.health.evaluate(now)
        if now >= self.sup.clock:
            self.sup.clock = now
        self.sup.health = {"aggregate": now} if ev["healthy"] else {}
        return ev

    def _transition(self, to: str, reason: str) -> None:
        frm = self.sup.state
        legal = to in TRANSITIONS.get(frm, ())
        self.sup.transition(to, reason=reason)
        if frm == "draining" and to != "draining":
            self.drain_intent = None  # leaving draining cancels the drain intent
        self.slo.record_transition(frm, to, legal, len(self.sup.workloads))
        log_event(self.log, "GAP01-TRANSITION", "lifecycle transition", frm=frm, to=to, reason=reason)

    def _apply(self, op: str, a: dict, caller: str, replay: bool = False) -> dict:
        now = self.clock.now()
        if op == "status":
            return self.status()
        if op == "diagnostics":
            return self.diagnostics()
        if op == "transition":
            to = a["to"]
            if to == "ready":
                if not self._sync_health(now)["healthy"]:
                    raise SupervisorError("E_NOT_ACCEPTING", "cannot become ready without healthy evidence")
            if to == "draining":
                return self._start_drain(a, now)
            self._transition(to, a.get("reason", ""))
            if to == "cordoned":
                self._new_cordon(now, a.get("reason", "transition"))
            return {"state": self.sup.state}
        if op == "cordon":
            self._transition("cordoned", a.get("reason", "cordon"))
            return {"state": self.sup.state, "cordon": self._new_cordon(now, a.get("reason", "cordon"))}
        if op == "uncordon":
            if not self._sync_health(now)["healthy"]:
                raise SupervisorError("E_NOT_ACCEPTING", "uncordon requires healthy evidence")
            self._transition("ready", a.get("reason", "uncordon"))
            self.cordon = None
            return {"state": self.sup.state}
        if op == "cordon_ack":
            if not self.cordon or a["generation"] != self.cordon["generation"]:
                raise SupervisorError("E_BAD_REQUEST", "ack does not match current cordon generation")
            self.cordon["acked_at"] = now
            self.cordon["acked_by"] = caller
            self.slo.record_cordon_placement(late=(now - self.cordon["at"]) > self.cfg.cordon_ack_timeout_s)
            return {"cordon": self.cordon}
        if op == "report_health":
            self.health.report(a["signal"], a["ok"], now, caller)
            return self._sync_health(now)
        if op == "admit":
            if len(self.sup.workloads) >= self.cfg.max_workloads:
                raise SupervisorError("E_CAPACITY", "max_workloads reached")
            self._sync_health(now)
            spec = WorkloadSpec(a["workload"], a["trust_class"], a.get("kind", "process"),
                                a.get("image", ""), tuple(a.get("argv", ())), a.get("memory_mb", 64))
            if a["trust_class"] not in DRAIN_ORDER:
                raise SupervisorError("E_BAD_REQUEST", "unknown trust class")
            if replay:
                # Replay restores intent only; reconciliation decides reality.
                self.sup.workloads[spec.name] = spec.trust_class
                self.runtime.placements.setdefault(spec.name, spec.kind)
                return {"admitted": spec.name}
            self.sup.admit(spec.name, spec.trust_class)
            try:
                handle = self.runtime.launch(spec)
            except Exception:
                del self.sup.workloads[spec.name]
                raise
            return {"admitted": spec.name, "handle": handle}
        if op == "terminate":
            return self._terminate(a["workload"], force=a.get("force", False))
        if op == "drain":
            return self._start_drain(a, now)
        if op == "drain_override":
            if not self.drain_intent:
                raise SupervisorError("E_BAD_REQUEST", "no drain in progress")
            if "extend_s" in a:
                self.drain_intent.deadline += int(a["extend_s"])
            if a.get("force_now"):
                self.drain_intent.kill_after = 0
                self.drain_intent.deadline = min(self.drain_intent.deadline, now)
            self.audit.append({"event": "drain_override", "by": caller, "args": a, "wall": self.clock.wall()})
            return self.drain_tick(now) if not replay else {}
        if op == "emergency_enter":
            return self.enter_emergency(a.get("reason", "operator"), by=caller)
        if op == "emergency_exit":
            self.emergency = None
            return {"emergency": None, "state": self.sup.state}
        if op == "disable":
            (self.dir / "DISABLED").write_text(json.dumps({"by": caller, "reason": a.get("reason", ""),
                                                           "wall": self.clock.wall()}))
            if self.sup.state == "ready":
                self._transition("cordoned", "emergency-disable")
            return {"disabled": True}
        if op == "reload_config":
            self.cfg = self.cfg.hot_reload(a["changes"])
            self.limiter.rate, self.limiter.burst = self.cfg.rate_per_second, self.cfg.rate_burst
            return {"config": self.cfg.to_dict()}
        if op == "control_plane_heartbeat":
            self.last_cp_heartbeat = now
            prev = self.partition
            self.partition, self.partition_since = "connected", None
            return {"partition": self.partition, "was": prev}
        raise SupervisorError("E_BAD_REQUEST", f"unknown op {op!r}")

    def _new_cordon(self, now: int, reason: str) -> dict:
        self.cordon = {"generation": self.store.generation + 1, "at": now, "acked_at": None,
                       "reason": reason}
        return self.cordon

    def _terminate(self, name: str, *, force: bool) -> dict:
        if name not in self.sup.workloads:
            raise SupervisorError("E_UNKNOWN_WORKLOAD", name)
        proof = self.runtime.terminate(name, grace_s=0 if force else min(2, self.cfg.drain_grace_s),
                                       force=force)
        if proof.proven:
            del self.sup.workloads[name]
            return {"terminated": name, "proof": proof.evidence}
        raise SupervisorError("E_ISOLATION_UNPROVEN", f"{name}: terminated={proof.terminated} "
                              f"released={proof.resources_released}")

    # ------------------------------------------- drain scheduler (13)
    def _start_drain(self, a: dict, now: int) -> dict:
        if self.sup.state == "stopped":
            raise SupervisorError("E_ILLEGAL_TRANSITION", "cannot drain a stopped node")
        deadline = now + int(a.get("timeout_s", self.cfg.drain_grace_s))
        if self.sup.state != "draining":
            self._transition("draining", a.get("reason", "drain requested"))
        if not self.drain_intent:
            self.drain_intent = DrainIntent(now, deadline, self.cfg.drain_kill_after_s,
                                            a.get("reason", "drain"))
        return self.drain_tick(now)

    def drain_tick(self, now: int | None = None) -> dict:
        now = self.clock.now() if now is None else now
        di = self.drain_intent
        if di is None or self.sup.state != "draining":
            return {"schema": "PK_DRAIN/1", "active": False}
        force = now >= di.deadline + di.kill_after
        released, remaining, unproven = [], [], []
        for w in self.sup.drain_order():
            # Non-blocking: signal and move on; the deadline scheduler owns the grace period.
            proof = self.runtime.terminate(w, grace_s=0, force=force)
            if proof.proven:
                del self.sup.workloads[w]
                released.append(w)
            else:
                remaining.append(w)
                if proof.terminated:
                    unproven.append(w)
        result = {"schema": "PK_DRAIN/1", "node": self.sup.node, "active": True,
                  "complete": False, "released": released, "remaining": remaining,
                  "unproven_reclaim": unproven, "deadline": di.deadline,
                  "kill_after": di.deadline + di.kill_after, "observed_at": now,
                  "forced": force, "escalation": None}
        if remaining:
            if now > di.deadline:
                breach = {"at": now, "deadline": di.deadline, "workloads": remaining}
                if not self.sup.breaches or self.sup.breaches[-1] != breach:
                    self.sup.breaches.append(breach)
                    self.metrics.inc("drain_deadline_breaches")
                result["escalation"] = ("force-kill failed; operator action required" if force
                                        else "deadline exceeded; force-kill at kill_after")
            return result
        self._transition("stopped", "drain complete")
        self.drain_intent = None
        result["complete"] = True
        return result

    # --------------------------------- emergency (30) / partition (20,21)
    def enter_emergency(self, reason: str, by: str = "supervisor") -> dict:
        if not self.emergency:
            self.emergency = {"reason": reason, "at": self.clock.now(), "by": by}
            if self.sup.state == "ready":
                self._transition("cordoned", f"emergency: {reason}")
                self._new_cordon(self.clock.now(), "emergency")
            self.metrics.inc("emergency_entries")
            log_event(self.log, "GAP01-EMERGENCY", "fail-safe emergency mode", logging.ERROR,
                      reason=reason, by=by)
        return {"emergency": self.emergency, "state": self.sup.state}

    def tick(self) -> dict:
        """Periodic control loop: heartbeat, partition machine, pressure, drain."""
        with self.lock:
            now = self.clock.now()
            self.last_beat = now
            silent = now - self.last_cp_heartbeat
            prev = self.partition
            if silent <= self.cfg.partition_lease_s // 2:
                self.partition = "connected"
            elif silent <= self.cfg.partition_lease_s:
                self.partition = "suspect"
            elif silent <= self.cfg.partition_lease_s + self.cfg.partition_max_autonomy_s:
                self.partition = "partitioned"
            else:
                self.partition = "autonomy-expired"
            if self.partition != prev:
                self.partition_since = now if self.partition != "connected" else None
                log_event(self.log, "GAP01-PARTITION", "partition state change", frm=prev, to=self.partition)
                self.audit.append({"event": "partition", "from": prev, "to": self.partition,
                                   "wall": self.clock.wall()})
            if self.partition == "autonomy-expired" and not self.emergency:
                self.enter_emergency("control-plane autonomy window expired")
            try:
                self.pressure = self.pressure_probe()
            except Exception:  # noqa: BLE001
                self.pressure = {"under_pressure": True, "reasons": ["pressure probe failed"]}
            self.metrics.set("under_pressure", 1 if self.pressure.get("under_pressure") else 0)
            if self.cordon and not self.cordon.get("acked_at") and \
                    now - self.cordon["at"] > self.cfg.cordon_ack_timeout_s:
                self.metrics.inc("cordon_ack_overdue")
            ev = self._sync_health(now)
            drain = self.drain_tick(now) if self.drain_intent else None
            if self.store.generation and (drain and (drain.get("released") or drain.get("complete"))):
                self.store.checkpoint(self._snapshot())
            return {"partition": self.partition, "healthy": ev["healthy"], "drain": drain}

    # ------------------------------------------ readiness/liveness (34)
    def liveness(self, now: int | None = None) -> dict:
        now = self.clock.now() if now is None else now
        stalled = now - self.last_beat > self.cfg.watchdog_timeout_s
        return {"live": self.started and not stalled, "last_beat": self.last_beat, "now": now}

    def readiness(self) -> dict:
        ev = self.health.evaluate(self.clock.now())
        ready = (self.started and not self.disabled and not self.emergency
                 and self.sup.state == "ready" and ev["healthy"]
                 and self.partition in ("connected", "suspect")
                 and not self.pressure.get("under_pressure"))
        return {"ready": ready, "state": self.sup.state, "healthy": ev["healthy"],
                "partition": self.partition, "emergency": bool(self.emergency),
                "disabled": self.disabled}

    def status(self) -> dict:
        return {"schema": "PK_NODE_LIFECYCLE/1", "node": self.sup.node, "state": self.sup.state,
                "last_reason": self.sup.last_reason, "workloads": dict(self.sup.workloads),
                "health": self.health.evaluate(self.clock.now()), "partition": self.partition,
                "emergency": self.emergency, "cordon": self.cordon, "disabled": self.disabled,
                "drain": self.drain_intent.to_dict() if self.drain_intent else None,
                "generation": self.store.generation}

    # --------------------------------------------- diagnostics (35)
    def diagnostics(self) -> dict:
        return redact({
            "schema": "GAP01_DIAG/1", "status": self.status(), "config": self.cfg.to_dict(),
            "config_provenance": self.cfg.provenance, "recovery": self.recovery_report,
            "breaches": self.sup.breaches[-20:], "slo": self.slo.report(),
            "audit_head": self.audit.head, "audit_count": self.audit.count,
            "recent_spans": list(self.tracer.spans)[-20:], "pressure": self.pressure,
            "inventory": inventory.snapshot((str(self.dir),)),
            "runtime_observed": self.runtime.observed(),
        })


# ------------------------------------------------ watchdog (10)
def sd_notify(msg: str) -> bool:
    """systemd notify protocol (READY=1, WATCHDOG=1, STOPPING=1)."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr or not hasattr(socket, "AF_UNIX"):
        return False
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.connect(addr)
        s.sendall(msg.encode())
    return True


class Watchdog(threading.Thread):
    """Self-supervision: pets systemd only while the control loop is making
    progress; if the loop hangs past ``timeout`` it enters emergency mode and
    (optionally) exits so the service manager restarts the process."""

    def __init__(self, ctl: SupervisorController, *, interval: float = 1.0,
                 exit_on_hang: bool = False) -> None:
        super().__init__(daemon=True, name="gap01-watchdog")
        self.ctl, self.interval, self.exit_on_hang = ctl, interval, exit_on_hang
        self.stop_event = threading.Event()
        self.hangs = 0

    def check_once(self) -> bool:
        live = self.ctl.liveness()["live"]
        if live:
            sd_notify("WATCHDOG=1")
        else:
            self.hangs += 1
            self.ctl.metrics.inc("watchdog_hangs")
            if self.ctl.lock.acquire(timeout=1):
                try:
                    self.ctl.enter_emergency("watchdog: control loop stalled")
                finally:
                    self.ctl.lock.release()
            if self.exit_on_hang:
                os._exit(70)
        return live

    def run(self) -> None:
        while not self.stop_event.wait(self.interval):
            self.check_once()
