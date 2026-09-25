"""Hardened runtime kernel for INV-69.

This module deliberately depends only on the Python standard library so the
safety-critical agent governance rules can be tested even when ``pk_core`` is
not installed.  The ``component`` module adapts this kernel to the larger
Post-Kubernetes conformance framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from collections.abc import Mapping  # C066: abc isinstance is ~5x cheaper than typing.Mapping
from typing import Any
import hashlib
import hmac
import json
import math
import secrets
import threading


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Immutable execution policy metadata for one tool."""

    side_effect: bool
    risk: str
    cost: int = 1

    def __post_init__(self) -> None:
        if self.risk not in {"low", "high"}:
            raise ValueError(f"unsupported tool risk class: {self.risk!r}")
        if not isinstance(self.cost, int) or isinstance(self.cost, bool) or self.cost <= 0:
            raise ValueError("tool cost must be a positive integer")


_TOOLS = {
    "search_docs": ToolSpec(side_effect=False, risk="low", cost=1),
    "run_python": ToolSpec(side_effect=False, risk="high", cost=10),
    "send_email": ToolSpec(side_effect=True, risk="low", cost=2),
    "delete_records": ToolSpec(side_effect=True, risk="high", cost=5),
}
TOOLS: Mapping[str, ToolSpec] = MappingProxyType(_TOOLS)

_SECRET_FIELD_FRAGMENTS = (
    "authorization",
    "credential",
    "passwd",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
)


