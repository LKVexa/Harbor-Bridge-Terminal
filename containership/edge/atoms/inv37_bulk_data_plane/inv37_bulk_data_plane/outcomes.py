"""Canonical outcome classes and the stable error-code registry (INV-37-C014, C026).

Every error raised by the package carries a ``code`` that appears in
``ERROR_CODES``.  The registry states the outcome class, whether the caller may
retry, whether a retry needs a fresh transfer id, and what happens to partial
progress.  ``tests/test_outcomes.py`` asserts the registry is complete.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import BulkDataPlaneError


class Outcome(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"      # some chunks verified, transfer resumable
    DEGRADED_SUCCESS = "degraded_success"    # success via an approved fallback (e.g. copy transport)
    RETRYABLE_FAILURE = "retryable_failure"
    TERMINAL_FAILURE = "terminal_failure"
    POLICY_REJECTION = "policy_rejection"
    SECURITY_REJECTION = "security_rejection"


class Progress(str, Enum):
    KEEP = "keep"              # verified progress stays durable and resumable
    DISCARD = "discard"        # progress is dropped; restart from manifest
    QUARANTINE = "quarantine"  # progress is frozen for investigation, never reused
    NONE = "none"              # no progress existed


@dataclass(frozen=True)
class CodeSpec:
    code: str
    outcome: Outcome
    retryable: bool
    max_attempts: int
    new_transfer_id_required: bool
    progress: Progress
    caller_action: str


def _s(code, outcome, retryable, attempts, new_id, progress, action):
    return CodeSpec(code, outcome, retryable, attempts, new_id, progress, action)


ERROR_CODES: dict[str, CodeSpec] = {s.code: s for s in [
    _s("invalid_manifest", Outcome.TERMINAL_FAILURE, False, 0, True, Progress.NONE,
       "Fix or re-fetch the manifest from the authenticated control plane."),
    _s("digest_mismatch", Outcome.TERMINAL_FAILURE, False, 0, False, Progress.KEEP,
       "Re-send the offending chunk from source; never re-send the same bytes blindly."),
    _s("object_digest_mismatch", Outcome.TERMINAL_FAILURE, False, 0, True, Progress.QUARANTINE,
       "Final verification failed; transfer is quarantined. Escalate as integrity incident."),
    _s("transfer_incomplete", Outcome.PARTIAL_SUCCESS, True, 0, False, Progress.KEEP,
       "Resume: send the chunks listed in details.missing."),
    _s("admission_rejected", Outcome.RETRYABLE_FAILURE, True, 5, False, Progress.NONE,
       "Back off with jitter (see retry.RetryPolicy) and retry."),
    _s("quota_exceeded", Outcome.POLICY_REJECTION, True, 5, False, Progress.NONE,
       "Tenant quota exhausted; retry after in-flight transfers drain."),
    _s("transfer_closed", Outcome.TERMINAL_FAILURE, False, 0, True, Progress.NONE,
       "Transfer was closed; start a new transfer."),
    _s("illegal_transition", Outcome.TERMINAL_FAILURE, False, 0, False, Progress.KEEP,
       "Caller bug: operation not legal in current lifecycle state."),
    _s("cancelled", Outcome.TERMINAL_FAILURE, False, 0, True, Progress.DISCARD,
       "Transfer was cancelled by caller or operator."),
    _s("timeout", Outcome.RETRYABLE_FAILURE, True, 3, False, Progress.KEEP,
       "Deadline exceeded; resume with the resume token."),
    _s("quarantined", Outcome.SECURITY_REJECTION, False, 0, True, Progress.QUARANTINE,
       "Transfer or tenant is quarantined; operator release required."),
    _s("admission_frozen", Outcome.POLICY_REJECTION, True, 3, False, Progress.NONE,
       "Operator freeze/emergency disable is active."),
    _s("authentication_failed", Outcome.SECURITY_REJECTION, False, 0, False, Progress.NONE,
       "Obtain a fresh credential; details intentionally minimal."),
    _s("authorization_denied", Outcome.SECURITY_REJECTION, False, 0, False, Progress.NONE,
       "Principal lacks the capability for this action/scope."),
    _s("replay_detected", Outcome.SECURITY_REJECTION, False, 0, False, Progress.NONE,
       "Token nonce reused; mint a new token."),
    _s("security_service_unavailable", Outcome.RETRYABLE_FAILURE, True, 3, False, Progress.KEEP,
       "Key/identity/policy/time service unavailable; fail closed and retry later."),
    _s("unsupported_capability", Outcome.TERMINAL_FAILURE, False, 0, True, Progress.NONE,
       "Platform lacks a required capability; choose a supported profile."),
    _s("version_incompatible", Outcome.TERMINAL_FAILURE, False, 0, True, Progress.NONE,
       "No mutually supported protocol profile; upgrade a peer."),
    _s("invalid_config", Outcome.TERMINAL_FAILURE, False, 0, False, Progress.NONE,
       "Fix configuration; admission stays disabled."),
    _s("checkpoint_corrupt", Outcome.SECURITY_REJECTION, False, 0, True, Progress.QUARANTINE,
       "Checkpoint failed its seal; quarantined file retained for investigation."),
    _s("stale_owner", Outcome.TERMINAL_FAILURE, False, 0, False, Progress.KEEP,
       "Fencing epoch superseded; another owner holds the transfer."),
    _s("resume_conflict", Outcome.TERMINAL_FAILURE, False, 0, False, Progress.KEEP,
       "Peer resume token disagrees with local verified progress; local state wins."),
    _s("encryption_unavailable", Outcome.POLICY_REJECTION, False, 0, False, Progress.NONE,
       "Policy requires encryption and no approved provider is configured."),
    _s("residency_violation", Outcome.POLICY_REJECTION, False, 0, True, Progress.NONE,
       "Destination region not permitted for this tenant's data."),
    _s("bulk_data_plane_error", Outcome.TERMINAL_FAILURE, False, 0, False, Progress.NONE,
       "Generic; should not be raised by production paths."),
]}


def classify(exc: BaseException) -> dict[str, Any]:
    """Map any exception to an outcome record.  Unknown exceptions are terminal."""
    if isinstance(exc, BulkDataPlaneError):
        spec = ERROR_CODES.get(exc.code, ERROR_CODES["bulk_data_plane_error"])
    else:
        spec = ERROR_CODES["bulk_data_plane_error"]
    return {
        "code": spec.code,
        "outcome": spec.outcome.value,
        "retryable": spec.retryable,
        "max_attempts": spec.max_attempts,
        "new_transfer_id_required": spec.new_transfer_id_required,
        "progress": spec.progress.value,
        "caller_action": spec.caller_action,
    }
