"""Quarantine / emergency isolation control (MC-11).

Directives are signed (Ed25519) by a quarantine authority, versioned, scoped,
time-bounded and carry their approvers.  The registry is checked before session
establishment and before each privileged dispatch; activation synchronously
terminates matching live sessions through registered terminators, so no new
operation can start after activation returns (MC-11.013/.014/.016).

Precedence: an active quarantine overrides every allow decision from policy or
configuration (MC-11.003).  Directives persist to disk atomically and are
re-verified on load; unverifiable persisted state fails safe to *deny* for the
scopes it names (MC-11.004/.012).
"""
from __future__ import annotations

import enum
import json
import os
import pathlib
import stat
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .errors import ErrorCode, Inv36Error


class QuarantineError(Inv36Error, PermissionError):
    code = ErrorCode.QUARANTINED


class Scope(str, enum.Enum):
    PEER = "peer"            # subject identity
    TENANT = "tenant"
    WORKLOAD = "workload"
    ENDPOINT = "endpoint"    # cid:port
    NODE = "node"
    SITE = "site"
    PROTOCOL = "protocol"    # e.g. PK_CTRL_FRAME/2
    OPERATION = "operation"  # message type name
    PROCESS = "process"
    GLOBAL = "global"


class Action(str, enum.Enum):
    DENY_NEW = "deny_new_sessions"
    TERMINATE = "terminate_sessions"          # implies deny_new
    DRAIN_ONLY = "receive_drain_only"         # existing sessions may receive, no new privileged ops
    BLOCK_OPERATIONS = "block_operations"     # scope must be OPERATION
    DISABLE = "disable_component"


BROAD_SCOPES = {Scope.NODE, Scope.SITE, Scope.GLOBAL, Scope.PROCESS, Scope.PROTOCOL}
MAX_TTL_S = 7 * 86400
_LABEL = b"PK_CTRL_QUARANTINE/1\x00"


