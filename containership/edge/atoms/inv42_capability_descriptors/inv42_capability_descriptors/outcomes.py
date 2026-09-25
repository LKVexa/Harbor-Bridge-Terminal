"""MC-010 - formal operation outcome taxonomy for INV-42.

Every public operation ends in exactly one outcome class.  The class, not the
exception text, is the contract callers program against.

* ``success``   - the operation took effect.
* ``terminal``  - retrying the same request can never succeed; the caller must
                  obtain a new descriptor or stop.
* ``retryable`` - the same request may succeed later without caller change
                  (capacity freed); callers retry with bounded backoff.
* ``degraded``  - the component is deliberately refusing service (emergency
                  disable, key service down); retry only after operator action.

There is no partial outcome: every operation is atomic under the table lock, so
an error never leaves a half-committed allocation or close.  The runtime has no
blocking I/O, therefore it has no timeouts or cancellation points of its own;
callers enforce deadlines around it.  Backpressure is expressed as
``table_full`` (retryable) and ``session_exhausted`` (terminal for the session:
destroy and create a new table).
"""
from __future__ import annotations

from dataclasses import dataclass

SUCCESS, TERMINAL, RETRYABLE, DEGRADED = "success", "terminal", "retryable", "degraded"

TAXONOMY: dict[str, tuple[str, str]] = {
    # code: (class, operator action)
    "ok": (SUCCESS, "none"),
    "invalid_descriptor": (TERMINAL, "treat payload as hostile; do not retry"),
    "foreign_descriptor": (TERMINAL, "route descriptor to its issuing table or re-issue"),
    "descriptor_closed": (TERMINAL, "descriptor revoked; obtain a fresh one"),
    "type_mismatch": (TERMINAL, "caller bug or attack; fix expected type"),
    "table_full": (RETRYABLE, "close unused descriptors; retry with backoff"),
    "session_exhausted": (TERMINAL, "destroy table and start a new session"),
    "forked_table": (TERMINAL, "create a new table in the child process"),
    "table_destroyed": (TERMINAL, "create a new table"),
    "component_disabled": (DEGRADED, "wait for operator to release emergency disable"),
    "key_unavailable": (DEGRADED, "restore key provider; table was not created"),
    "invalid_argument": (TERMINAL, "fix caller input"),
}

RETRY_POLICY = {"max_attempts": 5, "base_delay_s": 0.01, "max_delay_s": 1.0, "jitter": "full"}


@dataclass(frozen=True)
class Outcome:
    code: str
    klass: str
    action: str

    @property
    def retryable(self) -> bool:
        return self.klass == RETRYABLE


def classify(error: BaseException | None) -> Outcome:
    """Map an exception (or None for success) to its formal outcome."""
    if error is None:
        code = "ok"
    else:
        code = getattr(error, "code", None) or ("invalid_argument" if isinstance(error, ValueError) else "internal_error")
    klass, action = TAXONOMY.get(code, (TERMINAL, "unclassified failure: page owner"))
    return Outcome(code, klass, action)
