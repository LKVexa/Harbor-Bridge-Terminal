"""G13-MC-008 replay and downgrade protection.

The anti-rollback floor is kept per ``(issuer, policy_id, environment)``
namespace and persisted atomically.  Unreadable/corrupt state raises
``AntiReplayStateUnavailable`` -- it is never silently reset to zero.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .bundle import PolicyBundle, SUPPORTED_BUNDLE_SCHEMAS
from .errors import AntiReplayStateUnavailable, ReplayRejected
from .storage import Corrupt, read_record, write_record

KIND = "PK_POLICY_ANTIREPLAY/1"


def _ns(b: PolicyBundle) -> str:
    return f"{b.issuer}|{b.policy_id}|{b.environment}"


class AntiReplayState:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {"namespaces": {}}
        if self.path is not None:
            try:
                body = read_record(self.path, kind=KIND)
            except Corrupt as exc:
                raise AntiReplayStateUnavailable(f"anti-replay state corrupt: {exc}") from exc
            except OSError as exc:
                raise AntiReplayStateUnavailable(f"anti-replay state unreadable: {exc}") from exc
            if body is not None:
                self._state = body

    def floor(self, bundle: PolicyBundle) -> dict[str, Any] | None:
        return self._state["namespaces"].get(_ns(bundle))

    def check(self, bundle: PolicyBundle, *, rollback_authorized: bool = False) -> str:
        """Return ``new``/``benign-replay``; raise ``ReplayRejected`` otherwise."""
        rec = self.floor(bundle)
        if bundle.schema not in SUPPORTED_BUNDLE_SCHEMAS:
            raise ReplayRejected("schema downgrade/unknown schema")
        if rec is None:
            return "new"
        seen = rec["seen"]
        prior = seen.get(str(bundle.generation))
        if prior is not None and prior != bundle.digest:
            raise ReplayRejected("same generation with different digest (collision/substitution)",
                                 details={"generation": bundle.generation})
        if bundle.generation == rec["generation"] and bundle.digest == rec["digest"]:
            return "benign-replay"
        if bundle.generation <= rec["generation"]:
            if rollback_authorized and prior == bundle.digest:
                return "authorized-rollback"
            raise ReplayRejected(f"generation {bundle.generation} is at/below anti-rollback floor {rec['generation']}",
                                 details={"floor": rec["generation"], "received": bundle.generation})
        return "new"

    def commit(self, bundle: PolicyBundle, *, fault: Any = None) -> None:
        with self._lock:
            ns = _ns(bundle)
            rec = self._state["namespaces"].get(ns, {"generation": 0, "digest": None, "seen": {}})
            new = {"generation": max(rec["generation"], bundle.generation),
                   "digest": bundle.digest if bundle.generation >= rec["generation"] else rec["digest"],
                   "seen": dict(rec["seen"])}
            new["seen"][str(bundle.generation)] = bundle.digest
            # bound history
            if len(new["seen"]) > 64:
                for k in sorted(new["seen"], key=int)[:-64]:
                    del new["seen"][k]
            state = {"namespaces": {**self._state["namespaces"], ns: new}}
            if self.path is not None:
                write_record(self.path, state, kind=KIND, fault=fault)   # durable first
            self._state = state

    def status(self) -> dict[str, Any]:
        return {ns: {"generation": r["generation"], "digest": r["digest"]}
                for ns, r in self._state["namespaces"].items()}