def _jsonable(value: Any, _seen: set[int] | None = None) -> Any:
    """Return a deterministic JSON-compatible representation for binding.

    Container types are tagged so structurally different values do not collapse
    to the same approval binding. Cycles are represented explicitly. Arbitrary
    objects are reduced to a type plus a best-effort repr; this material is used
    only as HMAC input and is never written to the transcript.
    """
    if _seen is None:
        _seen = set()

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "nan"}
        if math.isinf(value):
            return {"__float__": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, bytes):
        return {"__bytes__": value.hex()}

    if isinstance(value, (Mapping, list, tuple, set, frozenset)):
        marker = id(value)
        if marker in _seen:
            return {"__cycle__": type(value).__qualname__}
        _seen.add(marker)
        try:
            if isinstance(value, Mapping):
                pairs = [[_jsonable(k, _seen), _jsonable(v, _seen)] for k, v in value.items()]
                pairs.sort(key=lambda pair: json.dumps(pair[0], sort_keys=True, separators=(",", ":"), ensure_ascii=False))
                return {"__mapping__": pairs}
            if isinstance(value, list):
                return {"__list__": [_jsonable(v, _seen) for v in value]}
            if isinstance(value, tuple):
                return {"__tuple__": [_jsonable(v, _seen) for v in value]}
            encoded = [_jsonable(v, _seen) for v in value]
            encoded.sort(key=lambda v: json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
            return {"__set__": encoded, "__kind__": type(value).__qualname__}
        finally:
            _seen.discard(marker)

    try:
        rendered = repr(value)
    except Exception:
        rendered = "<repr-failed>"
    return {"__type__": type(value).__qualname__, "__repr__": rendered}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _arg_shape(value: Any) -> Any:
    """Return a bounded, secret-safe shape summary for audit events."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return type(value).__name__
    if isinstance(value, str):
        return {"type": "str", "length": len(value)}
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    if isinstance(value, Mapping):
        fields = []
        for key in list(value.keys())[:32]:
            from .redaction import safe_key
            name = safe_key(key)
            lowered = str(key).lower()
            if name == "<redacted-key>" or any(fragment in lowered for fragment in _SECRET_FIELD_FRAGMENTS):
                fields.append({"name": name, "value": "<redacted>"})
            else:
                fields.append({"name": name, "type": type(value[key]).__name__})
        return {"type": "mapping", "size": len(value), "fields": fields}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {"type": type(value).__name__, "size": len(value)}
    return {"type": type(value).__qualname__}


def _check_bounds(value: Any) -> None:
    from .redaction import check_bounds
    check_bounds(value)


def _within_bounds(value: Any) -> bool:
    try:
        _check_bounds(value)
        return True
    except ValueError:
        return False


def _reason_code(reason: str) -> str | None:
    from .errors import code_for_reason
    return code_for_reason(reason)


def _event_digest(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass
class Agent:
    """Govern one agent's tool execution.

    Compatibility notes:
    - ``name``, ``allow``, ``max_steps``, ``approvals`` and ``transcript`` remain
      public attributes.
    - ``step`` still returns a dictionary containing the original ``arg`` for
      the direct caller, but the stored transcript never persists raw arguments.
    - approvals remain one-use and are now bound to a keyed digest of the exact
      tool arguments, so unhashable arguments (dict/list payloads) are supported.
    """

    name: str
    allow: frozenset[str]
    max_steps: int = 10
    max_cost: int = 100
    max_transcript_events: int = 256
    approvals: set[tuple[str, str]] = field(default_factory=set, init=False)
    transcript: list[dict[str, Any]] = field(default_factory=list, init=False)
    _attempts: int = field(default=0, init=False, repr=False)
    _cost_used: int = field(default=0, init=False, repr=False)
    _approval_key: bytes = field(default_factory=lambda: secrets.token_bytes(32), init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _head: str = field(default="0" * 64, init=False, repr=False)
    _sealed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("agent name must be a non-empty string")
        self.allow = frozenset(self.allow)
        unknown = sorted(set(self.allow).difference(TOOLS))
        if unknown:
            raise ValueError(f"allowlist contains unknown tools: {', '.join(unknown)}")
        for field_name, value in (
            ("max_steps", self.max_steps),
            ("max_cost", self.max_cost),
            ("max_transcript_events", self.max_transcript_events),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if self.max_transcript_events < 2:
            raise ValueError("max_transcript_events must allow at least two audit events")

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def cost_used(self) -> int:
        return self._cost_used

    @property
    def transcript_head(self) -> str:
        return self._head

    def _arg_ref(self, arg: Any, within_bounds: bool | None = None) -> str:
        if within_bounds is None:
            within_bounds = _within_bounds(arg)
        if not within_bounds:
            # Oversized/over-deep input: bind to a fixed marker so it can never match an approval.
            return hmac.new(self._approval_key, b"\x00<oversized-argument>", hashlib.sha256).hexdigest()
        return hmac.new(self._approval_key, _canonical_bytes(arg), hashlib.sha256).hexdigest()

    def _append(self, event: dict[str, Any]) -> dict[str, Any]:
        if self._sealed:
            raise RuntimeError("agent audit stream is sealed")
        if len(self.transcript) >= self.max_transcript_events:
            self._sealed = True
            raise RuntimeError("agent audit stream capacity exhausted; refusing further operations")
        material = dict(event)
        material["step"] = len(self.transcript)
        material["prev_hash"] = self._head
        material["event_hash"] = _event_digest(material)
        self.transcript.append(material)
        self._head = material["event_hash"]
        return material

    def verify_transcript(self) -> bool:
        """Verify the local hash chain and sequence numbers.

        A production deployment should persist/anchor ``transcript_head`` in an
        external append-only or signed audit system; this in-memory chain alone
        cannot protect against a process owner rewriting both history and head.
        """
        with self._lock:
            previous = "0" * 64
            for index, stored in enumerate(self.transcript):
                if stored.get("step") != index or stored.get("prev_hash") != previous:
                    return False
                event = dict(stored)
                claimed = event.pop("event_hash", None)
                if claimed != _event_digest(event):
                    return False
                previous = claimed
            return previous == self._head

    def export_transcript(self) -> dict[str, Any]:
        """Return the versioned public transcript envelope."""
        with self._lock:
            return {
                "schema": "PK_AGENT_TRANSCRIPT/1",
                "agent": self.name,
                "head": self._head,
                "events": [dict(event) for event in self.transcript],
            }

    def approve(self, tool: str, arg: Any, approver: str) -> None:
        with self._lock:
            if not isinstance(approver, str) or not approver.strip() or approver == self.name:
                raise PermissionError(f"{approver!r} cannot approve actions of agent {self.name!r}")
            if not isinstance(tool, str) or not tool:
                raise ValueError("tool must be a non-empty string")
            if tool not in TOOLS:
                raise ValueError(f"unknown tool: {tool!r}")
            if tool not in self.allow:
                raise PermissionError(f"{tool!r} is not in the agent allowlist")
            if not TOOLS[tool].side_effect:
                raise ValueError(f"{tool!r} does not require approval")

            if not _within_bounds(arg):
                raise ValueError("argument exceeds input limits")
            arg_ref = self._arg_ref(arg)
            approval = (tool, arg_ref)
            self.approvals.add(approval)
            try:
                self._append(
                    {
                        "schema": "PK_AGENT_APPROVAL/1",
                        "agent": self.name,
                        "outcome": "approved",
                        "reason": "one-use approval recorded",
                        "tool": tool,
                        "arg_ref": arg_ref,
                        "arg_shape": _arg_shape(arg),
                        "by": approver.strip(),
                    }
                )
            except Exception:
                self.approvals.discard(approval)
                raise

    def step(self, tool: str, arg: Any) -> dict[str, Any]:
        with self._lock:
            if self._sealed:
                return {
                    "outcome": "refused",
                    "reason": "audit stream sealed",
                    "code": "AGT-CAP-004",
                    "tool": tool,
                    "arg": arg,
                    "step": len(self.transcript),
                    "recorded": False,
                }

            tool_is_valid_string = isinstance(tool, str) and bool(tool)
            in_bounds = _within_bounds(arg)   # C066: one bounded traversal per step, reused below
            tool_label = tool if tool_is_valid_string else f"<invalid:{type(tool).__name__}>"
            consumed_approval: tuple[str, str] | None = None
            charged_cost = 0

            if self._attempts >= self.max_steps:
                event = {
                    "schema": "PK_AGENT_STEP/1",
                    "agent": self.name,
                    "outcome": "refused",
                    "reason": "step budget exhausted",
                    "tool": tool_label,
                    "arg_ref": self._arg_ref(arg, in_bounds),
                    "arg_shape": _arg_shape(arg),
                    "attempt": self._attempts,
                    "cost_used": self._cost_used,
                }
            elif not in_bounds:
                self._attempts += 1
                event = {
                    "schema": "PK_AGENT_STEP/1",
                    "agent": self.name,
                    "outcome": "refused",
                    "reason": "argument exceeds input limits",
                    "tool": tool_label,
                    "arg_ref": self._arg_ref(arg, in_bounds),
                    "arg_shape": {"type": "oversized"},
                    "attempt": self._attempts,
                    "cost_used": self._cost_used,
                }
            elif not tool_is_valid_string or tool not in TOOLS or tool not in self.allow:
                self._attempts += 1
                event = {
                    "schema": "PK_AGENT_STEP/1",
                    "agent": self.name,
                    "outcome": "refused",
                    "reason": f"{tool_label} not in allowlist",
                    "tool": tool_label,
                    "arg_ref": self._arg_ref(arg, in_bounds),
                    "arg_shape": _arg_shape(arg),
                    "attempt": self._attempts,
                    "cost_used": self._cost_used,
                }
            else:
                spec = TOOLS[tool]
                self._attempts += 1
                arg_ref = self._arg_ref(arg, in_bounds)
                if spec.side_effect and (tool, arg_ref) not in self.approvals:
                    event = {
                        "schema": "PK_AGENT_STEP/1",
                        "agent": self.name,
                        "outcome": "pending",
                        "reason": "awaiting one-use approval",
                        "tool": tool,
                        "arg_ref": arg_ref,
                        "arg_shape": _arg_shape(arg),
                        "attempt": self._attempts,
                        "cost_used": self._cost_used,
                    }
                elif self._cost_used + spec.cost > self.max_cost:
                    event = {
                        "schema": "PK_AGENT_STEP/1",
                        "agent": self.name,
                        "outcome": "refused",
                        "reason": "cost budget exhausted",
                        "tool": tool,
                        "arg_ref": arg_ref,
                        "arg_shape": _arg_shape(arg),
                        "attempt": self._attempts,
                        "cost_used": self._cost_used,
                    }
                else:
                    if spec.side_effect:
                        consumed_approval = (tool, arg_ref)
                        self.approvals.discard(consumed_approval)
                    charged_cost = spec.cost
                    self._cost_used += charged_cost
                    tier = "heavy" if spec.risk == "high" else "fast"
                    event = {
                        "schema": "PK_AGENT_STEP/1",
                        "agent": self.name,
                        "outcome": "ran",
                        "reason": "policy checks passed",
                        "tool": tool,
                        "arg_ref": arg_ref,
                        "arg_shape": _arg_shape(arg),
                        "attempt": self._attempts,
                        "cost": spec.cost,
                        "cost_used": self._cost_used,
                        "sandbox": tier,
                    }

            try:
                stored = self._append(event)
            except RuntimeError:
                if charged_cost:
                    self._cost_used -= charged_cost
                if consumed_approval is not None:
                    self.approvals.add(consumed_approval)
                self._sealed = True
                return {
                    "outcome": "refused",
                    "reason": "audit stream capacity exhausted",
                    "code": "AGT-CAP-004",
                    "tool": tool,
                    "arg": arg,
                    "step": len(self.transcript),
                    "recorded": False,
                }

            # Keep direct-call compatibility without persisting raw arguments.
            result = {k: v for k, v in stored.items() if k not in {"arg_ref", "arg_shape", "prev_hash", "event_hash"}}
            result["arg"] = arg
            result["recorded"] = True
            result["code"] = _reason_code(stored["reason"])
            return result
