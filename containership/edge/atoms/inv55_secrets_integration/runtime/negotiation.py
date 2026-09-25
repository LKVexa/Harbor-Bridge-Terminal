"""Protocol-version negotiation (checklist #8, #22).

Clients send ``versions`` (list of ``PK_SECRET_<OP>/<n>``).  The server picks
the highest mutually supported version per operation.  Unknown fields are
tolerated only in the ``ext`` object (tolerant reader); unknown top-level
fields are rejected (strict schema) so a newer client cannot smuggle
semantics an older server would silently ignore.
"""
from __future__ import annotations

from .errors import INV55Error

SUPPORTED = {"RESOLVE": (1,), "ROTATE": (1,), "SCOPE": (1,)}
DEPRECATED: dict[str, tuple[int, ...]] = {}   # op -> versions still accepted but announced for removal


def negotiate(op: str, offered: list[str]) -> str:
    best = None
    if not isinstance(offered, list):
        raise INV55Error("INV55-E-UNSUPPORTED-VERSION", "versions must be a list")
    for v in offered:
        if not isinstance(v, str) or not v.startswith("PK_SECRET_") or "/" not in v:
            continue
        name, _, num = v[len("PK_SECRET_"):].partition("/")
        if name == op and num.isdigit() and int(num) in SUPPORTED.get(op, ()):
            best = max(best or 0, int(num))
    if best is None:
        raise INV55Error("INV55-E-UNSUPPORTED-VERSION", f"offered={offered!r}")
    return f"PK_SECRET_{op}/{best}"
