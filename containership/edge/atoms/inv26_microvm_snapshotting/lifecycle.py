"""Normative snapshot lifecycle state machine (C015, C057, C059).

States are persisted by :mod:`metastore`; every transition goes through
:func:`check_transition`, so an illegal move is a stable
``SNAP_ILLEGAL_TRANSITION`` rather than an ad-hoc condition.

Snapshot (artifact) lifecycle::

    ABSENT -> CAPTURING -> CAPTURED -> VERIFYING -> AVAILABLE
    CAPTURING -> FAILED          (capture error; blob GC'd by reconcile)
    VERIFYING -> QUARANTINED     (integrity failure)
    AVAILABLE|CAPTURED|FAILED|QUARANTINED -> DELETING -> DELETED
    AVAILABLE <-> QUARANTINED    (operator; release needs snapshot.quarantine capability)

Restore (operation) lifecycle, per restore operation id::

    PENDING -> RESTORING -> RESEEDING -> READY
    RESTORING|RESEEDING -> FAILED   (guest is destroyed, never resumed)

``READY`` is reachable only from ``RESEEDING`` and only after the entropy
injector acknowledged the seed — the guarantee required by C015.

Crash recovery (C057): a record found in a *transient* state after restart is
resolved by :func:`recovery_action`; nothing transient is ever treated as
committed.
"""
from __future__ import annotations

from .errors import SnapshotServiceError

SNAPSHOT_STATES = ("ABSENT", "CAPTURING", "CAPTURED", "VERIFYING", "AVAILABLE", "FAILED",
                   "QUARANTINED", "DELETING", "DELETED")
RESTORE_STATES = ("PENDING", "RESTORING", "RESEEDING", "READY", "FAILED")

SNAPSHOT_TRANSITIONS: dict[str, frozenset[str]] = {
    "ABSENT": frozenset({"CAPTURING"}),
    "CAPTURING": frozenset({"CAPTURED", "FAILED"}),
    "CAPTURED": frozenset({"VERIFYING", "DELETING", "FAILED"}),
    "VERIFYING": frozenset({"AVAILABLE", "QUARANTINED", "FAILED"}),
    "AVAILABLE": frozenset({"QUARANTINED", "DELETING"}),
    "QUARANTINED": frozenset({"AVAILABLE", "DELETING"}),
    "FAILED": frozenset({"DELETING"}),
    "DELETING": frozenset({"DELETED"}),
    "DELETED": frozenset(),
}

RESTORE_TRANSITIONS: dict[str, frozenset[str]] = {
    "PENDING": frozenset({"RESTORING", "FAILED"}),
    "RESTORING": frozenset({"RESEEDING", "FAILED"}),
    "RESEEDING": frozenset({"READY", "FAILED"}),
    "READY": frozenset(),
    "FAILED": frozenset(),
}

TRANSIENT_SNAPSHOT = frozenset({"CAPTURING", "CAPTURED", "VERIFYING", "DELETING"})
TRANSIENT_RESTORE = frozenset({"PENDING", "RESTORING", "RESEEDING"})
RESTORABLE = frozenset({"AVAILABLE"})

# Per-transition timeout budgets (seconds); a record stuck longer is a stall (C052).
STATE_TIMEOUT_S = {"CAPTURING": 120.0, "CAPTURED": 30.0, "VERIFYING": 60.0, "DELETING": 300.0,
                   "PENDING": 5.0, "RESTORING": 10.0, "RESEEDING": 2.0}


def check_transition(kind: str, current: str, target: str) -> None:
    table = SNAPSHOT_TRANSITIONS if kind == "snapshot" else RESTORE_TRANSITIONS
    if current not in table or target not in table.get(current, ()):
        raise SnapshotServiceError("SNAP_ILLEGAL_TRANSITION", f"{kind}: {current} -> {target}")


def recovery_action(kind: str, state: str) -> str | None:
    """Deterministic restart resolution for a record left in *state* (C057).

    Returns the state the reconciler must move the record to, or ``None`` when
    the state is stable. Rules: an interrupted capture never becomes
    restorable (FAILED, blob garbage-collected); an interrupted verification
    is re-run (back to VERIFYING via CAPTURED semantics -> FAILED is safer, so
    we choose FAILED and require re-capture); an interrupted delete is resumed;
    an interrupted restore is FAILED and its guest destroyed (never resumed).
    """
    if kind == "snapshot":
        return {"CAPTURING": "FAILED", "CAPTURED": "FAILED", "VERIFYING": "FAILED",
                "DELETING": "DELETED"}.get(state)
    return {"PENDING": "FAILED", "RESTORING": "FAILED", "RESEEDING": "FAILED"}.get(state)


def model_document() -> dict:
    return {
        "schema": "PK_SNAPSHOT_LIFECYCLE/1",
        "snapshot": {k: sorted(v) for k, v in SNAPSHOT_TRANSITIONS.items()},
        "restore": {k: sorted(v) for k, v in RESTORE_TRANSITIONS.items()},
        "transient_snapshot": sorted(TRANSIENT_SNAPSHOT),
        "transient_restore": sorted(TRANSIENT_RESTORE),
        "timeouts_s": STATE_TIMEOUT_S,
    }
