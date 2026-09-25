"""#10 constraint precedence model.

When constraints conflict the higher-ranked constraint always wins; a lower
rank can only *narrow* choices a higher rank already allowed, never widen them.

    1. security      (authn/authz/sandbox/frozen/emergency-disable)
    2. residency     (classification legal at destination)
    3. integrity     (digest + signed label present when required)
    4. isolation     (tenant quota / isolation class)
    5. capacity      (global/tenant bounds -> backpressure)
    6. slo           (deadline feasibility)
    7. cost          (preference only)
    8. locality/gravity hints (advisory only; may promote tier, never override 1-5)
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

PRECEDENCE = ("security", "residency", "integrity", "isolation", "capacity", "slo", "cost", "locality")
HARD = frozenset(PRECEDENCE[:5])


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    decided_by: str | None
    reasons: tuple[str, ...]
    ranked: tuple[str, ...] = ()


def evaluate(checks: Mapping[str, Callable[[], tuple[bool, str]]],
             candidates: Sequence[str] = (),
             preferences: Mapping[str, Callable[[str], float]] | None = None) -> Verdict:
    """Evaluate constraints in precedence order.

    ``checks[name]()`` returns (ok, reason).  The first failing hard constraint
    decides.  Soft constraints (slo/cost/locality) only rank ``candidates``.
    Unknown constraint names are rejected so a typo cannot silently skip a check.
    """
    unknown = set(checks) - set(PRECEDENCE) | set(preferences or {}) - set(PRECEDENCE)
    if unknown:
        raise ValueError(f"unknown constraints: {sorted(unknown)}")
    reasons = []
    for name in PRECEDENCE:
        if name in checks:
            ok, why = checks[name]()
            reasons.append(f"{name}:{'ok' if ok else 'deny'}:{why}")
            if not ok and (name in HARD or name == "slo"):
                return Verdict(False, name, tuple(reasons))
    ranked = list(candidates)
    for name in reversed(PRECEDENCE):  # stable sort: highest-precedence preference applied last dominates
        if preferences and name in preferences:
            ranked.sort(key=preferences[name])
    return Verdict(True, None, tuple(reasons), tuple(ranked))
