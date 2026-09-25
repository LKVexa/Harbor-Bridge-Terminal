"""Trusted-time integration (v6).

Freshness/expiry decisions consume a ``TimeReading`` from ``TrustedClock`` -
never ``time.time()`` directly.  The clock combines:

* signed time attestations (``PK_TIME_ATTESTATION/1``) issued by a pinned time
  authority, namespaced to site/device, sequence-numbered (anti-replay) and
  expiring;
* a monotonic process clock to advance between attestations;
* a persisted, signed-by-nobody-but-monotonic ``floor`` (last trusted time)
  that survives restart, so a wall clock set backwards can never re-open
  expired certificates, snapshots, exceptions or signatures (CLOCK_ROLLBACK).

Uncertainty grows with time since the last attestation (drift ppm); when it
exceeds the per-control budget the clock refuses (TIME_UNTRUSTED / TIME_STALE).
Tests inject time through the explicit ``monotonic``/``wall`` callables; there
is no global override, and ``production=True`` rejects a reference authority.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from . import algorithms as algs
from .canonical import b64u_decode, b64u_encode, canonical_bytes, exact_fields, ld_encode
from .errors import fail

TIME_SCHEMA = "PK_TIME_ATTESTATION/1"


@dataclass(frozen=True)
class TimeReading:
    value: int               # trusted unix seconds
    uncertainty_s: float     # +/- bound
    source: str              # e.g. "attestation:time-authority-1#seq=42"
    last_sync: int

    def evidence(self) -> dict[str, Any]:
        return {"trusted_time": self.value, "uncertainty_ms": int(self.uncertainty_s * 1000),
                "source": self.source, "last_sync": self.last_sync}


@dataclass(frozen=True)
class TimeBudget:
    max_uncertainty_s: float = 5.0
    max_offline_s: int = 7 * 24 * 3600


class TimeAuthority:
    """Issues signed time attestations (runs at the control plane / secure time server)."""

    def __init__(self, authority_id: str, alg: str, signer: Callable[[bytes], bytes]):
        self.authority_id = authority_id
        self.alg = alg
        self._sign = signer
        self._seq = 0

    def attest(self, site: str, device: str, now: int, *, uncertainty_ms: int = 50, ttl_s: int = 300) -> dict[str, Any]:
        self._seq += 1
        body = {"schema": TIME_SCHEMA, "authority": self.authority_id, "alg": self.alg, "site": site, "device": device,
                "sequence": self._seq, "time": now, "uncertainty_ms": uncertainty_ms, "expires": now + ttl_s}
        return {**body, "sig": b64u_encode(self._sign(_time_message(body)))}


def _time_message(body: Mapping[str, Any]) -> bytes:
    return ld_encode("time-attestation/1", [(k, body[k]) for k in ("schema", "authority", "alg", "site", "device", "sequence", "time", "uncertainty_ms", "expires")])


class TrustedClock:
    def __init__(self, *, site: str, device: str, authorities: Mapping[str, tuple[str, bytes]],
                 state_path: str | None = None, drift_ppm: float = 50.0,
                 monotonic: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time,
                 max_forward_jump_s: int = 3600, max_restart_gap_s: int = 30 * 86400, production: bool = True):
        self.site, self.device = site, device
        self._auth = dict(authorities)  # authority_id -> (alg, spki)
        self._state_path = state_path
        self._drift = drift_ppm / 1e6
        self._mono, self._wall = monotonic, wall
        self._max_jump = max_forward_jump_s
        self._max_restart_gap = max_restart_gap_s
        self._production = production
        self._lock = threading.Lock()
        self._anchor: tuple[int, float, float, str, int] | None = None  # (time, mono, base_unc, source, sync)
        self._last_seq: dict[str, int] = {}
        self._floor = 0
        self._load_state()

    # persistence --------------------------------------------------------
    def _load_state(self) -> None:
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "rb") as fh:
                data = json.loads(fh.read(65536))
            self._floor = int(data["floor"])
            self._last_seq = {str(k): int(v) for k, v in data["last_seq"].items()}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise fail("TIME_UNTRUSTED", "persisted trusted-time state is corrupt; operator recovery required") from exc

    def _save_state(self) -> None:
        if not self._state_path:
            return
        tmp = self._state_path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(canonical_bytes({"floor": self._floor, "last_seq": self._last_seq}))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._state_path)

    # ingestion ----------------------------------------------------------
    def ingest(self, attestation: Mapping[str, Any]) -> TimeReading:
        a = exact_fields(attestation, {"schema", "authority", "alg", "site", "device", "sequence", "time", "uncertainty_ms", "expires", "sig"}, what="time attestation")
        if a["schema"] != TIME_SCHEMA:
            raise fail("TIME_UNTRUSTED", "unsupported time attestation schema")
        pinned = self._auth.get(a["authority"])
        if pinned is None or pinned[0] != a["alg"]:
            raise fail("TIME_UNTRUSTED", "time attestation from unpinned authority/algorithm")
        if a["site"] != self.site or a["device"] != self.device:
            raise fail("TENANT_MISMATCH", "time attestation namespaced to another site/device")
        for k in ("sequence", "time", "uncertainty_ms", "expires"):
            if isinstance(a[k], bool) or not isinstance(a[k], int) or a[k] < 0:
                raise fail("ENVELOPE_MALFORMED", f"time attestation field {k} invalid")
        algs.verify_raw(a["alg"], pinned[1], b64u_decode(a["sig"]), _time_message(a),
                        profile=algs.PROFILE_PRODUCTION if self._production else algs.PROFILE_REFERENCE)
        with self._lock:
            if a["sequence"] <= self._last_seq.get(a["authority"], 0):
                raise fail("REPLAY", "time attestation sequence replayed/rewound")
            if a["time"] < self._floor:
                raise fail("CLOCK_ROLLBACK", "attested time is behind persisted trusted floor", floor=self._floor, attested=a["time"])
            if a["time"] > a["expires"]:
                raise fail("TIME_UNTRUSTED", "time attestation already expired")
            if self._anchor is None and self._floor and a["time"] - self._floor > self._max_restart_gap:
                raise fail("CLOCK_JUMP", "first attestation after restart is implausibly far past the persisted floor",
                           floor=self._floor, attested=a["time"])
            if self._anchor is not None:
                predicted = self._current_unlocked()[0]
                if a["time"] - predicted > self._max_jump:
                    raise fail("CLOCK_JUMP", "implausible forward jump in attested time", predicted=predicted, attested=a["time"])
            self._last_seq[a["authority"]] = a["sequence"]
            self._anchor = (a["time"], self._mono(), a["uncertainty_ms"] / 1000.0, f"attestation:{a['authority']}#seq={a['sequence']}", a["time"])
            self._floor = max(self._floor, a["time"])
            self._save_state()
            return self._reading_unlocked()

    # reading ------------------------------------------------------------
    def _current_unlocked(self) -> tuple[int, float]:
        if self._anchor is None:
            raise fail("TIME_UNTRUSTED", "no trusted time attestation ingested")
        t0, m0, u0, _, _ = self._anchor
        elapsed = max(0.0, self._mono() - m0)
        return int(t0 + elapsed), u0 + elapsed * self._drift

    def _reading_unlocked(self) -> TimeReading:
        value, unc = self._current_unlocked()
        return TimeReading(value, unc, self._anchor[3], self._anchor[4])  # type: ignore[index]

    def now(self, budget: TimeBudget | None = None) -> TimeReading:
        budget = budget or TimeBudget()
        with self._lock:
            if self._anchor is None:
                raise fail("TIME_UNTRUSTED", "no trusted time attestation ingested")
            reading = self._reading_unlocked()
            if reading.value < self._floor:
                raise fail("CLOCK_ROLLBACK", "trusted time behind floor")
            if reading.value - reading.last_sync > budget.max_offline_s:
                raise fail("TIME_STALE", "trusted time offline budget exceeded", last_sync=reading.last_sync, budget_s=budget.max_offline_s)
            if reading.uncertainty_s > budget.max_uncertainty_s:
                raise fail("TIME_UNTRUSTED", "time uncertainty exceeds budget", uncertainty_s=reading.uncertainty_s, budget_s=budget.max_uncertainty_s)
            if reading.value > self._floor:
                self._floor = reading.value
            # wall clock is diagnostic only: detect local rollback for telemetry
            wall = int(self._wall())
            if wall + 300 < self._floor:
                reading = TimeReading(reading.value, reading.uncertainty_s, reading.source + ";wall_clock_behind", reading.last_sync)
            return reading

    def ready(self, budget: TimeBudget | None = None) -> tuple[bool, str]:
        try:
            self.now(budget)
            return True, "ok"
        except Exception as exc:  # noqa: BLE001
            return False, getattr(exc, "code", "TIME_UNTRUSTED")

    @property
    def floor(self) -> int:
        return self._floor


class FixedClock:
    """Deterministic test clock with the TrustedClock ``now`` interface.  Never production."""

    production = False

    def __init__(self, t: int, uncertainty_s: float = 0.0):
        self.t = t
        self.u = uncertainty_s

    def now(self, budget: TimeBudget | None = None) -> TimeReading:
        budget = budget or TimeBudget()
        if self.u > budget.max_uncertainty_s:
            raise fail("TIME_UNTRUSTED", "time uncertainty exceeds budget")
        return TimeReading(self.t, self.u, "fixed-test-clock", self.t)

    def ready(self, budget: TimeBudget | None = None) -> tuple[bool, str]:
        return True, "ok"

    def advance(self, s: int) -> None:
        self.t += s
