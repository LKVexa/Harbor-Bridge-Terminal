"""Versioned, typed wire schemas (MC-012) and protocol negotiation (MC-027).

IDL choice (ADR-003): canonical **JSON** with a Python-declared schema table
(this module), because the package is dependency-free and the interfaces are
low-rate control operations.  Every message has a ``schema`` string
``cstate.<message>/<major>.<minor>`` and stable field identifiers (the JSON
names below are frozen; ``tools/check_schema_compat.py`` diffs them against
``conformance/schema_lock.json`` in CI and fails on removals/type changes).

Compatibility rules (MC-012-03):

* Same major, any minor: fields are only ever *added* and are optional.
* A request whose minor is **newer** than the server's may carry unknown fields;
  they are ignored (forward compatibility).
* A request whose minor is **equal or older** must not carry unknown fields;
  they are rejected as ``CSTATE_INVALID_ARGUMENT`` (typo/injection guard).
* Duplicate JSON object keys are always rejected.
* A different major is rejected as ``CSTATE_INCOMPATIBLE_VERSION``.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .errors import IncompatibleVersion, InvalidArgument, SchemaVersionError
from .store import COMPARE_TARGETS, Compare, Delete, Put, Range

PROTOCOL = "PK_CSTATE"
PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 1
SUPPORTED_MAJORS = (1,)
CAPABILITIES = ("txn.compare_branches", "txn.rich_predicates", "range.pagination", "delete.prefix",
                "watch.stream", "watch.progress", "watch.resume", "lease.fencing", "compact.protected",
                "idempotency.request_id", "explain", "replication.feed")

# field -> (type(s), required)
MESSAGES: dict[str, dict[str, tuple[tuple[type, ...], bool]]] = {
    "txn": {"schema": ((str,), True), "compare": ((list,), False), "success": ((list,), False),
            "failure": ((list,), False), "request_id": ((str,), False), "deadline_ms": ((int,), False)},
    "range": {"schema": ((str,), True), "key": ((str,), True), "range_end": ((str,), False),
              "prefix": ((bool,), False), "revision": ((int,), False), "limit": ((int,), False),
              "page_token": ((str,), False), "deadline_ms": ((int,), False)},
    "watch": {"schema": ((str,), True), "prefix": ((str,), False), "start_revision": ((int,), False),
              "kinds": ((list,), False), "prev_value": ((bool,), False), "progress_interval_ms": ((int,), False)},
    "compact": {"schema": ((str,), True), "revision": ((int,), True)},
    "lease_grant": {"schema": ((str,), True), "ttl": ((int,), True)},
    "lease_keepalive": {"schema": ((str,), True), "id": ((int,), True)},
    "lease_revoke": {"schema": ((str,), True), "id": ((int,), True)},
    "hello": {"schema": ((str,), True), "protocol": ((str,), True), "versions": ((list,), True),
              "capabilities": ((list,), False), "client": ((str,), False)},
}
OP_FIELDS = {"put": {"key", "value", "lease"}, "delete": {"key", "prefix"},
             "range": {"key", "range_end", "prefix", "revision", "limit", "page_token"}}
COMPARE_FIELDS = {"key", "target", "op", "operand"}
SCHEMA_RE = re.compile(r"^cstate\.([a-z_]+)/(\d+)\.(\d+)$")


def _no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for k, v in pairs:
        if k in d:
            raise InvalidArgument(f"duplicate field {k!r}", field=k)
        d[k] = v
    return d


def loads(raw: bytes | str, max_bytes: int) -> Any:
    if isinstance(raw, str):
        raw = raw.encode()
    if len(raw) > max_bytes:
        from .errors import LimitExceeded
        raise LimitExceeded("request too large", limit="max_request_bytes", limit_value=max_bytes)
    try:
        return json.loads(raw, object_pairs_hook=_no_dupes,
                          parse_constant=lambda c: (_ for _ in ()).throw(InvalidArgument("non-finite number")))
    except InvalidArgument:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise InvalidArgument("request body is not valid JSON", field="body") from exc


def check_message(kind: str, msg: Any) -> dict[str, Any]:
    if not isinstance(msg, dict):
        raise InvalidArgument("message must be a JSON object", field="body")
    spec = MESSAGES[kind]
    m = SCHEMA_RE.match(str(msg.get("schema", "")))
    if not m or m.group(1) != kind:
        raise SchemaVersionError(f"schema must be cstate.{kind}/<major>.<minor>", field="schema",
                                 supported=[f"cstate.{kind}/{PROTOCOL_MAJOR}.{PROTOCOL_MINOR}"])
    major, minor = int(m.group(2)), int(m.group(3))
    if major not in SUPPORTED_MAJORS:
        raise IncompatibleVersion(f"major {major} unsupported", supported=list(SUPPORTED_MAJORS))
    unknown = set(msg) - set(spec)
    if unknown and minor <= PROTOCOL_MINOR:
        raise InvalidArgument(f"unknown fields {sorted(unknown)}", field=sorted(unknown)[0])
    out = {}
    for f, (types, req) in spec.items():
        if f not in msg:
            if req:
                raise InvalidArgument(f"missing field {f}", field=f)
            continue
        v = msg[f]
        if not isinstance(v, types) or (int in types and bool not in types and isinstance(v, bool)):
            raise InvalidArgument(f"field {f} has wrong type", field=f)
        out[f] = v
    return out


def _strict_keys(d: Any, allowed: set[str], what: str) -> dict[str, Any]:
    if not isinstance(d, dict):
        raise InvalidArgument(f"{what} must be an object", field=what)
    extra = set(d) - allowed
    if extra:
        raise InvalidArgument(f"unknown {what} fields {sorted(extra)}", field=what)
    return d


def parse_compare(d: Any) -> Compare:
    d = _strict_keys(d, COMPARE_FIELDS, "compare")
    for f in ("key", "target", "op"):
        if not isinstance(d.get(f), str):
            raise InvalidArgument(f"compare.{f} must be a string", field=f"compare.{f}")
    if "operand" not in d:
        raise InvalidArgument("compare.operand required", field="compare.operand")
    return Compare(d["key"], d["target"], d["op"], d["operand"])


def parse_op(d: Any) -> Put | Delete | Range:
    if not isinstance(d, dict) or len(d) != 1:
        raise InvalidArgument("op must be an object with exactly one of put/delete/range", field="op")
    (kind, body), = d.items()
    if kind not in OP_FIELDS:
        raise InvalidArgument(f"unknown op {kind!r}", field="op")
    body = _strict_keys(body, OP_FIELDS[kind], kind)
    if not isinstance(body.get("key"), str):
        raise InvalidArgument(f"{kind}.key must be a string", field=f"{kind}.key")
    try:
        if kind == "put":
            if "value" not in body:
                raise InvalidArgument("put.value required (use delete to remove a key)", field="put.value")
            return Put(body["key"], body["value"], _int(body.get("lease", 0), "put.lease"))
        if kind == "delete":
            return Delete(body["key"], _bool(body.get("prefix", False), "delete.prefix"))
        return Range(body["key"], _str(body.get("range_end", ""), "range.range_end"),
                     _bool(body.get("prefix", False), "range.prefix"), _int(body.get("revision", 0), "range.revision"),
                     _int(body.get("limit", 0), "range.limit"), _str(body.get("page_token", ""), "range.page_token"))
    except TypeError as exc:
        raise InvalidArgument(str(exc), field=kind) from exc


def _int(v: Any, f: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise InvalidArgument(f"{f} must be an integer", field=f)
    return v


def _bool(v: Any, f: str) -> bool:
    if not isinstance(v, bool):
        raise InvalidArgument(f"{f} must be a boolean", field=f)
    return v


def _str(v: Any, f: str) -> str:
    if not isinstance(v, str):
        raise InvalidArgument(f"{f} must be a string", field=f)
    return v


def negotiate(hello: dict[str, Any]) -> dict[str, Any]:
    """Protocol handshake (MC-027-01/03/04): pick the highest common version,
    return the intersection of capabilities; reject if no common major."""
    h = check_message("hello", hello)
    if h["protocol"] != PROTOCOL:
        raise IncompatibleVersion("unknown protocol", supported=[PROTOCOL])
    offered = []
    for v in h["versions"]:
        m = re.fullmatch(r"(\d+)\.(\d+)", str(v))
        if m:
            offered.append((int(m.group(1)), int(m.group(2))))
    common = [(ma, min(mi, PROTOCOL_MINOR)) for ma, mi in offered if ma in SUPPORTED_MAJORS]
    if not common:
        raise IncompatibleVersion("no common protocol major version",
                                  supported=[f"{PROTOCOL_MAJOR}.{PROTOCOL_MINOR}"])
    ma, mi = max(common)
    client_caps = set(h.get("capabilities", CAPABILITIES))
    return {"schema": f"cstate.hello/{PROTOCOL_MAJOR}.{PROTOCOL_MINOR}", "protocol": PROTOCOL,
            "version": f"{ma}.{mi}", "capabilities": sorted(client_caps & set(CAPABILITIES)),
            "server_only_capabilities": sorted(set(CAPABILITIES) - client_caps)}


def schema_lock() -> dict[str, Any]:
    """Frozen field inventory used for breaking-change detection (MC-012-06)."""
    return {"protocol": PROTOCOL, "major": PROTOCOL_MAJOR, "minor": PROTOCOL_MINOR,
            "messages": {k: {f: [t.__name__ for t in ts] + (["required"] if r else [])
                             for f, (ts, r) in v.items()} for k, v in MESSAGES.items()},
            "ops": {k: sorted(v) for k, v in OP_FIELDS.items()},
            "compare_targets": {k: sorted(v) for k, v in COMPARE_TARGETS.items()},
            "capabilities": list(CAPABILITIES)}
