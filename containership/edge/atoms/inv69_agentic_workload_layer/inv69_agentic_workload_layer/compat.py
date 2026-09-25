"""Versioning, deprecation, peer handshake and schema migration (C016, C027, C093).

Semantic versioning: MAJOR = breaking wire/persisted change, MINOR = additive,
PATCH = fix.  Window: readers accept current major and N-1 (via migrators);
writers emit only the current major; peers must share a major and are
feature-negotiated by capability sets, never by comparing version numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
import json
import warnings

from .errors import AgentError

COMPONENT = "INV-69"
COMPONENT_VERSION = "4.3.0"
PROTOCOL = "PK_AGENT_PEER/1"
CAPABILITIES = frozenset({
    "step.v1", "approval.v1", "transcript.v1", "run_event.v1", "error_codes.v1", "trace_context.w3c",
    "idempotency_keys", "fencing_tokens", "config_provenance.v1",
})
SCHEMAS = {
    "PK_AGENT_STEP": 1, "PK_AGENT_APPROVAL": 1, "PK_AGENT_TRANSCRIPT": 1, "PK_AGENT_RUN_EVENT": 1,
    "PK_AGENT_ERROR": 1, "PK_AGENT_CONFIG": 1, "PK_AGENT_STATUS": 1, "PK_AGENT_BACKUP": 1,
}
MATRIX_PATH = Path(__file__).resolve().parent / "ops" / "COMPATIBILITY_MATRIX.json"


class AgentDeprecationWarning(DeprecationWarning):
    pass


DEPRECATIONS = {
    # feature -> (stage, replacement, removal_target)
    "Agent.step result key 'reason' as the only failure signal": (
        "announce", "result['code'] (PK_AGENT_ERRORS/1)", "5.0.0"),
    "Agent.approvals direct mutation": ("warn", "Agent.approve()", "5.0.0"),
}


def deprecated(feature: str) -> None:
    stage, repl, target = DEPRECATIONS[feature]
    warnings.warn(f"{feature} is deprecated (stage={stage}); use {repl}; removal in {target}",
                  AgentDeprecationWarning, stacklevel=3)


def parse_schema_id(schema: Any) -> tuple[str, int]:
    if not isinstance(schema, str) or "/" not in schema or len(schema) > 64:
        raise AgentError("AGT-CMP-001", "malformed schema identifier")
    name, _, major = schema.partition("/")
    if not major.isdigit():
        raise AgentError("AGT-CMP-001", "malformed schema major version")
    return name, int(major)


# ---- migrators: (name, from_major) -> function producing from_major + 1
MIGRATORS: dict[tuple[str, int], Callable[[dict], dict]] = {}


def migrate(doc: Mapping[str, Any]) -> dict:
    """Read path: accept current major or older majors with a registered migrator chain."""
    name, major = parse_schema_id(doc.get("schema"))
    if name not in SCHEMAS:
        raise AgentError("AGT-CMP-001", "unknown schema family", details={"schema": name})
    current = SCHEMAS[name]
    if major > current:
        raise AgentError("AGT-CMP-001", "document is from a newer major version",
                         details={"schema": name, "got": major, "supported": current})
    out = dict(doc)
    while major < current:
        fn = MIGRATORS.get((name, major))
        if fn is None:
            raise AgentError("AGT-CMP-001", "no migrator for older major", details={"schema": name, "from": major})
        out = fn(out)
        major += 1
    return out


@dataclass(frozen=True)
class PeerInfo:
    component: str
    version: str
    protocol: str
    capabilities: frozenset[str]
    schemas: Mapping[str, int]


def local_peer() -> PeerInfo:
    return PeerInfo(COMPONENT, COMPONENT_VERSION, PROTOCOL, CAPABILITIES, dict(SCHEMAS))


def handshake(peer: Mapping[str, Any], *, required: frozenset[str] = frozenset(), matrix: Mapping | None = None) -> dict:
    """Negotiate with a peer BEFORE any side effect.  Returns the agreed feature set."""
    try:
        name, major = parse_schema_id(peer.get("protocol"))
        caps = frozenset(peer.get("capabilities") or ())
        comp, ver = str(peer.get("component", "")), str(peer.get("version", ""))
    except AgentError:
        raise
    except Exception:
        raise AgentError("AGT-CMP-001", "malformed handshake") from None
    lname, lmajor = parse_schema_id(PROTOCOL)
    if name != lname or major != lmajor:
        raise AgentError("AGT-CMP-001", "protocol major mismatch", details={"peer": peer.get("protocol"), "local": PROTOCOL})
    missing = required - caps
    if missing:
        raise AgentError("AGT-CMP-001", "peer lacks required capabilities", details={"missing": sorted(missing)})
    support = support_state(comp, ver, matrix)
    if support == "unsupported":
        raise AgentError("AGT-CMP-001", "peer version unsupported by the compatibility matrix",
                         details={"component": comp, "version": ver})
    agreed = sorted(caps & CAPABILITIES)
    return {"peer": comp, "peer_version": ver, "protocol": PROTOCOL, "agreed_capabilities": agreed,
            "disabled_features": sorted(CAPABILITIES - caps), "support_state": support}


def load_matrix(path: Path = MATRIX_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _vt(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (-1,)


def support_state(component: str, version: str, matrix: Mapping | None = None) -> str:
    matrix = matrix if matrix is not None else load_matrix()
    for row in matrix["rows"]:
        if row["component"] == component and _vt(row["min"]) <= _vt(version) <= _vt(row["max"]):
            return row["state"]
    return "unsupported" if any(r["component"] == component for r in matrix["rows"]) else "unknown"


def compatibility_manifest() -> dict:
    return {"schema": "PK_AGENT_COMPATIBILITY_MANIFEST/1", "component": COMPONENT, "version": COMPONENT_VERSION,
            "protocol": PROTOCOL, "capabilities": sorted(CAPABILITIES), "schemas": SCHEMAS,
            "deprecations": {k: {"stage": s, "replacement": r, "removal": t} for k, (s, r, t) in DEPRECATIONS.items()}}
