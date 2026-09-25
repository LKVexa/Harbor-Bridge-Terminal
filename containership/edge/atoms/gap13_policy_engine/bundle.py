"""G13-MC-002 typed ``PK_POLICY_BUNDLE/1`` schema and strict bounded parser.

Pipeline: size gate -> strict JSON decode (duplicate keys, floats, NaN refused)
-> depth gate -> schema-version gate -> structural validation -> canonical-form
check -> semantic validation -> immutable :class:`PolicyBundle`.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import canonical_bytes, sha256_hex
from .config import Limits
from .engine import Rule
from .errors import (BundleParseError, BundleSemanticError, BundleTooLarge, SchemaMismatch)

BUNDLE_SCHEMA = "PK_POLICY_BUNDLE/1"
SUPPORTED_BUNDLE_SCHEMAS = (BUNDLE_SCHEMA,)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_ATTR_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}(\.[a-z][a-z0-9_]{0,62}){0,3}$")
_TOP_REQUIRED = {"schema", "bundle_id", "policy_id", "issuer", "generation", "issued_at", "environment",
                 "version", "rules"}
_TOP_OPTIONAL = {"expires_at", "extensions"}
_RULE_KEYS = {"name", "effect", "scope", "match"}
_MAX_INT = 2**53 - 1


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise BundleParseError(f"duplicate object field: {k!r}")
        out[k] = v
    return out


def _no_float(s):
    raise BundleParseError("floating-point numbers are not permitted")


def _no_const(s):
    raise BundleParseError(f"non-finite constant {s} not permitted")


def strict_json_loads(data: bytes, *, max_bytes: int, max_depth: int) -> Any:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise BundleParseError("bundle must be bytes")
    data = bytes(data)
    if len(data) > max_bytes:
        raise BundleTooLarge(f"bundle is {len(data)} bytes; limit {max_bytes}", details={"limit": max_bytes})
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BundleParseError("bundle is not valid UTF-8") from exc
    # cheap pre-parse depth bound so pathological nesting never reaches the decoder's recursion
    depth = cur = 0
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            cur += 1
            depth = max(depth, cur)
            if depth > max_depth:
                raise BundleTooLarge(f"nesting deeper than {max_depth}", details={"limit": max_depth})
        elif ch in "]}":
            cur -= 1
    try:
        return json.loads(text, object_pairs_hook=_no_dupes, parse_float=_no_float, parse_constant=_no_const)
    except BundleParseError:
        raise
    except (ValueError, RecursionError) as exc:
        raise BundleParseError(f"malformed JSON: {exc.__class__.__name__}") from exc


def _check_str(v: Any, what: str, limits: Limits, pattern: re.Pattern | None = None) -> str:
    if not isinstance(v, str) or not v:
        raise BundleSemanticError(f"{what} must be a non-empty string")
    if len(v) > limits.max_string_length:
        raise BundleTooLarge(f"{what} exceeds {limits.max_string_length} characters")
    if unicodedata.normalize("NFC", v) != v:
        raise BundleSemanticError(f"{what} is not NFC-normalised")
    if any(unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co") for c in v):
        raise BundleSemanticError(f"{what} contains control/format characters")
    if pattern is not None and not pattern.match(v):
        raise BundleSemanticError(f"{what} {v!r} does not match {pattern.pattern}")
    return v


def _check_int(v: Any, what: str, minimum: int = 0) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not minimum <= v <= _MAX_INT:
        raise BundleSemanticError(f"{what} must be an integer in [{minimum}, 2^53-1]")
    return v


def _check_value(v: Any, what: str, limits: Limits) -> Any:
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, int):
        return _check_int(v, what, minimum=-_MAX_INT)
    if isinstance(v, str):
        return _check_str(v, what, limits)
    if isinstance(v, list):
        if len(v) > limits.max_match_attributes:
            raise BundleTooLarge(f"{what} list too long")
        if any(isinstance(x, (list, dict)) for x in v):
            raise BundleSemanticError(f"{what} nests lists/objects")
        return [_check_value(x, what, limits) for x in v]
    raise BundleSemanticError(f"{what} has unsupported type {type(v).__name__}")


@dataclass(frozen=True)
class PolicyBundle:
    schema: str
    bundle_id: str
    policy_id: str
    issuer: str
    generation: int
    issued_at: int
    expires_at: int | None
    environment: str
    version: str
    rules: tuple[Rule, ...]
    digest: str                  # sha256 over the exact canonical payload bytes

    def identity(self) -> dict[str, Any]:
        return {"bundle_id": self.bundle_id, "policy_id": self.policy_id, "issuer": self.issuer,
                "generation": self.generation, "digest": self.digest, "version": self.version}


def parse_bundle(payload: bytes, limits: Limits = Limits()) -> PolicyBundle:
    doc = strict_json_loads(payload, max_bytes=limits.max_bundle_bytes, max_depth=limits.max_nesting_depth)
    if not isinstance(doc, dict):
        raise BundleParseError("bundle root must be an object")
    schema = doc.get("schema")
    if schema not in SUPPORTED_BUNDLE_SCHEMAS:
        raise SchemaMismatch(f"unsupported bundle schema {schema!r}; supported {SUPPORTED_BUNDLE_SCHEMAS}",
                             details={"received": str(schema)[:64], "supported": list(SUPPORTED_BUNDLE_SCHEMAS)})
    missing = _TOP_REQUIRED - set(doc)
    unknown = set(doc) - _TOP_REQUIRED - _TOP_OPTIONAL
    if missing:
        raise BundleSemanticError(f"missing fields: {sorted(missing)}")
    if unknown:
        raise BundleSemanticError(f"unknown top-level fields: {sorted(unknown)} (use 'extensions')")
    if canonical_bytes(doc) != bytes(payload):
        raise BundleParseError("payload is not in canonical form (key order/whitespace/normalisation)")

    bundle_id = _check_str(doc["bundle_id"], "bundle_id", limits, _ID_RE)
    policy_id = _check_str(doc["policy_id"], "policy_id", limits, _ID_RE)
    issuer = _check_str(doc["issuer"], "issuer", limits, _ID_RE)
    environment = _check_str(doc["environment"], "environment", limits, _ID_RE)
    version = _check_str(doc["version"], "version", limits, _ID_RE)
    generation = _check_int(doc["generation"], "generation", minimum=1)
    issued_at = _check_int(doc["issued_at"], "issued_at")
    expires_at = doc.get("expires_at")
    if expires_at is not None:
        expires_at = _check_int(expires_at, "expires_at")
        if expires_at <= issued_at:
            raise BundleSemanticError("expires_at must be after issued_at")
    ext = doc.get("extensions", {})
    if not isinstance(ext, dict) or any(not k.startswith("x-") for k in ext):
        raise BundleSemanticError("extensions must be an object whose keys start with 'x-'")

    raw_rules = doc["rules"]
    if not isinstance(raw_rules, list):
        raise BundleSemanticError("rules must be an array")
    if len(raw_rules) > limits.max_rules:
        raise BundleTooLarge(f"{len(raw_rules)} rules exceeds limit {limits.max_rules}")
    rules: list[Rule] = []
    for i, r in enumerate(raw_rules):
        if not isinstance(r, dict):
            raise BundleSemanticError(f"rules[{i}] must be an object")
        if set(r) != _RULE_KEYS:
            raise BundleSemanticError(f"rules[{i}] must have exactly {sorted(_RULE_KEYS)}")
        name = _check_str(r["name"], f"rules[{i}].name", limits, _ID_RE)
        if r["effect"] not in ("allow", "deny"):
            raise BundleSemanticError(f"rules[{i}].effect must be allow|deny")
        if r["scope"] not in ("estate", "tenant"):
            raise BundleSemanticError(f"rules[{i}].scope must be estate|tenant")
        m = r["match"]
        if not isinstance(m, dict):
            raise BundleSemanticError(f"rules[{i}].match must be an object")
        if len(m) > limits.max_match_attributes:
            raise BundleTooLarge(f"rules[{i}].match exceeds {limits.max_match_attributes} attributes")
        pairs = []
        for k, v in m.items():
            _check_str(k, f"rules[{i}].match key", limits, _ATTR_RE)
            pairs.append((k, _check_value(v, f"rules[{i}].match.{k}", limits)))
        try:
            rules.append(Rule(name, r["effect"], tuple(pairs), scope=r["scope"]))
        except (TypeError, ValueError) as exc:
            raise BundleSemanticError(f"rules[{i}]: {exc}") from exc
    names = [r.name for r in rules]
    if len(set(names)) != len(names):
        raise BundleSemanticError("duplicate rule names")
    return PolicyBundle(schema, bundle_id, policy_id, issuer, generation, issued_at, expires_at, environment,
                        version, tuple(rules), "sha256:" + sha256_hex(bytes(payload)))


def bundle_to_dict(b: PolicyBundle) -> dict[str, Any]:
    d: dict[str, Any] = {"schema": b.schema, "bundle_id": b.bundle_id, "policy_id": b.policy_id,
                         "issuer": b.issuer, "generation": b.generation, "issued_at": b.issued_at,
                         "environment": b.environment, "version": b.version,
                         "rules": [{"name": r.name, "effect": r.effect, "scope": r.scope,
                                    "match": {k: v for k, v in r.match}} for r in b.rules]}
    if b.expires_at is not None:
        d["expires_at"] = b.expires_at
    return d
