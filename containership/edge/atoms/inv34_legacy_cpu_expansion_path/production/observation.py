"""Independent guest CPU-online observation (MC-006, MC-028).

SPDX-License-Identifier: NOASSERTION

The guest reports ``/sys/devices/system/cpu/online`` (Linux cpulist format,
e.g. ``0-3,6``) through an agent.  Reports are authenticated with a per-source
HMAC key, bound to a VM and a monotonically increasing sequence number, and
carry a timestamp so stale or replayed observations are refused.  This is
the ONLY path that may move ``observed_vcpus``; the hypervisor's presentation
count never does.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Callable

OBSERVATION_SCHEMA = "INV34_GUEST_CPU_OBSERVATION/1"
MAX_CPULIST_LEN = 4096


class ObservationRejected(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_cpulist(text: str, limit: int = 65_536) -> frozenset[int]:
    """Parse the kernel cpulist format strictly (no whitespace-tolerant guessing)."""
    if not isinstance(text, str) or len(text) > MAX_CPULIST_LEN:
        raise ObservationRejected("OBS_MALFORMED", "cpulist must be a short string")
    text = text.strip("\n")
    if not text:
        raise ObservationRejected("OBS_MALFORMED", "empty cpulist")
    cpus: set[int] = set()
    for part in text.split(","):
        if "-" in part:
            a, _, b = part.partition("-")
            if not (a.isdigit() and b.isdigit()) or int(a) > int(b):
                raise ObservationRejected("OBS_MALFORMED", f"bad range {part!r}")
            lo, hi = int(a), int(b)
        else:
            if not part.isdigit():
                raise ObservationRejected("OBS_MALFORMED", f"bad cpu id {part!r}")
            lo = hi = int(part)
        if hi >= limit:
            raise ObservationRejected("OBS_MALFORMED", "cpu id over sanity limit")
        cpus.update(range(lo, hi + 1))
    return frozenset(cpus)


def _canonical(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign_observation(key: bytes, body: dict) -> str:
    return hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class VerifiedObservation:
    vm_id: str
    source_id: str
    online_vcpus: int
    sequence: int
    observed_at: float


class ObservationVerifier:
    def __init__(self, keys: dict[str, bytes], *, max_age_s: float = 30.0,
                 max_future_skew_s: float = 5.0, clock: Callable[[], float] = time.time) -> None:
        if not keys:
            raise ValueError("at least one observation source key is required")
        self._keys = dict(keys)
        self._bindings: dict[str, str] = {}      # vm_id -> source allowed to report it
        self._seq: dict[tuple[str, str], int] = {}
        self.max_age_s = max_age_s
        self.skew = max_future_skew_s
        self._clock = clock

    def bind(self, vm_id: str, source_id: str) -> None:
        if source_id not in self._keys:
            raise ValueError("unknown source")
        self._bindings[vm_id] = source_id

    def restore_sequences(self, seqs: dict[tuple[str, str], int]) -> None:
        self._seq.update(seqs)

    def verify(self, report: dict) -> VerifiedObservation:
        if not isinstance(report, dict) or report.get("schema") != OBSERVATION_SCHEMA:
            raise ObservationRejected("OBS_SCHEMA", "wrong or missing schema")
        body = {k: report.get(k) for k in ("schema", "vm_id", "source_id", "sequence", "observed_at", "cpu_online")}
        src, vm = body["source_id"], body["vm_id"]
        key = self._keys.get(src) if isinstance(src, str) else None
        if key is None:
            raise ObservationRejected("OBS_UNKNOWN_SOURCE", "unauthenticated observation source")
        sig = report.get("signature")
        if not isinstance(sig, str) or not hmac.compare_digest(sig, sign_observation(key, body)):
            raise ObservationRejected("OBS_BAD_SIGNATURE", "signature mismatch")
        if self._bindings.get(vm) != src:
            raise ObservationRejected("OBS_SOURCE_NOT_BOUND", "source is not authorised for this VM")
        seq, ts = body["sequence"], body["observed_at"]
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
            raise ObservationRejected("OBS_MALFORMED", "sequence must be positive int")
        if not isinstance(ts, (int, float)) or isinstance(ts, bool):
            raise ObservationRejected("OBS_MALFORMED", "observed_at must be a number")
        now = self._clock()
        if ts > now + self.skew:
            raise ObservationRejected("OBS_FUTURE", "observation timestamp in the future")
        if now - ts > self.max_age_s:
            raise ObservationRejected("OBS_STALE", "observation older than freshness bound")
        last = self._seq.get((vm, src), 0)
        if seq <= last:
            raise ObservationRejected("OBS_REPLAY", f"sequence {seq} not after {last}")
        cpus = parse_cpulist(body["cpu_online"])
        self._seq[(vm, src)] = seq
        return VerifiedObservation(vm, src, len(cpus), seq, float(ts))


@dataclass(frozen=True)
class StallVerdict:
    state: str          # CONVERGED | PENDING | STALLED | PARTIAL_STALL | OBSERVATION_STALE
    pending_vcpus: int
    age_s: float
    reason: str


def classify_stall(desired: int, observed: int, accepted_at: float, last_progress_at: float,
                   last_observation_at: float | None, now: float, *, stall_after_s: float = 120.0,
                   observation_stale_after_s: float = 60.0) -> StallVerdict:
    """Explicit thresholds for pending/partial convergence (MC-028)."""
    pending = desired - observed
    if pending <= 0:
        return StallVerdict("CONVERGED", 0, 0.0, "observed == desired")
    if last_observation_at is None or now - last_observation_at > observation_stale_after_s:
        return StallVerdict("OBSERVATION_STALE", pending, now - (last_observation_at or accepted_at),
                            "no fresh guest observation; cannot judge progress")
    since = now - max(accepted_at, last_progress_at)
    if since > stall_after_s:
        state = "PARTIAL_STALL" if last_progress_at > accepted_at else "STALLED"
        return StallVerdict(state, pending, since, f"no progress for {since:.0f}s > {stall_after_s:.0f}s")
    return StallVerdict("PENDING", pending, since, "within stall threshold")
