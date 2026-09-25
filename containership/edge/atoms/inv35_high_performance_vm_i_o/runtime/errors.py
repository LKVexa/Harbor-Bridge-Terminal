"""Stable, machine-readable error model for INV-35 (INV-35-C014, INV-35-C026).

Every refusal the datapath or its control surface can emit maps to exactly one
code below.  Codes are append-only: a published code is never renumbered,
repurposed or removed (see docs/requirements/COMPATIBILITY_POLICY.md).  The
``outcome`` class tells a caller what it may do next:

* ``success``   - the operation took effect.
* ``degraded``  - the operation took effect under a declared degraded mode.
* ``retryable`` - nothing took effect; the same request MAY be retried later
                  with the same idempotency key.
* ``terminal``  - nothing took effect; retrying the same request is forbidden.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ERROR_SCHEMA = "INV35_ERROR/1"


class Outcome(str, Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    RETRYABLE = "retryable"
    TERMINAL = "terminal"


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    code: str
    outcome: Outcome
    security_relevant: bool
    summary: str


_SPECS: tuple[ErrorSpec, ...] = (
    ErrorSpec("INV35-E000", Outcome.SUCCESS, False, "ok"),
    ErrorSpec("INV35-E001", Outcome.DEGRADED, False, "accepted in a declared degraded mode"),
    # Guest-controlled input: terminal, security relevant.
    ErrorSpec("INV35-E100", Outcome.TERMINAL, True, "descriptor chain is not a mapping / not snapshottable"),
    ErrorSpec("INV35-E101", Outcome.TERMINAL, True, "invalid head, slot or next index"),
    ErrorSpec("INV35-E102", Outcome.TERMINAL, True, "descriptor chain loops"),
    ErrorSpec("INV35-E103", Outcome.TERMINAL, True, "descriptor chain exceeds MAX_CHAIN"),
    ErrorSpec("INV35-E104", Outcome.TERMINAL, True, "dangling descriptor link"),
    ErrorSpec("INV35-E105", Outcome.TERMINAL, True, "descriptor range outside registered guest memory"),
    ErrorSpec("INV35-E106", Outcome.TERMINAL, True, "descriptor field has wrong type or sign"),
    ErrorSpec("INV35-E107", Outcome.TERMINAL, True, "descriptor chain exceeds byte limit"),
    # Capacity / overload: retryable.
    ErrorSpec("INV35-E200", Outcome.RETRYABLE, False, "queue descriptor depth exhausted"),
    ErrorSpec("INV35-E201", Outcome.RETRYABLE, False, "tenant quota exhausted"),
    ErrorSpec("INV35-E202", Outcome.RETRYABLE, False, "load shed: circuit open"),
    ErrorSpec("INV35-E203", Outcome.RETRYABLE, False, "deadline exceeded before admission"),
    ErrorSpec("INV35-E204", Outcome.TERMINAL, False, "request cancelled by caller"),
    ErrorSpec("INV35-E205", Outcome.TERMINAL, False, "nothing in flight to complete"),
    # Identity / authorization: terminal, security relevant.
    ErrorSpec("INV35-E300", Outcome.TERMINAL, True, "missing or malformed capability"),
    ErrorSpec("INV35-E301", Outcome.TERMINAL, True, "capability signature invalid"),
    ErrorSpec("INV35-E302", Outcome.TERMINAL, True, "capability expired or not yet valid"),
    ErrorSpec("INV35-E303", Outcome.TERMINAL, True, "capability does not grant this action/queue/tenant"),
    ErrorSpec("INV35-E304", Outcome.TERMINAL, True, "replayed nonce"),
    ErrorSpec("INV35-E305", Outcome.TERMINAL, True, "cross-tenant access refused"),
    ErrorSpec("INV35-E306", Outcome.RETRYABLE, True, "trust service unavailable: fail closed"),
    ErrorSpec("INV35-E307", Outcome.TERMINAL, True, "stale controller epoch (fenced)"),
    # Lifecycle.
    ErrorSpec("INV35-E400", Outcome.TERMINAL, False, "illegal lifecycle transition"),
    ErrorSpec("INV35-E401", Outcome.RETRYABLE, False, "queue not serving (starting/draining/frozen)"),
    ErrorSpec("INV35-E402", Outcome.TERMINAL, True, "queue quarantined"),
    ErrorSpec("INV35-E403", Outcome.TERMINAL, False, "queue disabled"),
    # Configuration / artifacts / negotiation.
    ErrorSpec("INV35-E500", Outcome.TERMINAL, True, "configuration failed validation"),
    ErrorSpec("INV35-E501", Outcome.TERMINAL, True, "configuration provenance/digest mismatch"),
    ErrorSpec("INV35-E502", Outcome.TERMINAL, True, "artifact digest mismatch"),
    ErrorSpec("INV35-E503", Outcome.TERMINAL, False, "no mutually supported interface version"),
    ErrorSpec("INV35-E504", Outcome.TERMINAL, True, "secret material present in plain configuration"),
    ErrorSpec("INV35-E505", Outcome.TERMINAL, True, "audit chain integrity failure"),
)

REGISTRY: dict[str, ErrorSpec] = {spec.code: spec for spec in _SPECS}


class Inv35Error(Exception):
    """Base for every coded INV-35 refusal."""

    def __init__(self, code: str, detail: str = "", **context: object) -> None:
        if code not in REGISTRY:
            raise ValueError(f"unregistered INV-35 error code {code!r}")
        self.spec = REGISTRY[code]
        self.code = code
        self.detail = detail
        self.context = dict(context)
        super().__init__(f"{code}: {detail or self.spec.summary}")

    @property
    def outcome(self) -> Outcome:
        return self.spec.outcome

    @property
    def retryable(self) -> bool:
        return self.spec.outcome is Outcome.RETRYABLE

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "outcome": self.spec.outcome.value,
            "security_relevant": self.spec.security_relevant,
            "summary": self.spec.summary,
            "detail": self.detail,
        }


def classify_model_error(exc: BaseException) -> str:
    """Map a reference-model exception message onto a stable code.

    ``io_model`` raises ``DescriptorInvalid``/``QueueFull`` with human text; the
    datapath facade translates them here so external callers only ever see codes.
    """
    from ..io_model import DescriptorInvalid, QueueFull

    text = str(exc)
    if isinstance(exc, QueueFull):
        return "INV35-E200"
    if not isinstance(exc, DescriptorInvalid):
        return "INV35-E100"
    table = (
        ("byte limit", "INV35-E107"),
        ("loops at", "INV35-E102"),
        ("exceeds", "INV35-E103"),
        ("is not in the ring", "INV35-E104"),
        ("outside registered guest memory", "INV35-E105"),
        ("invalid head", "INV35-E101"),
        ("invalid descriptor slot", "INV35-E101"),
        ("invalid next index", "INV35-E101"),
        ("claiming index", "INV35-E101"),
        ("non-integer", "INV35-E106"),
        ("negative", "INV35-E106"),
        ("is not a Descriptor", "INV35-E106"),
    )
    for needle, code in table:
        if needle in text:
            return code
    return "INV35-E100"


def registry_document() -> dict[str, object]:
    """Machine-readable export used to generate schemas/errors/error_codes.json."""
    return {
        "schema": "INV35_ERROR_REGISTRY/1",
        "codes": [
            {
                "code": s.code,
                "outcome": s.outcome.value,
                "security_relevant": s.security_relevant,
                "summary": s.summary,
            }
            for s in _SPECS
        ],
    }
