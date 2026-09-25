"""MC16 - Production conflict-resolution adapter (port to GAP-13 policy engine).

The adapter sends a ``PK_CONFLICT_SET/1`` plus policy context to an injected policy
client and expects ``{"decision": "resolve", "value": str, "policy_version": str,
"evidence": {...}}`` or ``{"decision": "defer"}``.  Timeouts and errors are retried with
bounded, deterministic backoff (no wall-clock sleeps in the decision path; the sleep
function is injected).  If the policy owner stays unavailable, the conflict **stays
open** - the adapter never falls back to picking a winner itself.  The decision is only
applied if the conflict frontier is unchanged since the request (optimistic check on a
frontier digest), so a late decision cannot overwrite writes it never saw.
"""
from __future__ import annotations

import concurrent.futures as cf

from .errors import DependencyUnavailable, SchemaError
from .schemas import digest, validate_conflict_set


class ResolutionAdapter:
    def __init__(self, client, *, timeout_s: float = 2.0, retries: int = 2, backoff_s: float = 0.05,
                 sleep=None):
        self.client = client
        self.timeout_s = timeout_s
        self.retries = retries
        self.backoff_s = backoff_s
        self._sleep = sleep or (lambda s: None)
        self._pool = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="gap05-resolve")
        self.calls = 0

    def request(self, conflict: dict, context: dict) -> dict:
        validate_conflict_set(conflict)
        frontier = digest(conflict)
        last_error = None
        for attempt in range(self.retries + 1):
            self.calls += 1
            fut = self._pool.submit(self.client, {"conflict": conflict, "context": context,
                                                  "frontier_digest": frontier, "attempt": attempt})
            try:
                decision = fut.result(timeout=self.timeout_s)
            except cf.TimeoutError:
                last_error = "timeout"
            except Exception as exc:  # noqa: BLE001 - dependency failure class
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                return self._validate(decision, frontier)
            self._sleep(self.backoff_s * (2 ** attempt))
        raise DependencyUnavailable(f"policy engine unavailable after {self.retries + 1} attempts: {last_error}",
                                    code="DEP_POLICY_UNAVAILABLE")

    @staticmethod
    def _validate(decision, frontier: str) -> dict:
        if not isinstance(decision, dict) or decision.get("decision") not in ("resolve", "defer"):
            raise SchemaError("policy decision malformed", code="CORR_POLICY_DECISION")
        if decision["decision"] == "resolve":
            if not isinstance(decision.get("value"), str) or not decision.get("policy_version"):
                raise SchemaError("resolve decision needs value and policy_version", code="CORR_POLICY_DECISION")
        return {**decision, "frontier_digest": frontier}

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)