def _canon(obj: Mapping[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@dataclass(frozen=True)
class Directive:
    directive_id: str
    version: int
    op: str               # "apply" | "lift"
    scope: Scope
    value: str
    action: Action
    issued_at: float
    ttl_s: float
    requested_by: str
    approvers: tuple[str, ...]
    reason: str
    confirm_global: bool = False

    def body(self) -> dict:
        return {"id": self.directive_id, "version": self.version, "op": self.op, "scope": self.scope.value,
                "value": self.value, "action": self.action.value,
                "issued_at": float(self.issued_at), "ttl_s": float(self.ttl_s),
                "requested_by": self.requested_by, "approvers": list(self.approvers), "reason": self.reason[:256],
                "confirm_global": self.confirm_global}

    @classmethod
    def from_body(cls, b: Mapping[str, Any]) -> "Directive":
        return cls(str(b["id"]), int(b["version"]), str(b["op"]), Scope(b["scope"]), str(b["value"]),
                   Action(b["action"]), float(b["issued_at"]), float(b["ttl_s"]), str(b["requested_by"]),
                   tuple(b["approvers"]), str(b["reason"]), bool(b.get("confirm_global", False)))

    @property
    def expires_at(self) -> float:
        return self.issued_at + self.ttl_s


def sign_directive(signer, d: Directive) -> dict:
    return {"directive": d.body(), "sig": signer.sign(_LABEL + _canon(d.body())).hex()}


@dataclass(frozen=True)
class Context:
    subject: str = ""
    tenant: str = ""
    workload: str = ""
    endpoint: str = ""
    node: str = ""
    site: str = ""
    protocol: str = "PK_CTRL_FRAME/2"
    operation: str = ""
    process: str = ""

    def value(self, scope: Scope) -> str:
        if scope is Scope.GLOBAL:
            return "*"
        return self.subject if scope is Scope.PEER else getattr(self, scope.value)


@dataclass
class QuarantineRegistry:
    authority_keys: dict[str, bytes]           # key_id -> Ed25519 public bytes
    state_path: pathlib.Path | None = None
    kill_switch_path: pathlib.Path | None = None
    clock: Callable[[], float] = time.time
    audit: Callable[[str, dict], None] | None = None
    two_person_scopes: frozenset[Scope] = frozenset(BROAD_SCOPES)
    _active: dict[str, Directive] = field(default_factory=dict, init=False)
    _highest_version: int = field(default=0, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _terminators: list[Callable[[Directive], int]] = field(default_factory=list, init=False, repr=False)
    fail_safe_deny_all: bool = field(default=False, init=False)
    last_activation_latency_s: float | None = field(default=None, init=False)

    # -- persistence -------------------------------------------------------------------
    def load(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text())
            envelopes = data["directives"]
            with self._lock:
                self._highest_version = int(data.get("highest_version", 0))
                for env in envelopes:
                    d = self._verify(env)
                    if d.expires_at > self.clock():
                        self._active[d.directive_id] = d
        except (ValueError, KeyError, TypeError, QuarantineError):
            # MC-11.012: unverifiable persisted quarantine state fails safe (deny all) until an operator acts.
            self.fail_safe_deny_all = True
            self._emit("quarantine.rejected", reason="persisted_state_unverifiable")

    def _persist(self, envelopes: list[dict]) -> None:
        if not self.state_path:
            return
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"highest_version": self._highest_version, "directives": envelopes}))
        with open(tmp, "rb+") as fh:
            os.fsync(fh.fileno())
        os.replace(tmp, self.state_path)

    # -- hooks -------------------------------------------------------------------------
    def register_terminator(self, fn: Callable[[Directive], int]) -> None:
        self._terminators.append(fn)

    def _emit(self, ev: str, **data) -> None:
        if self.audit:
            self.audit(ev, data)

    # -- directive handling ------------------------------------------------------------
    def _verify(self, envelope: Mapping[str, Any]) -> Directive:
        try:
            body = envelope["directive"]
            sig = bytes.fromhex(envelope["sig"])
            d = Directive.from_body(body)
        except (KeyError, ValueError, TypeError) as exc:
            raise QuarantineError("malformed directive", code=ErrorCode.DIRECTIVE_INVALID) from exc
        payload = _LABEL + _canon(d.body())
        for pub in self.authority_keys.values():
            try:
                Ed25519PublicKey.from_public_bytes(pub).verify(sig, payload)
                return d
            except InvalidSignature:
                continue
        raise QuarantineError("directive signature not from a quarantine authority",
                              code=ErrorCode.DIRECTIVE_INVALID)

    def _validate(self, d: Directive) -> None:
        if d.op not in ("apply", "lift"):
            raise QuarantineError("unknown directive op", code=ErrorCode.DIRECTIVE_INVALID)
        if not 0 < d.ttl_s <= MAX_TTL_S:
            raise QuarantineError("ttl out of range", code=ErrorCode.DIRECTIVE_SCOPE)
        if d.scope is Scope.GLOBAL and (d.value != "*" or not d.confirm_global):
            raise QuarantineError("global scope requires value '*' and confirm_global", code=ErrorCode.DIRECTIVE_SCOPE)
        if d.scope is not Scope.GLOBAL and (not d.value or "*" in d.value or len(d.value) > 128):
            raise QuarantineError("scope selector must be a single explicit value", code=ErrorCode.DIRECTIVE_SCOPE)
        if d.action is Action.BLOCK_OPERATIONS and d.scope is not Scope.OPERATION:
            raise QuarantineError("block_operations requires operation scope", code=ErrorCode.DIRECTIVE_SCOPE)
        approvers = set(d.approvers) - {d.requested_by}
        if d.scope in self.two_person_scopes and len(approvers) < 1:
            raise QuarantineError("broad scope requires a second approver", code=ErrorCode.DIRECTIVE_SCOPE)
        if not d.approvers:
            raise QuarantineError("directive has no approver", code=ErrorCode.DIRECTIVE_SCOPE)
        now = self.clock()
        if d.issued_at > now + 300 or d.expires_at <= now:
            raise QuarantineError("directive outside validity window", code=ErrorCode.DIRECTIVE_INVALID)
        if d.version <= self._highest_version:
            raise QuarantineError("stale or replayed directive version", code=ErrorCode.DIRECTIVE_INVALID)

    def submit(self, envelope: Mapping[str, Any], *, actor: str) -> Directive:
        t0 = time.monotonic()
        self._emit("quarantine.request", actor=actor)
        try:
            d = self._verify(envelope)
            with self._lock:
                self._validate(d)
                if d.op == "lift":
                    target = self._active.get(d.value)
                    if target is None:
                        raise QuarantineError("no such active quarantine", code=ErrorCode.DIRECTIVE_SCOPE)
                    if actor == target.value or d.requested_by == target.value:
                        raise QuarantineError("quarantined subject cannot lift its own quarantine",
                                              code=ErrorCode.DIRECTIVE_SCOPE)
                    self._highest_version = d.version
                    del self._active[d.value]
                    self._persist(self._envelopes_locked(extra=None))
                    self._emit("quarantine.remove", directive=d.value, actor=actor, approvers=list(d.approvers))
                    return d
                if actor == d.value:
                    raise QuarantineError("subject cannot quarantine-manage itself", code=ErrorCode.DIRECTIVE_SCOPE)
                self._highest_version = d.version
                self._active[d.directive_id] = d
                self._signed[d.directive_id] = dict(envelope)
                self._persist(self._envelopes_locked(extra=None))
                terminated = 0
                if d.action in (Action.TERMINATE, Action.DISABLE):
                    for fn in list(self._terminators):
                        terminated += fn(d)
            self.last_activation_latency_s = time.monotonic() - t0
            self._emit("quarantine.activate", directive=d.directive_id, scope=d.scope.value, value=d.value,
                       action=d.action.value, approvers=list(d.approvers), terminated=terminated,
                       latency_ms=round(self.last_activation_latency_s * 1000, 3))
            return d
        except QuarantineError as exc:
            self._emit("quarantine.rejected", actor=actor, reason=exc.code.name)
            raise

    _signed: dict[str, dict] = field(default_factory=dict, init=False, repr=False)

    def _envelopes_locked(self, extra) -> list[dict]:
        return [self._signed[i] for i in self._active if i in self._signed]

    def expire(self) -> list[str]:
        now = self.clock()
        with self._lock:
            gone = [i for i, d in self._active.items() if d.expires_at <= now]
            for i in gone:
                del self._active[i]
                self._signed.pop(i, None)
            if gone:
                self._persist(self._envelopes_locked(extra=None))
        for i in gone:
            self._emit("quarantine.expire", directive=i)
        return gone

    # -- enforcement -------------------------------------------------------------------
    def kill_switch_engaged(self) -> bool:
        """Local OS-permission-guarded kill switch (MC-11.017).

        Presence of the file disables the component.  Engagement always wins
        (fail safe); insecure permissions are additionally reported.
        """
        p = self.kill_switch_path
        if not p or not p.exists():
            return False
        try:
            st = p.stat()
            parent = p.parent.stat()
            insecure = bool(st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)) or bool(parent.st_mode & stat.S_IWOTH)
        except OSError:
            insecure = True
        self._emit("killswitch.engaged", path=str(p), insecure_permissions=insecure)
        return True

    def matching(self, ctx: Context) -> list[Directive]:
        self.expire()
        with self._lock:
            return [d for d in self._active.values()
                    if d.scope is Scope.GLOBAL or (ctx.value(d.scope) and ctx.value(d.scope) == d.value)]

    def check_session(self, ctx: Context) -> None:
        if self.fail_safe_deny_all or self.kill_switch_engaged():
            raise QuarantineError("component disabled (fail-safe or kill switch)")
        for d in self.matching(ctx):
            if d.action in (Action.DENY_NEW, Action.TERMINATE, Action.DISABLE, Action.DRAIN_ONLY):
                raise QuarantineError("session establishment quarantined",
                                      detail={"directive": d.directive_id, "scope": d.scope.value})

    def check_operation(self, ctx: Context, *, privileged: bool = True) -> None:
        if self.fail_safe_deny_all or self.kill_switch_engaged():
            raise QuarantineError("component disabled (fail-safe or kill switch)")
        for d in self.matching(ctx):
            if d.action in (Action.TERMINATE, Action.DISABLE):
                raise QuarantineError("operation quarantined", detail={"directive": d.directive_id})
            if d.action is Action.DRAIN_ONLY and privileged:
                raise QuarantineError("drain-only quarantine", detail={"directive": d.directive_id})
            if d.action is Action.BLOCK_OPERATIONS and ctx.operation == d.value:
                raise QuarantineError("operation class blocked", detail={"directive": d.directive_id})

    def state(self) -> dict:
        """Exposed state without secrets (MC-11.018)."""
        with self._lock:
            return {"fail_safe_deny_all": self.fail_safe_deny_all,
                    "kill_switch": bool(self.kill_switch_path and self.kill_switch_path.exists()),
                    "active": [{"id": d.directive_id, "scope": d.scope.value, "value": d.value,
                                "action": d.action.value, "expires_at": d.expires_at} for d in self._active.values()],
                    "highest_version": self._highest_version}
