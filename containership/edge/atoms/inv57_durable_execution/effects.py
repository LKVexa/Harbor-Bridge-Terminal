"""External-effect protocol (SG-04).

Effect IDs are derived deterministically from the workflow identity and the
activity id (so they are known before anything runs) and persisted
(``prepared``) under the fencing lease after the ``started`` event commits and
strictly before dispatch.  Providers must implement::

    submit(effect_id, request) -> receipt      # conditional create keyed by effect_id
    lookup(effect_id) -> receipt | None        # authoritative status query

Classes:
  ``idempotent``   provider dedupes on effect_id; an in-doubt effect is
                   reconciled by lookup, then (if absent) by resubmission,
                   which cannot duplicate.
  ``lookup_only``  provider can report status but does not dedupe; in-doubt is
                   reconciled by lookup only; absence → EffectUnresolved.
  ``unsafe``       no dedupe, no lookup; in-doubt is always EffectUnresolved
                   and goes to an operator.  Compensation is never automatic.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from .durable import Worker, _default_activity_id
from .errors import EffectUnresolved
from .sqlite_store import SQLiteHistoryStore

EFFECT_CLASSES = frozenset({"idempotent", "lookup_only", "unsafe"})


class EffectProvider(Protocol):
    def submit(self, effect_id: str, request: Any) -> Any: ...
    def lookup(self, effect_id: str) -> Any | None: ...


def effect_id_for(store: SQLiteHistoryStore, activity_id: str) -> str:
    return "eff-" + hashlib.sha256(
        f"{store.identity.key()}#{activity_id}".encode()).hexdigest()[:32]


def run_effect(worker: Worker, name: str, provider: EffectProvider, request: Any, *,
               effect_class: str, activity_id: str | None = None) -> Any:
    store = worker.history_store
    if not isinstance(store, SQLiteHistoryStore):
        raise TypeError("run_effect requires a persistent SQLiteHistoryStore")
    if effect_class not in EFFECT_CLASSES:
        raise ValueError(f"effect_class must be one of {sorted(EFFECT_CLASSES)}")
    aid = activity_id or _default_activity_id(worker._step_pos, name)
    eid = effect_id_for(store, aid)
    req_text = json.dumps(request, sort_keys=True, separators=(",", ":"))
    fingerprint = f"effect:{effect_class}:" + hashlib.sha256(req_text.encode()).hexdigest()[:16]

    def dispatch() -> Any:
        store.backend.effect_prepare(store.lease, eid, aid, effect_class, req_text)
        receipt = provider.submit(eid, request)
        store.backend.effect_mark(store.lease, eid, "receipted", json.dumps(receipt))
        return receipt

    return worker.activity(name, dispatch, activity_id=aid, fingerprint=fingerprint)


def reconcile_in_doubt(worker: Worker, provider: EffectProvider) -> Any:
    """Establish the real outcome of the trailing in-doubt effect and record it."""
    store = worker.history_store
    events = store.events
    if not events or events[-1].kind != "started":
        raise EffectUnresolved("no trailing in-doubt activity")
    started = events[-1]
    eid = effect_id_for(store, started.activity_id)
    record = store.backend.effect_get(eid)
    if record is None:
        # started was committed but prepare never ran → dispatch never happened.
        raise EffectUnresolved("effect was never prepared; operator must decide (no dispatch occurred)")
    receipt = provider.lookup(eid) if record["effect_class"] != "unsafe" else None
    if receipt is None and record["effect_class"] == "idempotent":
        receipt = provider.submit(eid, json.loads(record["request"]))
    if receipt is None:
        raise EffectUnresolved(f"effect {eid} outcome unknown for class {record['effect_class']}")
    store.backend.effect_mark(store.lease, eid, "reconciled", json.dumps(receipt))
    worker.resolve_in_doubt(started.activity_id, receipt, name=started.name)
    return receipt
