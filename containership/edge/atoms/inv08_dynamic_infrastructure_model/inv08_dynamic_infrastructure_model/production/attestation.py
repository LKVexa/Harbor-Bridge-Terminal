"""Component 35 - node/workload attestation (contract ``PK_DYN_ATTEST/1``).

Evidence (canonical JSON object, all fields required)::

  {"schema": "PK_DYN_ATTEST/1", "node_id": str, "nonce": hex32, "ts": number,
   "rot": {"type": "tpm2"|"sev-snp"|"tdx"|"sim", "device_id": str, "ek_digest": "sha256:<hex>"},
   "pcrs": {"<int 0..23>": "<sha256 hex>"},
   "event_log": [{"pcr": int, "digest": "<sha256 hex>", "desc": str}],
   "quote": <signature dict over every field above except "quote">}

Invariants: the quote is produced by the device's attestation key; replaying the
event log (PCR_new = sha256(PCR_old || digest), PCR_0 = 32 zero bytes) reproduces
``pcrs``; the nonce was issued by this verifier, is unexpired and used once.

Only ``rot.type == "sim"`` evidence is producible here: the device key is an HMAC
key in a ``core.TrustRoot`` (``SimulatedDevice``).  Real TPM2/SEV-SNP/TDX quote
verification (EK certificate chain, vendor roots) is BLOCKED on hardware and vendor
root certificates.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .core import Inv08Error, Outcome, TrustRoot, canonical

SCHEMA = "PK_DYN_ATTEST/1"
ROT_TYPES = ("tpm2", "sev-snp", "tdx", "sim")
SUPPORTED_ROT = ("sim",)  # others BLOCKED: hardware + vendor roots absent
ZERO_PCR = "00" * 32
MAX_EVENTS = 4096


class Action(str, Enum):
    ADMIT = "ADMIT"
    DEGRADE = "DEGRADE"       # keep running existing leases, no new work, re-attest
    QUARANTINE = "QUARANTINE"  # drain + isolate for forensics, no reclaim of evidence
    DENY = "DENY"             # never admit


# failure reason -> action; unknown reasons fail closed to DENY
ACTION_POLICY = {
    "stale_nonce": Action.DEGRADE,
    "evidence_too_old": Action.DEGRADE,
    "unknown_nonce": Action.DENY,
    "nonce_replay": Action.QUARANTINE,
    "bad_quote": Action.QUARANTINE,
    "pcr_mismatch": Action.QUARANTINE,
    "event_log_mismatch": Action.QUARANTINE,
    "unsupported_rot": Action.DENY,
    "rot_not_allowed": Action.DENY,
    "malformed": Action.DENY,
}
_SEVERITY = [Action.ADMIT, Action.DEGRADE, Action.QUARANTINE, Action.DENY]


def extend(pcr_hex: str, event_digest_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(pcr_hex) + bytes.fromhex(event_digest_hex)).hexdigest()


def replay_event_log(events: list[dict]) -> dict[str, str]:
    pcrs: dict[str, str] = {}
    for ev in events:
        k = str(ev["pcr"])
        pcrs[k] = extend(pcrs.get(k, ZERO_PCR), ev["digest"])
    return pcrs


class NonceIssuer:
    """Single-use, time-bounded challenge nonces (bounded outstanding set)."""

    def __init__(self, clock: Callable[[], float], rng: random.Random, ttl: float = 30.0,
                 max_outstanding: int = 10000) -> None:
        self._clock, self._rng, self.ttl, self.max = clock, rng, ttl, max_outstanding
        self._out: dict[str, float] = {}
        self._used: set[str] = set()

    def issue(self) -> str:
        now = self._clock()
        self._out = {n: t for n, t in self._out.items() if now - t <= self.ttl}
        if len(self._out) >= self.max:
            raise Inv08Error("INV08.ATTEST.NONCE_EXHAUSTED", "too many outstanding challenges",
                             outcome=Outcome.RETRYABLE_FAILURE)
        n = "%032x" % self._rng.getrandbits(128)
        self._out[n] = now
        return n

    def consume(self, nonce: str) -> str | None:
        """Return None if fresh, else failure reason."""
        if nonce in self._used:
            return "nonce_replay"
        t = self._out.pop(nonce, None)
        if t is None:
            return "unknown_nonce"
        self._used.add(nonce)
        if self._clock() - t > self.ttl:
            return "stale_nonce"
        return None


@dataclass
class AttestationPolicy:
    allowed_rot: tuple[str, ...] = ("sim",)
    golden_pcrs: dict[str, str] = field(default_factory=dict)  # required values
    max_evidence_age: float = 60.0

    def __post_init__(self) -> None:
        for r in self.allowed_rot:
            if r not in ROT_TYPES:
                raise ValueError(f"unknown RoT type {r}")
        for k, v in self.golden_pcrs.items():
            if not (k.isdigit() and 0 <= int(k) <= 23 and len(v) == 64):
                raise ValueError(f"bad golden PCR {k}={v}")


@dataclass
class Verdict:
    node_id: str
    action: Action
    reasons: list[str]

    @property
    def admitted(self) -> bool:
        return self.action is Action.ADMIT


def _signed_part(ev: dict) -> dict:
    return {k: v for k, v in ev.items() if k != "quote"}


def _req(cond: object) -> None:
    if not cond:  # explicit check: must survive python -O (no assert)
        raise ValueError("malformed evidence")


def _well_formed(ev: object) -> bool:
    try:
        _req(isinstance(ev, dict) and ev["schema"] == SCHEMA)
        _req(isinstance(ev["node_id"], str) and ev["node_id"])
        _req(isinstance(ev["nonce"], str) and isinstance(ev["ts"], (int, float)))
        _req(ev["rot"]["type"] in ROT_TYPES and isinstance(ev["rot"]["device_id"], str))
        _req(isinstance(ev["pcrs"], dict) and isinstance(ev["event_log"], list))
        _req(len(ev["event_log"]) <= MAX_EVENTS)
        for e in ev["event_log"]:
            _req(isinstance(e["pcr"], int) and 0 <= e["pcr"] <= 23)
            bytes.fromhex(e["digest"])
            _req(len(e["digest"]) == 64)
        for v in ev["pcrs"].values():
            bytes.fromhex(v)
        _req(isinstance(ev["quote"], dict))
        canonical(ev)  # rejects NaN/inf and non-str keys
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


class AttestationVerifier:
    """Evaluates evidence against policy; device keys live in ``trust`` (kid = device_id)."""

    def __init__(self, trust: TrustRoot, nonces: NonceIssuer, policy: AttestationPolicy,
                 clock: Callable[[], float], audit=None) -> None:
        self.trust, self.nonces, self.policy, self.clock, self.audit = trust, nonces, policy, clock, audit
        self.node_state: dict[str, Action] = {}

    def evaluate(self, ev: object) -> Verdict:
        reasons: list[str] = []
        if not _well_formed(ev):
            node = ev.get("node_id", "?") if isinstance(ev, dict) else "?"
            return self._finish(str(node), ["malformed"])
        rot = ev["rot"]["type"]
        if rot not in SUPPORTED_ROT:
            reasons.append("unsupported_rot")
        elif rot not in self.policy.allowed_rot:
            reasons.append("rot_not_allowed")
        if ev["quote"].get("kid") != ev["rot"]["device_id"] or not self.trust.verify(_signed_part(ev), ev["quote"]):
            reasons.append("bad_quote")
        nr = self.nonces.consume(ev["nonce"])
        if nr:
            reasons.append(nr)
        if self.clock() - ev["ts"] > self.policy.max_evidence_age:
            reasons.append("evidence_too_old")
        if replay_event_log(ev["event_log"]) != ev["pcrs"]:
            reasons.append("event_log_mismatch")
        for k, want in self.policy.golden_pcrs.items():
            if ev["pcrs"].get(k) != want:
                reasons.append("pcr_mismatch")
                break
        return self._finish(ev["node_id"], reasons)

    def _finish(self, node: str, reasons: list[str]) -> Verdict:
        action = Action.ADMIT
        for r in reasons:
            a = ACTION_POLICY.get(r, Action.DENY)
            if _SEVERITY.index(a) > _SEVERITY.index(action):
                action = a
        self.node_state[node] = action
        if self.audit is not None:
            self.audit.append("attestation-verifier", "attest", node,
                              "SUCCESS" if action is Action.ADMIT else action.value, {"reasons": reasons})
        return Verdict(node, action, reasons)

    def schedulable(self, node_id: str) -> bool:
        """Only ADMIT nodes may receive new leases; unknown nodes fail closed."""
        return self.node_state.get(node_id) is Action.ADMIT


class SimulatedDevice:
    """Test double for a node with an HMAC 'attestation key'. NOT a hardware RoT."""

    def __init__(self, node_id: str, device_id: str, key: bytes, trust: TrustRoot) -> None:
        self.node_id, self.device_id, self.events = node_id, device_id, []
        self._trust = TrustRoot()
        self._trust.add(device_id, key)
        trust.add(device_id, key)  # verifier enrols the same key (simulated EK enrolment)

    def measure(self, pcr: int, blob: bytes, desc: str = "") -> None:
        self.events.append({"pcr": pcr, "digest": hashlib.sha256(blob).hexdigest(), "desc": desc})

    def quote(self, nonce: str, ts: float, *, pcr_override: dict | None = None) -> dict:
        ev = {"schema": SCHEMA, "node_id": self.node_id, "nonce": nonce, "ts": ts,
              "rot": {"type": "sim", "device_id": self.device_id,
                      "ek_digest": "sha256:" + hashlib.sha256(self.device_id.encode()).hexdigest()},
              "pcrs": pcr_override if pcr_override is not None else replay_event_log(self.events),
              "event_log": [dict(e) for e in self.events]}
        canonical(ev)
        ev["quote"] = self._trust.sign(self.device_id, ev)
        return ev
