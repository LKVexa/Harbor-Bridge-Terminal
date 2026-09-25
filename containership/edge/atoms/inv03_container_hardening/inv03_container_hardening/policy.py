"""Fail-closed policy primitives for INV-03 container hardening.

This module intentionally has no ``pk_core`` dependency so the security-critical
admission logic can be unit-tested in isolation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable
from types import MappingProxyType

BASELINE_VERSION = "4.2.0"
EVALUATION_SCHEMA = "PK_HARDEN_EVAL/1"
EXCEPTION_SCHEMA = "PK_HARDEN_EXCEPTION/1"
BASELINE_SCHEMA = "PK_HARDEN_BASELINE/1"


def _is_int(value: object) -> bool:
    """Return True for real integers, but not booleans."""
    return isinstance(value, int) and not isinstance(value, bool)


def _non_root(spec: Mapping[str, Any]) -> bool:
    user = spec.get("user")
    if _is_int(user):
        return user > 0
    if not isinstance(user, str):
        return False
    user = user.strip()
    if not user:
        return False
    if user.isdigit():
        return int(user, 10) > 0
    # Preserve support for named non-root users. Production adapters should
    # resolve image usernames to numeric UIDs before this boundary when possible.
    return user.casefold() != "root"


def _read_only_root(spec: Mapping[str, Any]) -> bool:
    return spec.get("readOnlyRootFilesystem") is True


def _not_privileged(spec: Mapping[str, Any]) -> bool:
    # Fail closed on omission or non-boolean values. The previous
    # ``not spec.get('privileged')`` accepted an omitted field.
    return spec.get("privileged") is False


def _caps(spec: Mapping[str, Any]) -> Mapping[str, Any] | None:
    caps = spec.get("capabilities")
    return caps if isinstance(caps, Mapping) else None


def _drop_all_capabilities(spec: Mapping[str, Any]) -> bool:
    caps = _caps(spec)
    if caps is None:
        return False
    dropped = caps.get("drop")
    added = caps.get("add", [])
    if not isinstance(dropped, list) or not all(isinstance(v, str) for v in dropped):
        return False
    if not isinstance(added, list) or not all(isinstance(v, str) for v in added):
        return False
    return "ALL" in dropped and len(added) == 0


def _seccomp(spec: Mapping[str, Any]) -> bool:
    value = spec.get("seccomp")
    return isinstance(value, str) and value in {"RuntimeDefault", "Localhost"}


# Ordered for deterministic findings/evidence.
_CONTROL_FUNCTIONS: dict[str, Callable[[Mapping[str, Any]], bool]] = {
    "non-root": _non_root,
    "read-only-root": _read_only_root,
    "not-privileged": _not_privileged,
    "drop-all-capabilities": _drop_all_capabilities,
    "seccomp": _seccomp,
}
CONTROLS: Mapping[str, Callable[[Mapping[str, Any]], bool]] = MappingProxyType(_CONTROL_FUNCTIONS)


def _safe_get(mapping: Mapping[str, Any], key: object, default: Any = None) -> Any:
    try:
        return mapping.get(key, default)
    except Exception:
        return default


def _lookup_exception(exceptions: object, workload: str, control: str) -> Mapping[str, Any] | None:
    """Accept legacy tuple-keyed maps plus JSON-safe nested/list encodings."""
    if isinstance(exceptions, Mapping):
        # Legacy in-process form: {(workload, control): record}
        try:
            record = _safe_get(exceptions, (workload, control))
        except (TypeError, AttributeError):
            record = None
        if isinstance(record, Mapping):
            return record

        # JSON-safe nested form: {"workload": {"control": record}}
        nested = _safe_get(exceptions, workload)
        if isinstance(nested, Mapping):
            record = _safe_get(nested, control)
            if isinstance(record, Mapping):
                return record

        # JSON-safe composite key form: {"workload/control": record}
        record = _safe_get(exceptions, f"{workload}/{control}")
        if isinstance(record, Mapping):
            return record

    # Wire-friendly list form:
    # [{"workload": "api", "control": "seccomp", ...}, ...]
    if isinstance(exceptions, Sequence) and not isinstance(exceptions, (str, bytes, bytearray)):
        for record in exceptions:
            if not isinstance(record, Mapping):
                continue
            if _safe_get(record, "workload") == workload and _safe_get(record, "control") == control:
                return record
    return None


def _exception_is_active(record: Mapping[str, Any] | None, now: object) -> bool:
    if record is None or not _is_int(now):
        return False
    expires = _safe_get(record, "expires")
    reason = _safe_get(record, "reason")
    if not _is_int(expires) or expires <= now:
        return False
    if not isinstance(reason, str) or not reason.strip():
        return False
    # Explicit or malformed revocation state fails closed; only False/None are non-revoked.
    revoked = _safe_get(record, "revoked", False)
    if revoked not in (False, None):
        return False
    return True


def get_baseline() -> dict[str, Any]:
    """Return a JSON-serializable description of the enforced baseline."""
    return {
        "schema": BASELINE_SCHEMA,
        "version": BASELINE_VERSION,
        "controls": list(CONTROLS),
        "exception_requirements": [
            "exact workload/control scope",
            "non-blank reason",
            "integer expiry strictly after evaluation time",
            "not explicitly revoked",
        ],
    }


def evaluate(workload: object, spec: object, exceptions: object, today: object) -> dict[str, Any]:
    """Evaluate one workload against the hardening baseline without throwing.

    Hostile or malformed inputs fail closed. Existing callers retain the original
    ``workload``, ``admit``, ``failed`` and ``excepted`` fields; additional schema,
    baseline, and input-error fields make the result self-describing.
    """
    input_errors: list[str] = []
    if not isinstance(workload, str) or not workload.strip():
        workload_id = "<invalid>"
        input_errors.append("invalid-workload")
    else:
        workload_id = workload.strip()

    if not isinstance(spec, Mapping):
        spec_map: Mapping[str, Any] = {}
        input_errors.append("invalid-spec")
    else:
        spec_map = spec

    if not _is_int(today):
        input_errors.append("invalid-time")

    if not isinstance(exceptions, (Mapping, Sequence)) or isinstance(exceptions, (str, bytes, bytearray)):
        exceptions_obj: object = {}
        input_errors.append("invalid-exceptions")
    else:
        exceptions_obj = exceptions

    failed: list[str] = []
    excepted: list[str] = []
    for name, check in CONTROLS.items():
        try:
            passed = bool(check(spec_map))
        except Exception:
            # A policy predicate must never turn malformed input into an
            # admission-process crash. Treat checker failure as control failure.
            passed = False
        if passed:
            continue
        try:
            record = _lookup_exception(exceptions_obj, workload_id, name)
        except Exception:
            record = None
        try:
            active = _exception_is_active(record, today)
        except Exception:
            active = False
        if active:
            excepted.append(name)
        else:
            failed.append(name)

    # Interface errors cannot be waived by a per-control exception.
    admit = not failed and not input_errors
    return {
        "schema": EVALUATION_SCHEMA,
        "baseline_version": BASELINE_VERSION,
        "workload": workload_id,
        "admit": admit,
        "failed": failed,
        "excepted": excepted,
        "input_errors": input_errors,
    }
