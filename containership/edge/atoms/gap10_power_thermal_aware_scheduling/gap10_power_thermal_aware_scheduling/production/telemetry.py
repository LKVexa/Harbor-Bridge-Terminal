"""Components 01 and 10 - authenticated GAP-09 telemetry adapter and the
multi-sensor aggregation model.

Envelope (``PK_TELEMETRY_ENVELOPE/1``) produced by GAP-09::

    {"schema": "PK_TELEMETRY_ENVELOPE/1", "key_id": "...", "signature": "...",
     "attestation": "hardware|software|none", "correlation_id": "...",
     "payload": {"node": "...", "site": "...", "seq": 17, "observed_at": 1.0,
                 "sensors": [{"sensor_id": "cpu0", "kind": "cpu", "temperature_c": 55.0}],
                 "power_draw_watts": 90.0, "power_budget_watts": 200.0,
                 "battery_fraction": 0.8}}

Signature is verified *before* any value is parsed into trusted fields.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import isfinite

from .errors import ErrorCode, Gap10Error
from .keys import KeyRing

SUPPORTED_MAJOR = 1
MAX_ENVELOPE_BYTES = 64 * 1024
MAX_SENSORS = 64
SENSOR_KINDS = ("cpu", "gpu", "vrm", "ssd", "inlet", "exhaust", "chassis", "accelerator", "battery", "other")
ATTESTATIONS = {"hardware": 2, "software": 1, "none": 0}


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(float(v))


@dataclass(frozen=True)
class SensorReading:
    sensor_id: str
    kind: str
    temperature_c: float | None
    trusted: bool
    reason: str = ""


@dataclass(frozen=True)
class CanonicalSample:
    """Canonical GAP-10 domain sample with full provenance."""
    node: str
    site: str
    seq: int
    observed_at: float
    received_at: float
    source_identity: str
    key_id: str
    attestation: str
    signature_status: str
    schema_version: str
    correlation_id: str
    sensors: tuple[SensorReading, ...]
    power_draw_watts: float | None
    power_budget_watts: float | None
    battery_fraction: float | None
    trust: str  # "trusted" | "partial"

    def provenance(self) -> dict:
        return {
            "node": self.node, "site": self.site, "seq": self.seq, "observed_at": self.observed_at,
            "received_at": self.received_at, "source_identity": self.source_identity, "key_id": self.key_id,
            "attestation": self.attestation, "signature_status": self.signature_status,
            "schema_version": self.schema_version, "correlation_id": self.correlation_id, "trust": self.trust,
        }


COUNTER_NAMES = ("rate_limited", "accepted", "stale", "future", "malformed", "unauthenticated", "unauthorized",
                 "bad_signature", "replayed", "unsupported_version", "implausible", "duplicate", "oversize")


@dataclass
class TelemetryAdapter:
    keyring: KeyRing
    max_age_s: float = 30.0
    max_future_skew_s: float = 5.0
    min_attestation: str = "hardware"
    min_temp_c: float = -40.0
    max_temp_c: float = 150.0
    max_power_w: float = 100_000.0
    counters: dict[str, int] = field(default_factory=lambda: {k: 0 for k in COUNTER_NAMES})
    _last_seq: dict[tuple[str, str], int] = field(default_factory=dict)
    last_success_at: float | None = None
    negotiated_version: str = "PK_TELEMETRY_ENVELOPE/1"
    rate_per_identity_s: float = 50.0     # token-bucket refill (samples/second per reporter identity and node)
    burst_per_identity: float = 100.0
    _buckets: dict[tuple[str, str], list] = field(default_factory=dict)

    def _rate_ok(self, identity: str, node: str, now: float) -> bool:
        b = self._buckets.setdefault((identity, node), [self.burst_per_identity, now])
        b[0] = min(self.burst_per_identity, b[0] + max(0.0, now - b[1]) * self.rate_per_identity_s)
        b[1] = now
        if b[0] < 1.0:
            return False
        b[0] -= 1.0
        return True

    def _reject(self, counter: str, code: ErrorCode, msg: str, cid=None):
        self.counters[counter] += 1
        raise Gap10Error(code, msg, correlation_id=cid)

    def ingest(self, raw: bytes | str | dict, *, now: float) -> CanonicalSample:
        # 1. bounded decode
        if isinstance(raw, (bytes, str)):
            if len(raw) > MAX_ENVELOPE_BYTES:
                self._reject("oversize", ErrorCode.TELEMETRY_OVERSIZE, "envelope too large")
            try:
                env = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "not JSON")
        else:
            env = raw
        if not isinstance(env, dict):
            self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "envelope must be an object")
        cid = env.get("correlation_id") if isinstance(env.get("correlation_id"), str) else None
        schema = env.get("schema")
        if not isinstance(schema, str) or not schema.startswith("PK_TELEMETRY_ENVELOPE/"):
            self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "missing schema", cid)
        try:
            major = int(schema.split("/")[1].split(".")[0])
        except ValueError:
            self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "bad schema version", cid)
        if major != SUPPORTED_MAJOR:
            self._reject("unsupported_version", ErrorCode.TELEMETRY_UNSUPPORTED_VERSION, schema, cid)
        payload, key_id, sig = env.get("payload"), env.get("key_id"), env.get("signature")
        if not isinstance(payload, dict) or not isinstance(key_id, str) or not isinstance(sig, str):
            self._reject("unauthenticated", ErrorCode.TELEMETRY_UNAUTHENTICATED, "unsigned envelope", cid)
        node = payload.get("node")
        if not isinstance(node, str) or not node or len(node) > 256:
            self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "bad node", cid)
        # 2. authenticate + authorize BEFORE trusting values
        try:
            identity = self.keyring.verify(key_id, "telemetry.publish", node, payload, sig, now=now)
        except Gap10Error as e:
            if e.code == ErrorCode.KEY_SCOPE_DENIED:
                self._reject("unauthorized", ErrorCode.TELEMETRY_UNAUTHORIZED, e.message, cid)
            if e.code == ErrorCode.TELEMETRY_BAD_SIGNATURE:
                self._reject("bad_signature", ErrorCode.TELEMETRY_BAD_SIGNATURE, e.message, cid)
            self._reject("unauthenticated", ErrorCode.TELEMETRY_UNAUTHENTICATED, e.message, cid)
        if not self._rate_ok(identity, node, now):
            self._reject("rate_limited", ErrorCode.TELEMETRY_RATE_LIMITED, f"{identity} over rate", cid)
        attestation = env.get("attestation", "none")
        if not isinstance(attestation, str):
            attestation = "invalid"
        if ATTESTATIONS.get(attestation, -1) < ATTESTATIONS[self.min_attestation]:
            self._reject("unauthenticated", ErrorCode.TELEMETRY_UNAUTHENTICATED, f"attestation {attestation!r} insufficient", cid)
        # 3. freshness / replay
        seq, observed = payload.get("seq"), payload.get("observed_at")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0 or not _num(observed):
            self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "seq/observed_at invalid", cid)
        stream = (identity, node)
        last = self._last_seq.get(stream)
        if last is not None and seq == last:
            self._reject("duplicate", ErrorCode.TELEMETRY_REPLAYED, f"duplicate seq {seq}", cid)
        if last is not None and seq < last:
            self._reject("replayed", ErrorCode.TELEMETRY_REPLAYED, f"seq {seq} < {last}", cid)
        age = now - float(observed)
        if age > self.max_age_s:
            self._reject("stale", ErrorCode.TELEMETRY_STALE, f"age {age:.1f}s", cid)
        if age < -self.max_future_skew_s:
            self._reject("future", ErrorCode.TELEMETRY_FUTURE, f"{-age:.1f}s in future", cid)
        # 4. parse values with plausibility
        sensors_raw = payload.get("sensors", [])
        if not isinstance(sensors_raw, list) or len(sensors_raw) > MAX_SENSORS:
            self._reject("malformed", ErrorCode.TELEMETRY_MALFORMED, "sensors invalid", cid)
        sensors = []
        for s in sensors_raw:
            if not isinstance(s, dict) or not isinstance(s.get("sensor_id"), str):
                sensors.append(SensorReading("?", "other", None, False, "malformed sensor record"))
                continue
            kind = s.get("kind") if s.get("kind") in SENSOR_KINDS else "other"
            t = s.get("temperature_c")
            if s.get("healthy") is False:
                sensors.append(SensorReading(s["sensor_id"], kind, None, False, "sensor reports unhealthy"))
            elif not _num(t) or not self.min_temp_c <= float(t) <= self.max_temp_c:
                self.counters["implausible"] += 1
                sensors.append(SensorReading(s["sensor_id"], kind, None, False, f"implausible temperature {t!r}"))
            else:
                sensors.append(SensorReading(s["sensor_id"], kind, float(t), True))
        pdraw, pbud, bat = payload.get("power_draw_watts"), payload.get("power_budget_watts"), payload.get("battery_fraction")
        pdraw = float(pdraw) if _num(pdraw) and 0 <= pdraw <= self.max_power_w else None
        pbud = float(pbud) if _num(pbud) and 0 < pbud <= self.max_power_w else None
        bat = float(bat) if _num(bat) and 0 <= bat <= 1 else None
        trust = "trusted" if sensors and all(r.trusted for r in sensors) else "partial"
        self._last_seq[stream] = seq
        self.counters["accepted"] += 1
        self.last_success_at = now
        site = payload.get("site") if isinstance(payload.get("site"), str) else "unknown"
        return CanonicalSample(node, site, seq, float(observed), now, identity, key_id, attestation,
                               "verified", schema, cid or "", tuple(sensors), pdraw, pbud, bat, trust)

    def health(self, now: float) -> dict:
        age = None if self.last_success_at is None else now - self.last_success_at
        return {"negotiated_version": self.negotiated_version, "last_success_at": self.last_success_at,
                "degraded": age is None or age > self.max_age_s, "counters": dict(self.counters)}


# ------------------------------------------------------- component 10: aggregation
@dataclass(frozen=True)
class AggregationPolicy:
    """Worst-case by default. ``offsets`` converts sensor-kind readings onto
    the node reference scale (e.g. a hotspot runs 10 C hotter than the package
    limit it protects), ``required_kinds`` must be present and trusted or the
    node is treated as partially observed (fail-closed to at least critical)."""
    mode: str = "worst-case"   # worst-case | weighted-with-floor
    offsets: dict = field(default_factory=dict)
    weights: dict = field(default_factory=dict)
    required_kinds: tuple[str, ...] = ("cpu",)


@dataclass(frozen=True)
class AggregateResult:
    temperature_c: float | None
    limiting_sensor: str | None
    complete: bool
    missing_required: tuple[str, ...]
    untrusted_sensors: tuple[str, ...]


def aggregate(sensors, policy: AggregationPolicy = AggregationPolicy()) -> AggregateResult:
    trusted = [s for s in sensors if s.trusted and s.temperature_c is not None]
    untrusted = tuple(s.sensor_id for s in sensors if not s.trusted)
    present = {s.kind for s in trusted}
    missing = tuple(k for k in policy.required_kinds if k not in present)
    if not trusted:
        return AggregateResult(None, None, False, missing, untrusted)
    adjusted = [(s.temperature_c - policy.offsets.get(s.kind, 0.0), s) for s in trusted]
    worst_t, worst_s = max(adjusted, key=lambda x: x[0])
    if policy.mode == "weighted-with-floor" and policy.weights:
        wsum = sum(policy.weights.get(s.kind, 1.0) for _, s in adjusted)
        weighted = sum(t * policy.weights.get(s.kind, 1.0) for t, s in adjusted) / wsum
        # Weighted averaging is reported for diagnostics only; the decision value
        # is floored at the worst trusted sensor so averaging can never hide a hotspot.
        value = max(weighted, worst_t)
    else:
        value = worst_t
    return AggregateResult(value, worst_s.sensor_id, not missing and not untrusted, missing, untrusted)
