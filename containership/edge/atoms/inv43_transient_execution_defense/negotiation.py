"""Checklist 20: interface version negotiation and compatibility rules.

Rules (also in docs/COMPATIBILITY.md):

* A client lists acceptable schema versions, most preferred first, e.g.
  ``PK_MITIGATIONS/2, PK_MITIGATIONS/1``.  The server picks the first one it
  supports; no overlap -> ``version_unsupported`` (never a silent downgrade to
  something the client did not ask for).
* Minor evolution within a major version is additive only: new optional
  fields may appear; consumers must ignore unknown fields EXCEPT in the
  ``status`` enum, where an unknown value must be read as ``unknown`` (fail
  closed).  :func:`read_status_forward_compatible` implements that consumer
  rule and is what the compatibility tests exercise.
* A status that an older major version cannot express makes the server refuse
  that version for that node (``schema_version_unrepresentable``) rather than
  rewrite it.
"""
from __future__ import annotations

from .defense import MitigationMissing

SUPPORTED: dict[str, tuple[int, ...]] = {
    "PK_MITIGATIONS": (2, 1),
    "PK_COTENANCY": (1,),
    "PK_ERROR": (1,),
    "PK_READBACK": (1,),
}

KNOWN_STATUSES = {1: {"active", "inactive", "unknown"}, 2: {"active", "inactive", "unknown", "not_affected"}}


def parse_accept(header: str | None, family: str) -> list[int]:
    if not header:
        return [1]  # no header: the original 4.2.x contract, for backward compatibility
    out = []
    for part in header.split(","):
        part = part.strip()
        if not part.startswith(family + "/"):
            continue
        try:
            v = int(part.split("/", 1)[1])
        except ValueError:
            continue
        if v not in out:
            out.append(v)
    return out


def negotiate(family: str, accept: str | None) -> int:
    if family not in SUPPORTED:
        raise MitigationMissing(f"unknown schema family {family}", code="version_unsupported",
                                details={"family": family})
    wanted = parse_accept(accept, family)
    for v in wanted:
        if v in SUPPORTED[family]:
            return v
    raise MitigationMissing(f"no mutually supported {family} version", code="version_unsupported",
                            details={"family": family, "requested": wanted, "supported": list(SUPPORTED[family])})


def read_status_forward_compatible(report: dict) -> dict[str, str]:
    """Consumer-side reader: map a PK_MITIGATIONS/N report to statuses a
    v1/v2 consumer understands; any unrecognised status becomes ``unknown``."""
    schema = report.get("schema", "")
    try:
        major = int(schema.split("/", 1)[1])
    except (IndexError, ValueError):
        raise MitigationMissing("not a PK_MITIGATIONS report", code="version_unsupported", details={}) from None
    known = KNOWN_STATUSES.get(major, KNOWN_STATUSES[max(KNOWN_STATUSES)])
    out = {}
    for name, rec in report.get("mitigations", {}).items():
        st = rec.get("status") if isinstance(rec, dict) else None
        out[name] = st if st in known else "unknown"
    return out
