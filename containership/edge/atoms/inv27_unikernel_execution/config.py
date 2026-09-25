"""Declarative runtime configuration with provenance, atomic update and rollback
(MC-029..MC-033; C031-C035, C039).

``PK_UNIKERNEL_CONFIG/1`` is validated strictly before activation.  ``ConfigStore`` holds
immutable generations; ``apply`` validates, then swaps the active generation under a lock (all or
nothing); ``rollback`` re-activates a prior generation by number.  Every generation records who
applied it, why, its sha256, and the previous generation's hash (tamper-evident history).
Secrets are referenced (``secret_ref``), never inlined; a literal secret-looking value fails
validation, and ``redacted()`` is what diagnostics print.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType

from .errors import UkError
from .redaction import redact

SCHEMA = "PK_UNIKERNEL_CONFIG/1"
_KEYS = {"schema", "environment", "site_architecture", "permitted_syscalls", "trust_root_ref", "provenance_policy",
         "isolation", "limits", "vmm", "quotas", "features"}
_SECRET_LIKE = re.compile(r"(?i)(-----BEGIN|\bsk-|\bghp_|\bAKIA)")
_SC = re.compile(r"^(solo5\.)?[a-z0-9_]{1,40}$")


def _bad(msg: str) -> UkError:
    return UkError("UK_CONFIG_INVALID", msg)


def validate(cfg: dict) -> dict:
    if not isinstance(cfg, dict) or cfg.get("schema") != SCHEMA:
        raise UkError("UK_UNSUPPORTED_VERSION", f"config schema must be {SCHEMA}")
    if set(cfg) != _KEYS:
        raise _bad(f"config keys: unknown {sorted(set(cfg) - _KEYS)} missing {sorted(_KEYS - set(cfg))}")
    if cfg["environment"] not in ("dev", "staging", "prod", "edge"):
        raise _bad("environment must be dev|staging|prod|edge")
    if cfg["site_architecture"] not in ("x86_64", "aarch64"):
        raise _bad("site_architecture must be x86_64|aarch64")
    ps = cfg["permitted_syscalls"]
    if not isinstance(ps, list) or not ps or len(ps) > 512 or not all(isinstance(x, str) and _SC.match(x) for x in ps):
        raise _bad("permitted_syscalls must be a non-empty list of syscall names")
    tr = cfg["trust_root_ref"]
    if not isinstance(tr, dict) or set(tr) != {"secret_ref", "max_age_hours"} or not isinstance(tr["max_age_hours"], int) \
            or not 1 <= tr["max_age_hours"] <= 168:
        raise _bad("trust_root_ref must be {secret_ref, max_age_hours 1..168}")
    pp = cfg["provenance_policy"]
    if not isinstance(pp, dict) or set(pp) != {"approved_builders", "approved_toolchains", "require_source_digest"}:
        raise _bad("provenance_policy keys")
    if cfg["environment"] == "prod" and pp["require_source_digest"] is not True:
        raise _bad("prod requires require_source_digest: true")
    lim = cfg["limits"]
    need = {"max_image_bytes": (4096, 256 << 20), "parser_work_budget": (10_000, 200_000_000),
            "admission_deadline_ms": (10, 60_000), "boot_deadline_ms": (100, 120_000)}
    if not isinstance(lim, dict) or set(lim) != set(need):
        raise _bad(f"limits keys must be {sorted(need)}")
    for k, (lo, hi) in need.items():
        v = lim[k]
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise _bad(f"limits.{k} must be an integer in {lo}..{hi}")
    vmm = cfg["vmm"]
    if not isinstance(vmm, dict) or vmm.get("backend") not in ("qemu", "firecracker", "script") \
            or vmm.get("accel") not in ("tcg", "kvm"):
        raise _bad("vmm.backend qemu|firecracker|script and vmm.accel tcg|kvm required")
    if cfg["environment"] == "prod" and vmm["backend"] == "script":
        raise _bad("the script backend is test-only and refused in prod")
    q = cfg["quotas"]
    if not isinstance(q, dict) or not isinstance(q.get("max_instances_per_tenant"), int) or not 1 <= q["max_instances_per_tenant"] <= 10_000:
        raise _bad("quotas.max_instances_per_tenant 1..10000 required")
    f = cfg["features"]
    if not isinstance(f, dict) or not all(isinstance(v, bool) for v in f.values()):
        raise _bad("features must map names to booleans")
    if f.get("allow_attested_facts_for_stripped", False) and cfg["environment"] == "prod" and not f.get("attested_facts_approved", False):
        raise _bad("attested-facts mode in prod needs features.attested_facts_approved")
    for path, v in _walk(cfg):
        if isinstance(v, str) and _SECRET_LIKE.search(v):
            raise _bad(f"{path} looks like an inline secret; use a secret_ref")
    return cfg


def _walk(o, p="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, f"{p}[{i}]")
    else:
        yield p, o


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _freeze(o):
    if isinstance(o, dict):
        return MappingProxyType({k: _freeze(v) for k, v in o.items()})
    if isinstance(o, list):
        return tuple(_freeze(v) for v in o)
    return o


@dataclass(frozen=True)
class Generation:
    number: int
    config: object          # frozen mapping
    sha256: str
    prev_sha256: str
    actor: str
    reason: str
    applied_at: float


@dataclass
class ConfigStore:
    clock: object = time.time
    history: list = field(default_factory=list)
    active: Generation | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    max_history: int = 100

    def apply(self, cfg: dict, *, actor: str, reason: str) -> Generation:
        if not actor or not reason:
            raise _bad("actor and reason are required for every change (provenance)")
        cfg = validate(copy.deepcopy(cfg))
        with self._lock:
            prev = self.history[-1].sha256 if self.history else "0" * 64
            g = Generation(len(self.history) + 1, _freeze(cfg), digest(cfg), prev, actor, reason, self.clock())
            self.history.append(g)
            if len(self.history) > self.max_history:
                raise _bad("config history full; export and compact first")
            self.active = g
            return g

    def rollback(self, number: int, *, actor: str, reason: str) -> Generation:
        with self._lock:
            target = next((g for g in self.history if g.number == number), None)
        if target is None:
            raise _bad(f"no generation {number}")
        return self.apply(_thaw(target.config), actor=actor, reason=f"rollback to {number}: {reason}")

    def verify_history(self) -> list[str]:
        errs, prev = [], "0" * 64
        for g in self.history:
            if g.prev_sha256 != prev:
                errs.append(f"generation {g.number}: broken prev link")
            if digest(_thaw(g.config)) != g.sha256:
                errs.append(f"generation {g.number}: content hash mismatch")
            prev = g.sha256
        return errs

    def redacted(self) -> dict:
        return redact(_thaw(self.active.config)) if self.active else {}


def _thaw(o):
    if isinstance(o, MappingProxyType) or isinstance(o, dict):
        return {k: _thaw(v) for k, v in o.items()}
    if isinstance(o, tuple):
        return [_thaw(v) for v in o]
    return o


def example(environment: str = "dev") -> dict:
    return {"schema": SCHEMA, "environment": environment, "site_architecture": "x86_64",
            "permitted_syscalls": ["read", "write", "clock_gettime", "solo5.console_write", "solo5.clock_monotonic"],
            "trust_root_ref": {"secret_ref": "vault://pk/inv27/trust-root", "max_age_hours": 24},
            "provenance_policy": {"approved_builders": ["pk-reference-builder"],
                                  "approved_toolchains": {"unikraft": ["0.17.0"], "solo5": ["0.9.0"]},
                                  "require_source_digest": True},
            "isolation": {"allow_network": ["none"], "allowed_devices": ["serial"], "allowed_storage": []},
            "limits": {"max_image_bytes": 64 << 20, "parser_work_budget": 20_000_000,
                       "admission_deadline_ms": 5000, "boot_deadline_ms": 10_000},
            "vmm": {"backend": "qemu", "accel": "kvm"},
            "quotas": {"max_instances_per_tenant": 16},
            "features": {"allow_attested_facts_for_stripped": False}}
