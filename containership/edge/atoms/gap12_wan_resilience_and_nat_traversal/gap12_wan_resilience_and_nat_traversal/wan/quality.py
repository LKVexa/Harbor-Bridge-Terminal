"""Path quality, selection and session lifecycle (G12-C028..C042).

* ``AttemptRunner`` — hard per-strategy deadline and cancellation scope around
  an adapter call.  The adapter runs in a worker thread; at the deadline the
  runner sets the cancel event, invokes the adapter's ``cleanup`` hook, and
  returns ``CANCELLED_DEADLINE`` without waiting for cooperative return.  A
  late completion is recorded (``late``) and its result discarded.  Every
  attempt produces a record: start, deadline, completion, cancellation cause,
  elapsed, cleanup_finished.  Worker count is bounded (``max_workers``).
* ``HealthScheduler`` — probe schedule independent of caller traffic, with
  per-peer jitter and a global probe budget per second.
* ``QualityWindow`` — RTT, loss and RFC 3550 interarrival jitter over a bounded
  rolling window with min-sample / confidence semantics (``unknown`` below the
  minimum), median/p95 robust aggregation, RTT-only (no one-way inference).
* ``bulk_ready`` — separate bulk-transfer readiness decision (sustained
  goodput over a window, not a single small probe).
* ``BandwidthEstimator`` — bounded packet-train estimate that ages to
  ``unknown`` (never zero) and is disabled on metered/restricted links.
* ``PathScorer`` — score from quality + cost + policy inputs with hysteresis,
  hold-down and deterministic tie-break.
* ``KeepalivePolicy``, ``ResumptionTickets``, ``CandidateCache``,
  ``RelayPrewarm``, ``choose_region``, ``RelayQuota``, ``InstrumentedRelay``,
  ``MultipathScheduler`` (P2), ``TrendPredictor`` (P2).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import random
import statistics
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field


# --- C028 hard deadlines ---------------------------------------------------------------------

@dataclass
class AttemptRecord:
    strategy: str
    started: float
    deadline: float
    completed: float | None = None
    outcome: str | None = None
    cancel_cause: str | None = None
    cleanup_finished: bool | None = None
    late: bool = False

    @property
    def elapsed(self) -> float | None:
        return None if self.completed is None else self.completed - self.started


class AttemptRunner:
    def __init__(self, *, max_workers: int = 8, clock=time.monotonic):
        self.clock = clock
        self._slots = threading.BoundedSemaphore(max_workers)
        self.records: deque[AttemptRecord] = deque(maxlen=256)
        self.live_workers = 0
        self._lock = threading.Lock()

    def run(self, strategy: str, fn, *, timeout: float, cleanup=None) -> tuple[bool, AttemptRecord]:
        """``fn(cancel_event) -> truthy``.  Never blocks beyond ``timeout``."""
        if not 0 < timeout <= 120:
            raise ValueError("timeout must be in (0, 120] seconds")
        rec = AttemptRecord(strategy, self.clock(), self.clock() + timeout)
        self.records.append(rec)
        if not self._slots.acquire(blocking=False):
            rec.completed, rec.outcome, rec.cancel_cause = self.clock(), "BUDGET_RATE_LIMITED", "worker-ceiling"
            return False, rec
        cancel = threading.Event()
        box: dict = {}
        done = threading.Event()

        def work():
            with self._lock:
                self.live_workers += 1
            try:
                box["value"] = bool(fn(cancel))
            except Exception as exc:
                box["error"] = type(exc).__name__
            finally:
                with self._lock:
                    self.live_workers -= 1
                if rec.outcome is not None and rec.cancel_cause:
                    rec.late = True
                done.set()
                self._slots.release()

        threading.Thread(target=work, daemon=True, name=f"g12-attempt-{strategy}").start()
        finished = done.wait(timeout)
        rec.completed = self.clock()
        if not finished:
            rec.outcome, rec.cancel_cause = "CANCELLED_DEADLINE", "deadline"
            cancel.set()
            if cleanup is not None:
                try:
                    cleanup()
                    rec.cleanup_finished = True
                except Exception:
                    rec.cleanup_finished = False
            else:
                rec.cleanup_finished = False
            return False, rec
        rec.cleanup_finished = True
        if "error" in box:
            rec.outcome = "DEFECT_EXCEPTION"
            return False, rec
        rec.outcome = "OK" if box.get("value") else "NET_UNREACHABLE"
        return bool(box.get("value")), rec


def bounded_prober(adapters: dict, runner: AttemptRunner, timeouts: dict[str, float]):
    """Wrap per-strategy adapters into the ``prober(strategy)`` the v4.2.0 Path expects,
    so a hung adapter can no longer block escalation (the gap the v4.2.0 audit named)."""
    def prober(strategy: str) -> bool:
        adapter = adapters.get(strategy)
        if adapter is None:
            return False
        ok, _ = runner.run(strategy, adapter.attempt, timeout=timeouts.get(strategy, 3.0),
                           cleanup=getattr(adapter, "cleanup", None))
        return ok
    return prober


# --- C029 health scheduling --------------------------------------------------------------------

@dataclass
class HealthScheduler:
    interval: float = 10.0
    jitter: float = 0.2
    max_probes_per_second: float = 50.0
    seed: int = 0
    due: dict[str, float] = field(default_factory=dict)
    _tokens: float = 0.0
    _last: float | None = None

    def add(self, peer: str, now: float) -> None:
        rng = random.Random(hash((self.seed, peer)))
        self.due[peer] = now + rng.uniform(0, self.interval)       # spread initial probes

    def remove(self, peer: str) -> None:
        self.due.pop(peer, None)

    def ready(self, now: float) -> list[str]:
        if self._last is None:
            self._last = now
        self._tokens = min(self.max_probes_per_second, self._tokens + (now - self._last) * self.max_probes_per_second)
        self._last = now
        out = []
        for peer, t in sorted(self.due.items(), key=lambda kv: kv[1]):
            if t > now or self._tokens < 1:
                break
            self._tokens -= 1
            out.append(peer)
            rng = random.Random(hash((self.seed, peer, t)))
            self.due[peer] = now + self.interval * (1 + rng.uniform(-self.jitter, self.jitter))
        return out


# --- C031 quality measurement ----------------------------------------------------------------------

@dataclass
class QualityWindow:
    size: int = 64
    min_samples: int = 8
    max_age: float = 60.0
    samples: deque = field(default_factory=lambda: deque(maxlen=64))
    jitter: float = 0.0
    _prev_transit: float | None = None

    def __post_init__(self):
        self.samples = deque(maxlen=self.size)

    def add(self, now: float, rtt: float | None, *, send_ts: float | None = None, recv_ts: float | None = None) -> None:
        if rtt is not None and (rtt < 0 or rtt > 60):
            return                                # outlier policy: physically implausible sample dropped
        self.samples.append((now, rtt))
        if send_ts is not None and recv_ts is not None:
            transit = recv_ts - send_ts
            if self._prev_transit is not None:
                d = abs(transit - self._prev_transit)
                self.jitter += (d - self.jitter) / 16.0        # RFC 3550 A.8
            self._prev_transit = transit

    def summary(self, now: float) -> dict:
        fresh = [(t, r) for t, r in self.samples if 0 <= now - t <= self.max_age]
        if len(fresh) < self.min_samples:
            return {"state": "unknown", "samples": len(fresh), "rtt_median": None, "rtt_p95": None,
                    "loss": None, "jitter": None, "metric": "round-trip"}
        rtts = sorted(r for _, r in fresh if r is not None)
        loss = 1 - len(rtts) / len(fresh)
        p95 = rtts[min(len(rtts) - 1, int(math.ceil(0.95 * len(rtts))) - 1)] if rtts else None
        return {"state": "measured", "samples": len(fresh), "rtt_median": statistics.median(rtts) if rtts else None,
                "rtt_p95": p95, "loss": round(loss, 4), "jitter": round(self.jitter, 6), "metric": "round-trip"}


def bulk_ready(goodput_samples: list[tuple[float, int]], *, window: float = 5.0, min_bytes_per_s: float = 1e6,
               now: float) -> tuple[bool, str]:
    """Readiness for sustained traffic: goodput over a window, separate from liveness."""
    recent = [(t, b) for t, b in goodput_samples if 0 <= now - t <= window]
    if len(recent) < 3:
        return False, "unknown"
    span = max(t for t, _ in recent) - min(t for t, _ in recent)
    if span < window * 0.6:
        return False, "unknown"
    rate = sum(b for _, b in recent) / span
    return rate >= min_bytes_per_s, f"{rate:.0f}B/s"


@dataclass
class BandwidthEstimator:
    max_age: float = 120.0
    max_probe_bytes: int = 256 * 1024
    estimate: float | None = None
    measured_at: float | None = None
    disabled_reason: str | None = None

    def configure(self, *, metered: bool, power_saving: bool = False, policy_allowed: bool = True) -> None:
        self.disabled_reason = ("metered" if metered else "power" if power_saving else
                                "policy" if not policy_allowed else None)

    def probe_train(self, send_train, n: int = 8, size: int = 1200) -> float | None:
        if self.disabled_reason:
            return None
        n = min(n, self.max_probe_bytes // size)
        dispersions = send_train(n, size)          # returns arrival timestamps of the train
        if not dispersions or len(dispersions) < 2:
            return None
        spread = dispersions[-1] - dispersions[0]
        if spread <= 0:
            return None
        return (len(dispersions) - 1) * size / spread

    def update(self, value: float | None, now: float) -> None:
        if value is not None:
            self.estimate, self.measured_at = value, now

    def current(self, now: float) -> float | None:
        if self.disabled_reason or self.measured_at is None or now - self.measured_at > self.max_age:
            return None                             # unknown, never zero
        return self.estimate


# --- C033 scoring with hysteresis ------------------------------------------------------------------

@dataclass
class PathScorer:
    margin: float = 0.2
    hold_down: float = 10.0
    current: str | None = None
    switched_at: float | None = None
    switches: int = 0

    @staticmethod
    def score(q: dict, *, cost: float = 0.0, trusted: bool = True, policy_ok: bool = True,
              quota_ok: bool = True, residency_ok: bool = True) -> float:
        if not (trusted and policy_ok and quota_ok and residency_ok):
            return 0.0                              # constraints are inputs, not annotations
        if q.get("state") != "measured" or q.get("rtt_median") is None:
            return 0.01
        rtt, loss = q["rtt_median"], q.get("loss") or 0.0
        return max(0.0, (1.0 / (1.0 + rtt * 10)) * (1 - loss) ** 2 / (1.0 + cost))

    def choose(self, scores: dict[str, float], now: float) -> str | None:
        if not scores:
            return None
        best = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0]     # deterministic tie-break
        if self.current is None or scores.get(self.current, 0.0) == 0.0:
            self._switch(best[0], now)
            return self.current
        if best[0] == self.current:
            return self.current
        in_hold = self.switched_at is not None and now - self.switched_at < self.hold_down
        if not in_hold and best[1] > scores[self.current] * (1 + self.margin):
            self._switch(best[0], now)
        return self.current

    def _switch(self, name, now):
        if name != self.current:
            self.switches += 1
        self.current, self.switched_at = name, now


# --- C034 keepalive / C035 resumption / C036 candidate cache ---------------------------------------

@dataclass
class KeepalivePolicy:
    """UDP NAT bindings commonly expire after 30-120 s (RFC 4787 REQ-5 asks >= 2 min).
    Refresh at a fraction of the smallest observed/assumed binding timeout."""
    assumed_binding_timeout: float = 30.0
    fraction: float = 0.5
    min_interval: float = 5.0

    def interval(self, observed_timeout: float | None = None) -> float:
        t = min(self.assumed_binding_timeout, observed_timeout or self.assumed_binding_timeout)
        return max(self.min_interval, t * self.fraction)

    def due(self, last_sent: float, now: float, observed_timeout: float | None = None) -> bool:
        return now - last_sent >= self.interval(observed_timeout)


class ResumptionTickets:
    """HMAC-sealed, expiring, single-use resumption tickets bound to peer + path epoch."""

    def __init__(self, key: bytes, lifetime: float = 30.0, clock=time.time):
        self.key, self.lifetime, self.clock = key, lifetime, clock
        self.used: OrderedDict[str, None] = OrderedDict()

    def issue(self, peer: str, epoch: int, state: dict) -> str:
        body = json.dumps({"p": peer, "e": epoch, "x": self.clock() + self.lifetime, "n": os.urandom(8).hex(),
                           "s": state}, sort_keys=True, separators=(",", ":"))
        tag = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return body + "." + tag

    def redeem(self, ticket: str, peer: str, epoch: int) -> dict | None:
        try:
            body, tag = ticket.rsplit(".", 1)
        except ValueError:
            return None
        if not hmac.compare_digest(hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest(), tag):
            return None
        d = json.loads(body)
        if d["p"] != peer or d["e"] != epoch or d["x"] < self.clock() or d["n"] in self.used:
            return None
        self.used[d["n"]] = None
        while len(self.used) > 4096:
            self.used.popitem(last=False)
        return d["s"]


@dataclass
class CandidateCache:
    ttl: float = 120.0
    max_entries: int = 512
    entries: OrderedDict = field(default_factory=OrderedDict)

    def put(self, peer: str, candidates: list, network_fp: str, now: float) -> None:
        self.entries[peer] = (list(candidates), network_fp, now)
        self.entries.move_to_end(peer)
        while len(self.entries) > self.max_entries:
            self.entries.popitem(last=False)

    def get(self, peer: str, network_fp: str, now: float) -> list | None:
        hit = self.entries.get(peer)
        if hit is None:
            return None
        cands, fp, t = hit
        if fp != network_fp or not 0 <= now - t <= self.ttl:
            del self.entries[peer]                # expired or measured on another network
            return None
        return list(cands)

    def invalidate_network(self, network_fp: str) -> int:
        stale = [p for p, (_, fp, _) in self.entries.items() if fp != network_fp]
        for p in stale:
            del self.entries[p]
        return len(stale)


@dataclass
class RelayPrewarm:
    threshold: int = 3
    window: float = 3600.0
    max_prewarmed: int = 32
    failures: dict[str, deque] = field(default_factory=dict)

    def record_direct_failure(self, site: str, now: float) -> None:
        self.failures.setdefault(site, deque(maxlen=16)).append(now)

    def should_prewarm(self, site: str, now: float, currently_prewarmed: int) -> bool:
        recent = [t for t in self.failures.get(site, ()) if now - t <= self.window]
        return len(recent) >= self.threshold and currently_prewarmed < self.max_prewarmed


def choose_region(regions: list[dict], *, residency: set[str] | None = None, max_cost: float | None = None) -> tuple[dict | None, str]:
    """regions: {name, jurisdiction, rtt_ms, cost_per_gb, healthy}. Residency is a hard filter."""
    ok = [r for r in regions if r.get("healthy") and (residency is None or r["jurisdiction"] in residency)
          and (max_cost is None or r["cost_per_gb"] <= max_cost)]
    if not ok:
        return None, "POLICY_EGRESS_DENIED" if residency else "DEP_UNAVAILABLE"
    ok.sort(key=lambda r: (r["rtt_ms"] * (1 + r["cost_per_gb"]), r["name"]))
    return ok[0], "OK"


# --- C039 quota / C040 instrumentation ---------------------------------------------------------------

class RelayQuota:
    """Atomic per-tenant counters with soft/hard limits.  Keyed by tenant identity,
    not connection, so reconnects and region changes cannot reset usage.  On
    telemetry outage the hard limit still applies to locally observed bytes
    (fail-closed); counter disagreement uses the larger value."""

    def __init__(self, soft: int, hard: int):
        if not 0 < soft <= hard:
            raise ValueError("0 < soft <= hard")
        self.soft, self.hard = soft, hard
        self._lock = threading.Lock()
        self.used: dict[str, int] = {}
        self.lineage: dict[str, list[str]] = {}

    def reserve(self, tenant: str, n: int, *, region: str = "", authoritative: int | None = None) -> str:
        if n < 0:
            raise ValueError("negative reservation")
        with self._lock:
            cur = max(self.used.get(tenant, 0), authoritative or 0)
            if cur + n > self.hard:
                return "BUDGET_QUOTA_EXHAUSTED"
            self.used[tenant] = cur + n
            if region:
                lin = self.lineage.setdefault(tenant, [])
                if not lin or lin[-1] != region:
                    lin.append(region)
            return "SOFT_LIMIT" if cur + n > self.soft else "OK"


class InstrumentedRelay:
    """Wraps a relay transport (e.g. TurnClient) so bytes are counted where they
    cross the data plane — callers cannot forget to account them."""

    def __init__(self, transport, path=None, quota: RelayQuota | None = None, tenant: str = ""):
        self.t, self.path, self.quota, self.tenant = transport, path, quota, tenant
        self.bytes_out = self.bytes_in = 0

    def send(self, peer, payload: bytes):
        if self.quota is not None and self.quota.reserve(self.tenant, len(payload)) == "BUDGET_QUOTA_EXHAUSTED":
            raise PermissionError("BUDGET_QUOTA_EXHAUSTED")
        self.t.send(peer, payload)
        self.bytes_out += len(payload)
        if self.path is not None and self.path.strategy == "relay":
            self.path.record_relay_bytes(len(payload))

    def recv(self, timeout: float = 1.0):
        got = self.t.recv(timeout)
        if got is not None:
            self.bytes_in += len(got[1])
            if self.path is not None and self.path.strategy == "relay":
                self.path.record_relay_bytes(len(got[1]))
        return got

    def reconcile(self, server_reported: int, tolerance: float = 0.02) -> dict:
        local = self.bytes_out + self.bytes_in
        diverged = abs(local - server_reported) > max(64, tolerance * max(local, server_reported))
        return {"local": local, "server": server_reported, "diverged": diverged,
                "alert": "relay_accounting_divergence" if diverged else None}


# --- P2: multipath and prediction ----------------------------------------------------------------------

@dataclass
class MultipathScheduler:
    """Failover-first; striping only when the caller declares the payload reorder-tolerant."""
    paths: dict[str, float] = field(default_factory=dict)          # name -> weight (score)

    def pick(self, *, reorder_tolerant: bool, seq: int) -> list[str]:
        live = sorted((n for n, w in self.paths.items() if w > 0), key=lambda n: (-self.paths[n], n))
        if not live:
            return []
        if not reorder_tolerant or len(live) == 1:
            return [live[0]]
        total = sum(self.paths[n] for n in live)
        x = (seq * 0.6180339887) % 1.0 * total
        for n in live:
            x -= self.paths[n]
            if x <= 0:
                return [n]
        return [live[-1]]


@dataclass
class TrendPredictor:
    """EWMA slope of RTT/loss; recommends a pre-emptive switch only on a sustained,
    significant deterioration (never on a single spike)."""
    alpha: float = 0.3
    min_points: int = 6
    level: float | None = None
    trend: float = 0.0
    n: int = 0

    def add(self, value: float) -> None:
        self.n += 1
        if self.level is None:
            self.level = value
            return
        prev = self.level
        self.level = self.alpha * value + (1 - self.alpha) * (self.level + self.trend)
        self.trend = self.alpha * (self.level - prev) + (1 - self.alpha) * self.trend

    def deteriorating(self, threshold: float) -> bool:
        return self.n >= self.min_points and self.trend > threshold
