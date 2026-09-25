"""M27-M32 - configuration schema, secure defaults, overlays, provenance,
atomic distributed activation, rollback to last-known-good, secret references.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass, field

from . import limits as _limits
from .errors import FabricError

CONFIG_SCHEMA_VERSION = "inv60.config/1.0.0"

# field -> (type, default, constraint, protected)   protected = lower-trust overlays may not weaken
SCHEMA: dict[str, tuple] = {
    "transport.require_tls":        (bool, True, None, "true_only"),
    "transport.nats_url":           (str, "tls://127.0.0.1:4222", r"^tls://", "pattern"),
    "auth.allow_anonymous":         (bool, False, None, "false_only"),
    "auth.token_ttl_s":             (float, 300.0, (10.0, 900.0), None),
    "auth.max_clock_skew_s":        (float, 30.0, (0.0, 120.0), None),
    "membership.suspect_after_s":   (float, 3.0, (0.5, 60.0), None),
    "membership.lost_after_s":      (float, 8.0, (1.0, 600.0), None),
    "membership.isolated_serving_s": (float, 300.0, (0.0, 3600.0), None),
    "placement.allowed_regions":    (list, [], None, "residency"),
    "signing.min_slsa_level":       (int, 2, (1, 4), "min_only"),
    "signing.require_signature":    (bool, True, None, "true_only"),
    "resilience.max_attempts":      (int, 4, (1, 10), None),
    "resilience.default_deadline_s": (float, 5.0, (0.01, 300.0), None),
    "resilience.breaker_threshold": (int, 5, (1, 100), None),
    "telemetry.trace_sample_ratio": (float, 0.1, (0.0, 1.0), None),
    "telemetry.export_endpoint":    (str, "", None, None),
    "telemetry.retention_days":     (int, 30, (1, 400), None),
    "storage.state_dir":            (str, "./state", None, None),
    "features.batching":            (bool, False, None, None),
    "secrets.nats_credentials":     (dict, {"ref": "secret://vault/inv60/nats-creds#v1"}, "secretref", None),
    **{f"limits.{k}": (type(v) if not isinstance(v, int) else (int if isinstance(_limits.BOUNDS[k][0], int) else float),
                       v, _limits.BOUNDS[k], None) for k, v in _limits.DEFAULTS.items()},
}
SECRET_REF = re.compile(r"^secret://(vault|k8s|kms|env-dev)/[A-Za-z0-9._/-]+(#v[0-9]+)?$")
TRUST_ORDER = {"base": 3, "production": 3, "staging": 2, "edge": 2, "disconnected": 2, "test": 1, "development": 1}


def defaults() -> dict:
    return {k: copy.deepcopy(v[1]) for k, v in SCHEMA.items()}


def validate(cfg: dict) -> dict:
    """Validate a fully rendered config; returns normalized copy or raises INVALID_ARGUMENT."""
    errors = []
    out = {}
    for k in cfg:
        if k not in SCHEMA:
            errors.append(f"unknown field {k}")
    for k, (typ, default, cons, _prot) in SCHEMA.items():
        v = cfg.get(k, copy.deepcopy(default))
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is int and isinstance(v, bool) or not isinstance(v, typ):
            errors.append(f"{k}: expected {typ.__name__}")
            continue
        if isinstance(cons, tuple) and not (cons[0] <= v <= cons[1]):
            errors.append(f"{k}: {v} outside [{cons[0]}, {cons[1]}]")
        if isinstance(cons, str) and cons not in ("secretref",) and not re.search(cons, v):
            errors.append(f"{k}: {v!r} does not match {cons}")
        if cons == "secretref":
            if set(v) != {"ref"} or not SECRET_REF.match(str(v.get("ref", ""))):
                errors.append(f"{k}: must be a secret reference {{'ref': 'secret://...'}}, never a value")
        out[k] = v
    if out.get("membership.suspect_after_s", 0) >= out.get("membership.lost_after_s", 0):
        errors.append("membership.suspect_after_s must be < membership.lost_after_s")
    if out.get("transport.require_tls") is False or out.get("auth.allow_anonymous") is True:
        errors.append("insecure transport/auth settings are not permitted")
    if errors:
        raise FabricError("INVALID_ARGUMENT", "; ".join(errors), detail={"errors": len(errors)})
    return out


def render(base: dict, *overlays: tuple[str, dict]) -> dict:
    """Merge overlays onto base deterministically: scalars replace, lists replace,
    ``None`` deletes (reverts to default). Lower-trust overlays may not weaken
    protected fields; residency lists may only narrow."""
    cfg = validate(base)
    for env, ov in overlays:
        if env not in TRUST_ORDER:
            raise FabricError("INVALID_ARGUMENT", f"unknown environment {env!r}")
        for k, v in sorted(ov.items()):
            if k not in SCHEMA:
                raise FabricError("INVALID_ARGUMENT", f"overlay {env}: unknown field {k}")
            prot = SCHEMA[k][3]
            cur = cfg[k]
            new = copy.deepcopy(SCHEMA[k][1]) if v is None else v
            if prot == "true_only" and cur is True and new is not True:
                raise FabricError("PERMISSION_DENIED", f"overlay {env} may not disable {k}")
            if prot == "false_only" and cur is False and new is not False:
                raise FabricError("PERMISSION_DENIED", f"overlay {env} may not enable {k}")
            if prot == "min_only" and isinstance(new, int) and new < cur:
                raise FabricError("PERMISSION_DENIED", f"overlay {env} may not lower {k}")
            if prot == "residency" and cur and not set(new or []) <= set(cur):
                raise FabricError("PERMISSION_DENIED", f"overlay {env} may only narrow {k}")
            cfg[k] = new
    return validate(cfg)


def digest(cfg: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def diff(a: dict, b: dict) -> list[dict]:
    return [{"field": k, "from": a.get(k), "to": b.get(k)} for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


@dataclass
class Revision:
    id: str
    generation: int
    config: dict
    digest: str
    schema: str
    source_commit: str
    author: str
    approver: str | None
    change_ref: str
    environment: str
    created_at: float
    secret_refs: dict

    def provenance(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "config"}
        return d


@dataclass
class Target:
    name: str
    online: bool = True
    fail_on_commit: bool = False
    active_generation: int = 0
    prepared: int | None = None
    healthy_after: bool = True


class ConfigController:
    """Two-phase activation with monotonic generations, per-target status and LKG rollback."""

    def __init__(self, targets: list[Target], ledger=None, clock=time.time):
        self.targets = {t.name: t for t in targets}
        self.revisions: dict[int, Revision] = {}
        self.active: int = 0
        self.last_known_good: int = 0
        self.ledger = ledger
        self.clock = clock
        self._activating = False

    def propose(self, cfg: dict, *, source_commit: str, author: str, approver: str | None,
                change_ref: str, environment: str) -> Revision:
        cfg = validate(cfg)
        if not re.fullmatch(r"[0-9a-f]{40}", source_commit or ""):
            raise FabricError("INVALID_ARGUMENT", "source_commit must be an immutable 40-hex commit id")
        if environment == "production" and (not approver or approver == author):
            raise FabricError("PERMISSION_DENIED", "production revision needs an independent approver")
        gen = max(self.revisions, default=0) + 1
        secrets = {k: v["ref"] for k, v in cfg.items() if isinstance(v, dict) and "ref" in v}
        rev = Revision(f"cfg-{gen:06d}", gen, cfg, digest(cfg), CONFIG_SCHEMA_VERSION, source_commit, author,
                       approver, change_ref, environment, self.clock(), secrets)
        self.revisions[gen] = rev
        self._audit("config.proposed", author, rev.provenance())
        return rev

    def activate(self, generation: int, *, min_success_ratio: float = 1.0) -> dict:
        if self._activating:
            raise FabricError("ALREADY_EXISTS", "another activation is in progress")
        if generation not in self.revisions:
            raise FabricError("NOT_FOUND", f"generation {generation} unknown")
        if generation <= self.active:
            raise FabricError("STALE_GENERATION", f"generation {generation} <= active {self.active}")
        self._activating = True
        try:
            per = {}
            # phase 1: prepare (all-or-nothing readiness)
            for t in self.targets.values():
                if not t.online:
                    per[t.name] = "unreachable"
            ready = [t for t in self.targets.values() if t.online]
            if len(ready) / max(1, len(self.targets)) < min_success_ratio:
                self._audit("config.aborted", None, {"generation": generation, "per_target": per})
                return {"code": "PARTIAL" if ready else "UNAVAILABLE", "generation": generation,
                        "committed": False, "per_target": per}
            for t in ready:
                t.prepared = generation
            # phase 2: commit
            committed, failed = [], []
            for t in ready:
                if t.fail_on_commit:
                    failed.append(t.name)
                    per[t.name] = "commit_failed"
                else:
                    t.active_generation = generation
                    t.prepared = None
                    committed.append(t.name)
                    per[t.name] = "committed"
            healthy = all(self.targets[n].healthy_after for n in committed)
            if failed or not healthy:
                prev = self.active
                for n in committed:                     # compensate: roll back to previous
                    self.targets[n].active_generation = prev
                    per[n] = "rolled_back"
                self._audit("config.rolled_back", None, {"generation": generation, "to": prev, "per_target": per})
                return {"code": "PARTIAL", "generation": generation, "committed": False,
                        "rolled_back_to": prev, "per_target": per}
            self.active = generation
            self.last_known_good = generation
            self._audit("config.activated", None, {"generation": generation, "digest": self.revisions[generation].digest})
            return {"code": "OK", "generation": generation, "committed": True, "per_target": per}
        finally:
            self._activating = False

    def reconcile_offline(self, name: str) -> str:
        """A target that was offline during activation converges to the active generation on return."""
        t = self.targets[name]
        t.online = True
        if t.active_generation != self.active:
            t.active_generation = self.active
            self._audit("config.reconciled", None, {"target": name, "generation": self.active})
            return "converged"
        return "current"

    def rollback(self, actor: str) -> dict:
        """Roll back to the previous LKG revision (idempotent)."""
        candidates = sorted(g for g in self.revisions if g < self.active)
        if not candidates:
            return {"code": "OK", "generation": self.active, "note": "nothing older to roll back to"}
        target = candidates[-1]
        rev = self.revisions[target]
        clone = self.propose(rev.config, source_commit=rev.source_commit, author=actor, approver=rev.approver,
                             change_ref=f"rollback-of-{self.active}", environment=rev.environment) \
            if rev.environment != "production" or rev.approver != actor else None
        if clone is None:
            raise FabricError("PERMISSION_DENIED", "rollback actor may not self-approve production revision")
        res = self.activate(clone.generation)
        res["rolled_back_from"] = target
        return res

    def status(self) -> dict:
        rev = self.revisions.get(self.active)
        return {"schema": CONFIG_SCHEMA_VERSION, "active_generation": self.active,
                "digest": rev.digest if rev else None,
                "targets": {n: t.active_generation for n, t in sorted(self.targets.items())},
                "drift": sorted(n for n, t in self.targets.items() if t.active_generation != self.active)}

    def _audit(self, kind, actor, data):
        if self.ledger is not None:
            self.ledger.append(kind, actor, {"summary": json.dumps(data, sort_keys=True, default=str)[:900]})


# -- secrets (M32) ----------------------------------------------------
class SecretValue:
    """Holds secret bytes; never renders in repr/str/json; explicit wipe()."""
    __slots__ = ("_b",)

    def __init__(self, b: bytes):
        self._b = bytearray(b)

    def reveal(self) -> bytes:
        return bytes(self._b)

    def wipe(self) -> None:
        for i in range(len(self._b)):
            self._b[i] = 0
        self._b = bytearray()

    def __repr__(self) -> str:
        return "SecretValue([REDACTED])"
    __str__ = __repr__


class SecretResolver:
    """Narrow interface to secret backends with per-scope ACL, TTL cache and fail-closed refresh."""

    def __init__(self, backends: dict, acl: dict, ttl_s: float = 60.0, clock=time.monotonic):
        self.backends, self.acl, self.ttl_s, self.clock = backends, acl, ttl_s, clock
        self._cache: dict[tuple, tuple[SecretValue, float]] = {}

    def resolve(self, ref: str, *, principal) -> SecretValue:
        if not SECRET_REF.match(ref):
            raise FabricError("INVALID_ARGUMENT", "malformed secret reference")
        allowed = self.acl.get(ref, set())
        if principal.id not in allowed:
            raise FabricError("PERMISSION_DENIED", "principal not in secret ACL")
        key = (ref, principal.id)
        hit = self._cache.get(key)
        if hit and self.clock() - hit[1] < self.ttl_s:
            return hit[0]
        backend = ref.split("/")[2]
        fetch = self.backends.get(backend)
        if fetch is None:
            raise FabricError("BACKEND_NOT_CONFIGURED", f"secret backend {backend} not configured")
        try:
            val = SecretValue(fetch(ref))
        except FabricError:
            raise
        except Exception:
            if hit:
                hit[0].wipe()
            self._cache.pop(key, None)
            raise FabricError("UNAVAILABLE", "secret backend refresh failed; no stale fallback") from None
        if hit:
            hit[0].wipe()
        self._cache[key] = (val, self.clock())
        return val

    def rotate(self, ref: str) -> None:
        for k in [k for k in self._cache if k[0] == ref]:
            self._cache.pop(k)[0].wipe()


SECRET_SCAN = [re.compile(p) for p in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"(?i)aws_secret_access_key\s*=", r"AKIA[0-9A-Z]{16}",
    r"(?i)\b(password|passwd|secret)\s*[:=]\s*['\"][^'\"]{6,}['\"]", r"xox[baprs]-[0-9A-Za-z-]{10,}",
    r"ghp_[0-9A-Za-z]{36}", r"SUAC[A-Z0-9]{52}")]


def scan_text_for_secrets(text: str) -> list[str]:
    return [p.pattern for p in SECRET_SCAN if p.search(text)]
