"""Pure certification state machine: ledger events -> state -> verdict.

The append-only ledger is the source of truth; every table in the durable
store is a materialisation of ``apply()`` over ledger events, and every
verdict is a pure function ``certify(state, key, now, policy)``. That single
code path is what makes historical reconstruction (MC-02-04), explain
(MC-28-03) and post-restore verification (MC-15-05) produce the *same*
answer as the live decision.

Components realised here: lifecycle metadata model (20), negative-evidence
ageing (21), revocation/quarantine precedence (13), exact-key semantics
inherited from the v4.2.0 reference matrix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .timepolicy import effective_expiry

STATE_ENGINE_VERSION = "GAP15-STATE/1.0.0"

# verdicts (v4.2.0 vocabulary + production additions)
CERTIFIED, INCOMPATIBLE, UNTESTED, EXPIRED, END_OF_LIFE = "certified", "incompatible", "untested", "expired", "end-of-life"
REVOKED, QUARANTINED, RETEST_REQUIRED = "revoked", "quarantined", "retest-required"

# lifecycle (component 20)
ACTIVE, DEPRECATED, BLOCKED_FOR_NEW, EOL, LC_REVOKED, REACTIVATED = (
    "active", "deprecated", "blocked-for-new", "end-of-life", "revoked", "reactivated-by-waiver")
LIFECYCLE_TRANSITIONS = {
    None: {ACTIVE, DEPRECATED, BLOCKED_FOR_NEW, EOL},
    ACTIVE: {DEPRECATED, BLOCKED_FOR_NEW, EOL, LC_REVOKED},
    DEPRECATED: {BLOCKED_FOR_NEW, EOL, LC_REVOKED, REACTIVATED},
    BLOCKED_FOR_NEW: {EOL, LC_REVOKED, REACTIVATED},
    EOL: {LC_REVOKED, REACTIVATED},
    REACTIVATED: {EOL, LC_REVOKED, DEPRECATED},
    LC_REVOKED: set(),  # terminal: a revoked runtime needs a new identity
}

# negative-evidence classes (component 21): class -> (ttl seconds or None=authoritative, min retest backoff)
FAILURE_CLASSES = {
    "deterministic": (None, 0),
    "security-policy": (None, 0),
    "performance": (7 * 86400, 3600),
    "transient": (3600, 300),
    "flaky": (3600, 900),
    "harness-defect": (0, 60),
}


class StateError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class CertKey:
    partition: str
    artifact_digest: str
    runtime: str  # name@version
    profile_id: str

    def as_dict(self) -> dict:
        return {"partition": self.partition, "artifact_digest": self.artifact_digest,
                "runtime": self.runtime, "profile_id": self.profile_id}


@dataclass(frozen=True)
class CertPolicy:
    ttl_s: int = 500  # v4.2.0 CERTIFICATION_TTL_SECONDS preserved as default
    offline_grace_s: int = 0
    revision: str = "policy:1"


@dataclass
class State:
    seq: int = 0
    revision: int = 0
    evidence: dict = field(default_factory=dict)  # CertKey -> latest accepted envelope
    history: dict = field(default_factory=dict)  # CertKey -> [evidence_id ...]
    lifecycle: dict = field(default_factory=dict)  # (partition, runtime) -> [event ...]
    revocations: dict = field(default_factory=dict)  # (subject_type, subject_id) -> event
    conflicts: dict = field(default_factory=dict)  # CertKey -> {case_id: latest conflict event}


def key_of(env: dict) -> CertKey:
    return CertKey(env["partition"], env["artifact_digest"], env["runtime"], env["profile_id"])


def lifecycle_at(state: State, partition: str, runtime: str, now: int) -> Optional[dict]:
    events = [e for e in state.lifecycle.get((partition, runtime), []) if e["effective_at"] <= now]
    events += [e for e in state.lifecycle.get(("*", runtime), []) if e["effective_at"] <= now]
    if not events:
        return None
    return max(events, key=lambda e: (e["effective_at"], e["seq"]))


def check_transition(state: State, ev: dict) -> None:
    history = state.lifecycle.get((ev["partition"], ev["runtime"]), [])
    current = max(history, key=lambda e: (e["effective_at"], e["seq"]))["state"] if history else None
    if ev["state"] == current:
        return
    if ev["state"] not in LIFECYCLE_TRANSITIONS.get(current, set()):
        raise StateError("E_LIFECYCLE_TRANSITION", f"{current!r} -> {ev['state']!r} is not a legal transition")
    if ev["state"] == REACTIVATED and not ev.get("waiver_id"):
        raise StateError("E_LIFECYCLE_WAIVER_REQUIRED", "reactivation requires a signed waiver record")


def apply(state: State, event: dict) -> State:
    """Apply one ledger event. Raises ``StateError`` on an illegal event (never partially)."""
    et = event["event_type"]
    seq = event["seq"]
    if seq <= state.seq:
        raise StateError("E_LEDGER_ORDER", f"event seq {seq} not after {state.seq}")
    if et == "evidence":
        k = key_of(event)
        prev = state.evidence.get(k)
        if prev is not None:
            if event["observed_at"] < prev["observed_at"]:
                raise StateError("E_EVIDENCE_STALE", "older evidence cannot replace newer evidence")
            if event["observed_at"] == prev["observed_at"] and event["result"] != prev["result"]:
                raise StateError("E_EVIDENCE_CONTRADICTION", "contradictory evidence at the same observed time")
        state.evidence[k] = event
        state.history.setdefault(k, []).append(event["evidence_id"])
        state.revision += 1
    elif et == "lifecycle":
        check_transition(state, event)
        state.lifecycle.setdefault((event["partition"], event["runtime"]), []).append(event)
        state.revision += 1
    elif et in ("revoke", "quarantine", "reinstate"):
        k = (event["subject_type"], event["subject_id"])
        if et == "reinstate" and k not in state.revocations:
            raise StateError("E_REVOCATION_NONE", "nothing to reinstate")
        if et == "reinstate" and state.revocations[k]["event_type"] == "revoke" and not event.get("second_approver"):
            raise StateError("E_REVOCATION_SOD", "reversing a revocation needs a second approver")
        state.revocations[k] = event
        state.revision += 1
    elif et == "conflict":
        cases = state.conflicts.setdefault(key_of(event), {})
        if event.get("status") == "resolved" and event["case_id"] not in cases:
            raise StateError("E_CONFLICT_UNKNOWN_CASE", event["case_id"])
        cases[event["case_id"]] = event  # latest record per case; history stays in the ledger
        state.revision += 1
    elif et in ("waiver", "note", "checkpoint"):
        pass  # recorded in the ledger; interpreted by policy/waiver registry
    else:
        raise StateError("E_EVENT_TYPE", et)
    state.seq = seq
    return state


def replay(events: list, *, upto_seq: Optional[int] = None) -> State:
    state = State()
    for ev in sorted(events, key=lambda e: e["seq"]):
        if upto_seq is not None and ev["seq"] > upto_seq:
            break
        apply(state, ev)
    return state


def _revocation_hit(state: State, key: CertKey, now: int, extra_subjects: tuple = ()) -> Optional[dict]:
    env = state.evidence.get(key)
    subjects = [("artifact", key.artifact_digest), ("runtime", key.runtime), ("profile", key.profile_id)]
    if env is not None:
        subjects += [("evidence", env["evidence_id"]), ("signer", env.get("signer_key_id", "")),
                     ("producer", env.get("producer", ""))]
    subjects += list(extra_subjects)
    hits = []
    for s in subjects:
        ev = state.revocations.get(s)
        if ev and ev["event_type"] != "reinstate" and ev["effective_at"] <= now and (
                ev.get("expires_at") is None or now < ev["expires_at"]):
            hits.append(ev)
    if not hits:
        return None
    return sorted(hits, key=lambda e: (e["event_type"] != "revoke", e["seq"]))[0]


def certify(state: State, key: CertKey, now: int, policy: CertPolicy = CertPolicy(), *,
            new_admission: bool = True, extra_subjects: tuple = ()) -> dict:
    """The one verdict function. Precedence: revocation > quarantine > conflict > lifecycle > evidence."""
    if isinstance(now, bool) or not isinstance(now, int) or now < 0:
        raise StateError("E_TIME_INVALID", "now must be a non-negative integer")
    trace: list = []
    base = {"schema": "PK_CERTIFICATION/1", "engine": STATE_ENGINE_VERSION, "key": key.as_dict(),
            "environment": key.partition.split("/")[1] if key.partition.count("/") == 2 else key.partition,
            "matrix_revision": state.revision, "ledger_seq": state.seq, "policy_revision": policy.revision,
            "evaluated_at": now, "trace": trace}

    def out(verdict: str, reason_code: str, reason: str, deployable: bool = False, **extra) -> dict:
        trace.append({"rule": "final", "verdict": verdict, "reason_code": reason_code})
        return {**base, "verdict": verdict, "reason_code": reason_code, "reason": reason,
                "deployable": deployable, **extra}

    hit = _revocation_hit(state, key, now, extra_subjects)
    trace.append({"rule": "revocation", "matched": bool(hit)})
    if hit:
        verdict = REVOKED if hit["event_type"] == "revoke" else QUARANTINED
        return out(verdict, "R_" + verdict.upper(), f"{hit['subject_type']} {hit['subject_id']} is {verdict}: {hit.get('reason', '')}",
                   revocation_seq=hit["seq"])
    if state.conflicts.get(key):
        open_cases = [c for c in state.conflicts[key].values() if c.get("status", "open") == "open"]
        trace.append({"rule": "conflict", "open": len(open_cases)})
        if open_cases:
            return out(QUARANTINED, "R_CONFLICT", "unresolved evidence conflict; scope quarantined",
                       conflict_case=open_cases[-1]["case_id"])
    lc = lifecycle_at(state, key.partition, key.runtime, now)
    lc_state = lc["state"] if lc else ACTIVE
    trace.append({"rule": "lifecycle", "state": lc_state, "seq": lc["seq"] if lc else None})
    base["lifecycle"] = {"state": lc_state, "event_seq": lc["seq"] if lc else None,
                         "replacement": lc.get("replacement") if lc else None,
                         "waiver_id": lc.get("waiver_id") if lc else None}
    base["deprecated"] = lc_state == DEPRECATED
    if lc_state in (EOL, LC_REVOKED):
        return out(END_OF_LIFE, "R_EOL", f"runtime {key.runtime} is {lc_state}")
    if lc_state == BLOCKED_FOR_NEW and new_admission:
        return out(END_OF_LIFE, "R_BLOCKED_FOR_NEW", f"runtime {key.runtime} accepts no new admissions")

    env = state.evidence.get(key)
    trace.append({"rule": "evidence", "evidence_id": env["evidence_id"] if env else None})
    if env is None:
        return out(UNTESTED, "R_NO_EVIDENCE", "no recorded test result for this exact key; compatibility is not inferred")
    tested_at = env["observed_at"]
    ev_meta = {"evidence_id": env["evidence_id"], "tested_at": tested_at, "age": now - tested_at,
               "evidence_history": list(state.history.get(key, []))}
    if tested_at > now:
        return out(UNTESTED, "R_FUTURE_EVIDENCE", f"evidence observed at {tested_at} is later than now ({now})", **ev_meta)
    if env["result"] == "incompatible":
        cls = env.get("failure_class", "deterministic")
        ttl, backoff = FAILURE_CLASSES.get(cls, (None, 0))
        trace.append({"rule": "negative-ageing", "class": cls, "ttl": ttl})
        if ttl is None:
            return out(INCOMPATIBLE, "R_INCOMPATIBLE", f"tested incompatible ({cls}) at {tested_at}; authoritative until inputs change",
                       failure_class=cls, next_retest_at=None, **ev_meta)
        if now - tested_at > ttl:
            return out(RETEST_REQUIRED, "R_NEGATIVE_AGED", f"{cls} failure older than {ttl}s; retest required (never implies compatible)",
                       failure_class=cls, next_retest_at=tested_at + backoff, **ev_meta)
        return out(INCOMPATIBLE, "R_INCOMPATIBLE", f"tested incompatible ({cls}) at {tested_at}",
                   failure_class=cls, next_retest_at=tested_at + max(ttl, backoff), **ev_meta)
    eol_at = None
    for e in state.lifecycle.get((key.partition, key.runtime), []):
        if e["state"] == EOL and e["effective_at"] > now:
            eol_at = e["effective_at"] if eol_at is None else min(eol_at, e["effective_at"])
    expires_at = effective_expiry(tested_at, policy.ttl_s, eol_at=eol_at, offline_grace_s=policy.offline_grace_s)
    ev_meta["expires_at"] = expires_at
    if now > expires_at:
        return out(EXPIRED, "R_EXPIRED", f"certified at {tested_at}, expired at {expires_at}", **ev_meta)
    return out(CERTIFIED, "R_CERTIFIED", f"tested compatible at {tested_at}", True, **ev_meta)
