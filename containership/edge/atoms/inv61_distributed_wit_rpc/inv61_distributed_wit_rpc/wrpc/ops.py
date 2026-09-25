"""M12-M17, M20 - configuration, audit chain, health, metrics, logs, traces, journal."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import threading
import time

# ------------------------------------------------------------ M12 config
SCHEMA = {
    "node_id": (str, None),
    "listen_host": (str, None),
    "listen_port": (int, (0, 65535)),
    "max_frame_bytes": (int, (1024, 1 << 24)),
    "max_connections": (int, (1, 100_000)),
    "max_inflight": (int, (1, 100_000)),
    "max_queue": (int, (0, 1_000_000)),
    "per_tenant_inflight": (int, (1, 100_000)),
    "handshake_timeout_s": (float, (0.1, 60.0)),
    "idle_timeout_s": (float, (1.0, 86400.0)),
    "idempotency_ttl_s": (float, (1.0, 86400.0)),
    "breaker_threshold": (int, (1, 1000)),
    "breaker_cooldown_s": (float, (0.1, 3600.0)),
    "log_level": (str, ("DEBUG", "INFO", "WARNING", "ERROR")),
    "trace_sample_ratio": (float, (0.0, 1.0)),
    "psk_ref": (str, None),               # a REFERENCE (env:/file:), never a secret value
}
DEFAULTS = {
    "node_id": "node-local", "listen_host": "127.0.0.1", "listen_port": 0,
    "max_frame_bytes": 1 << 20, "max_connections": 256, "max_inflight": 64, "max_queue": 128,
    "per_tenant_inflight": 32, "handshake_timeout_s": 5.0, "idle_timeout_s": 300.0,
    "idempotency_ttl_s": 600.0, "breaker_threshold": 5, "breaker_cooldown_s": 5.0,
    "log_level": "INFO", "trace_sample_ratio": 0.1, "psk_ref": "env:INV61_PSK",
}
_SECRET_LIKE = re.compile(r"(?i)(secret|password|token|psk)$")


class ConfigError(ValueError):
    pass


def validate_config(cfg: dict) -> dict:
    unknown = set(cfg) - set(SCHEMA)
    if unknown:
        raise ConfigError(f"unknown keys: {sorted(unknown)}")
    missing = set(SCHEMA) - set(cfg)
    if missing:
        raise ConfigError(f"missing keys: {sorted(missing)}")
    for k, (typ, rng) in SCHEMA.items():
        v = cfg[k]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = cfg[k] = float(v)
        if not isinstance(v, typ) or isinstance(v, bool):
            raise ConfigError(f"{k}: expected {typ.__name__}")
        if isinstance(rng, tuple) and len(rng) == 2 and typ in (int, float) and not rng[0] <= v <= rng[1]:
            raise ConfigError(f"{k}: out of range {rng}")
        if typ is str and isinstance(rng, tuple) and v not in rng:
            raise ConfigError(f"{k}: must be one of {rng}")
    if not re.fullmatch(r"(env|file):[A-Za-z0-9_./\-]+", cfg["psk_ref"]):
        raise ConfigError("psk_ref must be env:NAME or file:PATH (secret values are never inline)")
    if cfg["listen_host"] not in ("127.0.0.1", "::1", "localhost") and cfg["psk_ref"].startswith("env:INV61_PSK_DEV"):
        raise ConfigError("dev credential on non-loopback bind")
    return cfg


def resolve_secret(ref: str) -> bytes:
    kind, _, where = ref.partition(":")
    if kind == "env":
        v = os.environ.get(where)
        if not v:
            raise ConfigError(f"secret reference {ref} unresolved")
        return bytes.fromhex(v)
    with open(where, "rb") as fh:
        return bytes.fromhex(fh.read().decode().strip())


class ConfigStore:
    """Layered (defaults < file < environment overlay) config with a provenance
    digest, atomic activation, and one-step rollback to the last good config."""

    def __init__(self):
        self.active: dict | None = None
        self.previous: dict | None = None
        self.provenance: dict | None = None
        self._lock = threading.Lock()

    @staticmethod
    def build(*layers: tuple[str, dict]) -> tuple[dict, dict]:
        cfg, sources = copy.deepcopy(DEFAULTS), {k: "defaults" for k in DEFAULTS}
        for name, layer in layers:
            for k, v in layer.items():
                cfg[k], sources[k] = v, name
        validate_config(cfg)
        digest = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
        return cfg, {"digest": digest, "sources": sources, "built_at": time.time()}

    def activate(self, *layers) -> str:
        cfg, prov = self.build(*layers)       # validation happens BEFORE the swap
        with self._lock:
            self.previous, self.active, self.provenance = self.active, cfg, prov
        return prov["digest"]

    def rollback(self) -> str:
        with self._lock:
            if self.previous is None:
                raise ConfigError("no previous config")
            self.active, self.previous = self.previous, None
            self.provenance = {"digest": hashlib.sha256(json.dumps(self.active, sort_keys=True).encode()).hexdigest(),
                               "sources": {"*": "rollback"}, "built_at": time.time()}
            return self.provenance["digest"]


# ------------------------------------------------------- M13 audit chain
AUDIT_FIELDS = ("seq", "ts", "event", "tenant", "peer", "subject", "decision", "reason", "prev", "hash")


class AuditLog:
    """Append-only, hash-chained, fsync'd JSONL audit log. ``verify`` detects any
    edit, reorder, deletion or insertion; tail truncation is detected by comparing
    against an externally recorded head (``head()``)."""

    def __init__(self, path: str | None = None, max_memory_records: int = 10_000):
        # Memory holds a rolling window (M29 soak finding: an unbounded list grew RSS by
        # ~120 MB in 60 s). The durable copy is the file; the chain head is tracked separately.
        from collections import deque
        self.path = path
        self.records = deque(maxlen=max_memory_records)
        self._count, self._last = 0, "0" * 64
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                loaded = [json.loads(line) for line in fh if line.strip()]
            ok, why = self.verify(loaded)       # never extend a chain that does not verify
            if not ok:
                raise ValueError(f"audit log {path} failed verification on load: {why}")
            for rec in loaded:
                self.records.append(rec)
            if loaded:
                self._count, self._last = loaded[-1]["seq"] + 1, loaded[-1]["hash"]

    @staticmethod
    def _digest(rec: dict) -> str:
        body = {k: rec[k] for k in AUDIT_FIELDS if k != "hash"}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def append(self, event: str, tenant: str = "", peer: str = "", subject: str = "",
               decision: str = "", reason: str = "") -> dict:
        with self._lock:
            prev = self._last
            rec = {"seq": self._count, "ts": time.time(), "event": event, "tenant": tenant,
                   "peer": peer, "subject": subject, "decision": decision, "reason": reason, "prev": prev}
            rec["hash"] = self._digest(rec)
            self.records.append(rec)
            self._count, self._last = self._count + 1, rec["hash"]
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return rec

    def head(self) -> tuple[int, str]:
        with self._lock:
            return (self._count, self._last)

    @classmethod
    def verify(cls, records, expected_head: tuple | None = None, window: bool = False) -> tuple[bool, str]:
        """Verify a full log (default) or, with ``window=True``, a contiguous tail window
        whose first record is trusted as the anchor."""
        records = list(records)
        base = records[0]["seq"] if window and records else 0
        prev = records[0]["prev"] if window and records else "0" * 64
        for i, r in enumerate(records):
            if set(r) != set(AUDIT_FIELDS):
                return False, f"record {i}: field set"
            if r["seq"] != base + i or r["prev"] != prev or r["hash"] != cls._digest(r):
                return False, f"record {i}: chain broken"
            prev = r["hash"]
        if expected_head is not None and (base + len(records), prev) != tuple(expected_head):
            return False, "head mismatch (truncation or divergence)"
        return True, "ok"


# ------------------------------------------------------------ M15 metrics
class Metrics:
    """Counters and fixed-bucket histograms with a label-cardinality cap; renders
    Prometheus text exposition format 0.0.4."""

    BUCKETS = (0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
    ALLOWED_LABELS = frozenset({"interface", "function", "outcome", "tenant"})

    def __init__(self, max_series: int = 2000):
        self.max_series = max_series
        self.counters: dict = {}
        self.hists: dict = {}
        self.dropped = 0
        self._lock = threading.Lock()

    def _key(self, name, labels):
        if set(labels) - self.ALLOWED_LABELS:
            raise ValueError("label not allowed")
        return (name, tuple(sorted(labels.items())))

    def _admit(self, store, key) -> bool:
        if key in store:
            return True
        if len(self.counters) + len(self.hists) >= self.max_series:
            self.dropped += 1
            return False
        return True

    def inc(self, name: str, n: float = 1, **labels):
        k = self._key(name, labels)
        with self._lock:
            if self._admit(self.counters, k):
                self.counters[k] = self.counters.get(k, 0) + n

    def observe(self, name: str, value: float, **labels):
        k = self._key(name, labels)
        with self._lock:
            if not self._admit(self.hists, k):
                return
            h = self.hists.setdefault(k, [[0] * len(self.BUCKETS), 0, 0.0])
            for i, b in enumerate(self.BUCKETS):
                if value <= b:
                    h[0][i] += 1
            h[1] += 1
            h[2] += value

    @staticmethod
    def _lbl(pairs, extra=()):
        items = list(pairs) + list(extra)
        if not items:
            return ""
        esc = lambda v: str(v).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in items) + "}"

    def render(self) -> str:
        lines = []
        with self._lock:
            for name in sorted({k[0] for k in self.counters}):
                lines.append(f"# TYPE {name} counter")
                for (n, lbl), v in sorted(self.counters.items()):
                    if n == name:
                        lines.append(f"{name}{self._lbl(lbl)} {v}")
            for name in sorted({k[0] for k in self.hists}):
                lines.append(f"# TYPE {name} histogram")
                for (n, lbl), (buckets, count, total) in sorted(self.hists.items()):
                    if n != name:
                        continue
                    for b, c in zip(self.BUCKETS, buckets):
                        lines.append(f"{name}_bucket{self._lbl(lbl, [('le', repr(b))])} {c}")
                    lines.append(f"{name}_bucket{self._lbl(lbl, [('le', '+Inf')])} {count}")
                    lines.append(f"{name}_sum{self._lbl(lbl)} {total}")
                    lines.append(f"{name}_count{self._lbl(lbl)} {count}")
            lines.append("# TYPE inv61_metric_series_dropped_total counter")
            lines.append(f"inv61_metric_series_dropped_total {self.dropped}")
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------ M16 logging
_REDACT_KEYS = re.compile(r"(?i)(secret|password|token|psk|key|args|payload|authorization)")


class JsonLogger:
    """One JSON object per line; fixed envelope; secrets and call arguments are
    redacted by key; oversize fields truncated; level-filtered; rate-limited."""

    LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

    def __init__(self, sink, level: str = "INFO", max_field: int = 512, rate_per_s: int = 1000, clock=time.time):
        self.sink, self.level, self.max_field, self.rate, self.clock = sink, self.LEVELS[level], max_field, rate_per_s, clock
        self._window, self._count, self.suppressed, self.sink_failures = 0, 0, 0, 0
        self._lock = threading.Lock()

    def _clean(self, v):
        if isinstance(v, dict):
            return {k: ("[REDACTED]" if _REDACT_KEYS.search(k) else self._clean(x)) for k, x in v.items()}
        if isinstance(v, str) and len(v) > self.max_field:
            return v[: self.max_field] + "...[truncated]"
        return v

    def log(self, level: str, event: str, **fields):
        if self.LEVELS[level] < self.level:
            return
        now = self.clock()
        with self._lock:
            w = int(now)
            if w != self._window:
                self._window, self._count = w, 0
            self._count += 1
            if self._count > self.rate:
                self.suppressed += 1
                return
        rec = {"ts": round(now, 6), "level": level, "component": "INV-61", "event": event}
        rec.update(self._clean(fields))
        try:
            self.sink(json.dumps(rec, sort_keys=True, default=str))
        except Exception:               # a broken log sink must never drop a response
            self.sink_failures += 1


# ------------------------------------------------------------ M17 tracing
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(tp: str):
    """W3C trace-context ``traceparent``; invalid or all-zero ids -> None (start a new trace)."""
    m = _TP.fullmatch(tp or "")
    if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
        return None
    return m.group(1), m.group(2), int(m.group(3), 16) & 1


def child_traceparent(parent: str | None, sample_ratio: float, rng=secrets.randbelow) -> tuple[str, str, bool]:
    parsed = parse_traceparent(parent) if parent else None
    if parsed:
        trace_id, _, sampled = parsed
    else:
        trace_id, sampled = secrets.token_hex(16), rng(1_000_000) < sample_ratio * 1_000_000
    span_id = secrets.token_hex(8)
    return f"00-{trace_id}-{span_id}-{'01' if sampled else '00'}", span_id, bool(sampled)


class Tracer:
    def __init__(self, exporter=None, max_attrs: int = 16):
        self.exporter = exporter or (lambda span: None)
        self.max_attrs = max_attrs
        self.export_failures = 0

    def span(self, name: str, traceparent: str, status_fn=None, **attrs):
        """``status_fn`` (evaluated at exit) lets a handler that returns typed errors,
        rather than raising, mark the span as failed."""
        tracer = self
        safe = {k: v for k, v in list(attrs.items())[: self.max_attrs] if not _REDACT_KEYS.search(k)}

        class _S:
            def __enter__(s):
                s.t0 = time.perf_counter()
                s.status, s.error = "ok", None
                return s

            def __exit__(s, et, ev, tb):
                if et is not None:
                    s.status, s.error = "error", et.__name__
                elif status_fn is not None:
                    st = status_fn()
                    if st != "ok":
                        s.status, s.error = "error", st
                parsed = parse_traceparent(traceparent)
                if parsed and parsed[2]:
                    span = {"name": name, "trace_id": parsed[0], "span_id": parsed[1],
                            "duration_s": time.perf_counter() - s.t0, "status": s.status, "attrs": safe}
                    if s.error:
                        span["error"] = s.error
                    try:
                        tracer.exporter(span)
                    except Exception:           # telemetry must never fail the call
                        tracer.export_failures += 1
                return False
        return _S()


# ------------------------------------------------------------ M14 health
class Health:
    """Liveness = process loop responsive; readiness = every *critical* dependency
    check passes and the node is not draining. Checks are time-boxed and cached."""

    def __init__(self, clock=time.monotonic, cache_s: float = 1.0, check_timeout_s: float = 0.5):
        self.check_timeout_s = check_timeout_s
        self.checks: dict = {}
        self.draining = False
        self.clock, self.cache_s = clock, cache_s
        self._cache: dict = {}

    def register(self, name: str, fn, critical: bool = True):
        self.checks[name] = (fn, critical)

    def _run(self, name):
        fn, _ = self.checks[name]
        hit = self._cache.get(name)
        if hit and self.clock() - hit[0] < self.cache_s:
            return hit[1]
        box = {}

        def target():
            try:
                box["ok"] = bool(fn())
            except Exception as exc:     # a check that raises is a failed check
                box["exc"] = type(exc).__name__
        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(self.check_timeout_s)
        if t.is_alive():
            ok, detail = False, "timeout"
        elif "exc" in box:
            ok, detail = False, box["exc"]
        else:
            ok, detail = box["ok"], ""
        self._cache[name] = (self.clock(), (ok, detail))
        return ok, detail

    def live(self) -> dict:
        return {"status": "pass"}

    def ready(self) -> dict:
        deps = {n: self._run(n) for n in self.checks}
        crit_ok = all(ok for n, (ok, _) in deps.items() if self.checks[n][1])
        status = "fail" if self.draining or not crit_ok else ("warn" if not all(ok for ok, _ in deps.values()) else "pass")
        return {"status": status, "draining": self.draining,
                "checks": {n: {"status": "pass" if ok else "fail", "critical": self.checks[n][1],
                               **({"detail": d} if d else {})} for n, (ok, d) in deps.items()}}


# ------------------------------------------------------------ M20 journal
class Journal:
    """Durable append-only journal for completed idempotent outcomes, so a restart
    does not re-execute a call the caller already saw succeed. Torn final lines
    (crash mid-write) are ignored; every other corrupt line fails closed."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()

    SCHEMA = "INV61_JOURNAL/2"

    def append(self, key: tuple, ts: float, outcome, digest: str = "") -> None:
        line = json.dumps({"v": self.SCHEMA, "k": list(key), "ts": ts, "o": outcome, "d": digest},
                          sort_keys=True, default=str)
        with self._lock, open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def replay(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        out = {}
        with open(self.path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        tail_torn = lines and lines[-1] != ""
        for i, line in enumerate(lines):
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                if tail_torn and i == len(lines) - 1:
                    break
                raise ValueError(f"journal corrupt at line {i + 1}") from None
            if rec.get("v", self.SCHEMA) != self.SCHEMA:
                raise ValueError(f"journal schema {rec.get('v')!r} unsupported at line {i + 1}")
            out[tuple(rec["k"])] = (rec["ts"], rec["o"], rec.get("d", ""))
        return out
