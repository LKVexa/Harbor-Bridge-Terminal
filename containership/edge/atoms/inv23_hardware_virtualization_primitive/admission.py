"""Consumer-side admission contract for GAP-02 / INV-24 / INV-40 / INV-43 (MC-11).

Downstream components must not infer virtualization capability themselves; they admit
a host only through ``require_usable`` on an INV-23 report, which checks the schema
version at the boundary and preserves the reason code on refusal.
"""

from __future__ import annotations

from collections.abc import Iterable

from .schema import SchemaError, validate

ACCEPTED = ("PK_VIRT_PRIMITIVE/2",)


class NotAdmitted(RuntimeError):
    def __init__(self, reason: str, state: str, detail: str = "") -> None:
        super().__init__(f"virtualization not admitted: {state}/{reason} {detail}".strip())
        self.reason, self.state = reason, state


def require_usable(report: dict, *, accepted: Iterable[str] = ACCEPTED, max_nesting: int = 1, require_known_depth: bool = False) -> dict:
    sid = report.get("schema") if isinstance(report, dict) else None
    if sid not in tuple(accepted):
        raise NotAdmitted("schema_version_rejected", "unknown", repr(sid))
    try:
        validate(report, sid)
    except SchemaError as exc:
        raise NotAdmitted("malformed_probe_response", "unknown", str(exc)) from exc
    if report["state"] != "usable":
        raise NotAdmitted(report["reason"], report["state"])
    d = report["nesting_depth"]
    if d is None and require_known_depth:
        raise NotAdmitted("nesting_unknown", "usable")
    if d is not None and d > max_nesting:
        raise NotAdmitted("nesting_policy", "usable", f"depth {d} > {max_nesting}")
    return report
