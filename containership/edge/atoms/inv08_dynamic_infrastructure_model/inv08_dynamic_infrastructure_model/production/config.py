"""Components 30 & 31 - declarative configuration schema and atomic
deployment/rollback.

Schema ``PK_DYN_CONFIG/1`` (unknown keys are rejected at every level)::

  schema: "PK_DYN_CONFIG/1"
  env: "dev" | "staging" | "prod"
  site: str [a-z0-9-]{1,40}
  tenant: str [a-z0-9-]{1,40} | null
  pool: {min_nodes:int>=0, max_nodes:int>=min, per_node:int>=1, lease_ttl:int>=1}
  providers: [{name:str unique, kind: cloud|hypervisor|baremetal|edge,
               credentials: "secretref://..."}]   (>=1)
  controller: {reconcile_interval_s>0, op_timeout_s>reconcile_interval_s,
               max_retries:int 1..10, leader_ttl_s>reconcile_interval_s}
  security: {allow_insecure_transport:bool, require_fencing:bool,
             audit_enabled:bool, break_glass_max_ttl_s: 1..3600}

Secure defaults (``SECURE_DEFAULTS``) are fail-closed: insecure transport
off, fencing on, audit on, conservative pool bounds.  ``prod`` additionally
forbids turning any of them off.  Credentials may only be secret references.

Every accepted config is wrapped with provenance {author, source, created_ts,
digest}; author and source are mandatory (who changed what is always known).

Deployment (31): stage -> validate (schema + semantic + caller preflight
checks) -> activate (atomic ``os.replace`` of ``active.json``; previous active
becomes ``lkg.json``) -> post-activation verify; on verify failure the
previous config is restored and the candidate is moved to ``quarantine/``.
Activation is scoped per (env, tenant): a config can only be activated into
the scope it declares.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
from pathlib import Path
from typing import Callable

from .core import Inv08Error, Outcome, digest
from .leasestore import _atomic_write
from .secrets import SecretRef

SCHEMA = "PK_DYN_CONFIG/1"
ENVS = ("dev", "staging", "prod")
KINDS = ("cloud", "hypervisor", "baremetal", "edge")
_NAME = re.compile(r"^[a-z0-9-]{1,40}$")

SECURE_DEFAULTS = {
    "schema": SCHEMA,
    "tenant": None,
    "pool": {"min_nodes": 0, "max_nodes": 4, "per_node": 4, "lease_ttl": 10},
    "controller": {"reconcile_interval_s": 10.0, "op_timeout_s": 300.0, "max_retries": 4,
                   "leader_ttl_s": 15.0},
    "security": {"allow_insecure_transport": False, "require_fencing": True, "audit_enabled": True,
                 "break_glass_max_ttl_s": 900},
}
_REQUIRED_TOP = {"env", "site", "providers"}
_TOP = {"schema", "env", "site", "tenant", "pool", "providers", "controller", "security"}


def _invalid(problems: list[str]) -> Inv08Error:
    return Inv08Error("INV08.CONFIG.INVALID", "; ".join(problems[:5]), outcome=Outcome.TERMINAL_FAILURE,
                      remediation="fix the configuration; nothing was activated",
                      details={"problems": problems})


def _merge(defaults: dict, raw: dict) -> dict:
    out = copy.deepcopy(defaults)
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))


def validate(raw: dict) -> dict:
    """Return the fully-defaulted config or raise INV08.CONFIG.INVALID."""
    if not isinstance(raw, dict):
        raise _invalid(["config must be an object"])
    p: list[str] = []
    for k in sorted(set(raw) - _TOP):
        p.append(f"unknown key {k}")
    for k in sorted(_REQUIRED_TOP - set(raw)):
        p.append(f"missing {k}")
    for sec in ("pool", "controller", "security"):
        if sec in raw:
            if not isinstance(raw[sec], dict):
                p.append(f"{sec} must be an object")
            else:
                for k in sorted(set(raw[sec]) - set(SECURE_DEFAULTS[sec])):
                    p.append(f"unknown key {sec}.{k}")
    if p:
        raise _invalid(p)
    c = _merge(SECURE_DEFAULTS, raw)
    if c["schema"] != SCHEMA:
        p.append(f"schema must be {SCHEMA}")
    if c["env"] not in ENVS:
        p.append(f"env must be one of {ENVS}")
    if not isinstance(c["site"], str) or not _NAME.match(c["site"]):
        p.append("site must match [a-z0-9-]{1,40}")
    if c["tenant"] is not None and (not isinstance(c["tenant"], str) or not _NAME.match(c["tenant"])):
        p.append("tenant must be null or match [a-z0-9-]{1,40}")
    pool = c["pool"]
    for k, lo in (("min_nodes", 0), ("max_nodes", 0), ("per_node", 1), ("lease_ttl", 1)):
        if not _is_int(pool[k]) or pool[k] < lo:
            p.append(f"pool.{k} must be int >= {lo}")
    if not p and pool["min_nodes"] > pool["max_nodes"]:
        p.append("pool.min_nodes > pool.max_nodes")
    provs = c["providers"]
    if not isinstance(provs, list) or not provs:
        p.append("providers must be a non-empty list")
    else:
        names = set()
        for i, pr in enumerate(provs):
            if not isinstance(pr, dict) or set(pr) != {"name", "kind", "credentials"}:
                p.append(f"providers[{i}] needs exactly name, kind, credentials")
                continue
            if not isinstance(pr["name"], str) or not _NAME.match(pr["name"]) or pr["name"] in names:
                p.append(f"providers[{i}].name invalid or duplicate")
            names.add(pr["name"])
            if pr["kind"] not in KINDS:
                p.append(f"providers[{i}].kind must be one of {KINDS}")
            try:
                SecretRef.parse(pr["credentials"])
            except (ValueError, TypeError):
                p.append(f"providers[{i}].credentials must be a secretref:// reference, not a literal")
    ctl = c["controller"]
    for k in ("reconcile_interval_s", "op_timeout_s", "leader_ttl_s"):
        if not _is_num(ctl[k]) or ctl[k] <= 0:
            p.append(f"controller.{k} must be a finite number > 0")
    if not _is_int(ctl["max_retries"]) or not 1 <= ctl["max_retries"] <= 10:
        p.append("controller.max_retries must be int in [1, 10]")
    if not p:
        if ctl["op_timeout_s"] <= ctl["reconcile_interval_s"]:
            p.append("controller.op_timeout_s must exceed reconcile_interval_s")
        if ctl["leader_ttl_s"] <= ctl["reconcile_interval_s"]:
            p.append("controller.leader_ttl_s must exceed reconcile_interval_s (else leadership flaps)")
    sec = c["security"]
    for k in ("allow_insecure_transport", "require_fencing", "audit_enabled"):
        if not isinstance(sec[k], bool):
            p.append(f"security.{k} must be bool")
    if not _is_int(sec["break_glass_max_ttl_s"]) or not 1 <= sec["break_glass_max_ttl_s"] <= 3600:
        p.append("security.break_glass_max_ttl_s must be int in [1, 3600]")
    if c["env"] == "prod" and not p:
        if sec["allow_insecure_transport"] or not sec["require_fencing"] or not sec["audit_enabled"]:
            p.append("prod forbids weakening security defaults")
    if p:
        raise _invalid(p)
    return c


def with_provenance(raw: dict, *, author: str, source: str, created_ts: float) -> dict:
    if not isinstance(author, str) or not author.strip():
        raise _invalid(["provenance.author is required"])
    if not isinstance(source, str) or not source.strip():
        raise _invalid(["provenance.source is required"])
    cfg = validate(raw)
    return {"config": cfg, "provenance": {"author": author, "source": source,
                                          "created_ts": created_ts, "digest": digest(cfg)}}


def verify_envelope(env: dict) -> dict:
    cfg = validate(env["config"])
    if env["provenance"]["digest"] != digest(cfg):
        raise Inv08Error("INV08.CONFIG.TAMPERED", "config digest mismatch", outcome=Outcome.OPERATOR_REQUIRED)
    return cfg


class ConfigDeployer:
    """File-backed staged/atomic config activation for one (env, tenant) scope."""

    def __init__(self, directory: str | os.PathLike, *, env: str, tenant: str | None = None,
                 audit=None, clock: Callable[[], float] = lambda: 0.0) -> None:
        if env not in ENVS:
            raise ValueError(env)
        self.dir = Path(directory) / f"{env}__{tenant or '_'}"
        for sub in ("staged", "quarantine"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        self.env, self.tenant, self.audit, self.clock = env, tenant, audit, clock
        self._validated: set[str] = set()

    def _log(self, action: str, res: str, outcome: str, **d) -> None:
        if self.audit is not None:
            self.audit.append("config-deployer", action, res, outcome, d, ts=self.clock())

    def _write(self, path: Path, envelope: dict) -> None:
        _atomic_write(path, json.dumps(envelope, sort_keys=True).encode())

    def _read(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        env = json.loads(path.read_bytes())
        verify_envelope(env)
        return env

    def stage(self, envelope: dict) -> str:
        cfg = verify_envelope(envelope)
        if cfg["env"] != self.env or cfg["tenant"] != self.tenant:
            raise Inv08Error("INV08.CONFIG.SCOPE", f"config scope ({cfg['env']},{cfg['tenant']}) does not "
                             f"match deployer ({self.env},{self.tenant})", outcome=Outcome.TERMINAL_FAILURE)
        sid = envelope["provenance"]["digest"].split(":")[1][:16]
        self._write(self.dir / "staged" / f"{sid}.json", envelope)
        self._log("config.stage", sid, "SUCCESS", author=envelope["provenance"]["author"])
        return sid

    def validate_staged(self, sid: str, preflight: list[Callable[[dict], str | None]] = ()) -> list[str]:
        env = self._read(self.dir / "staged" / f"{sid}.json")
        if env is None:
            raise KeyError(sid)
        problems = [msg for check in preflight if (msg := check(env["config"]))]
        if problems:
            self._validated.discard(sid)
            self._log("config.validate", sid, "FAILED", problems=problems)
        else:
            self._validated.add(sid)
            self._log("config.validate", sid, "SUCCESS")
        return problems

    def active(self) -> dict | None:
        return self._read(self.dir / "active.json")

    def activate(self, sid: str, verify: Callable[[dict], bool] = lambda c: True) -> dict:
        if sid not in self._validated:
            raise Inv08Error("INV08.CONFIG.NOT_VALIDATED", f"{sid} has not passed pre-activation validation",
                             outcome=Outcome.TERMINAL_FAILURE)
        staged = self.dir / "staged" / f"{sid}.json"
        env = self._read(staged)
        prev = self.active()
        if prev is not None:
            self._write(self.dir / "lkg.json", prev)
        self._write(self.dir / "active.json", env)            # atomic boundary
        ok = False
        try:
            ok = bool(verify(env["config"]))
        except Exception:  # noqa: BLE001 - any verify crash counts as failure
            ok = False
        if ok:
            staged.unlink()
            self._validated.discard(sid)
            self._log("config.activate", sid, "SUCCESS")
            return env
        self._restore(prev)
        os.replace(staged, self.dir / "quarantine" / f"{sid}.json")
        self._validated.discard(sid)
        self._log("config.activate", sid, "ROLLED_BACK")
        raise Inv08Error("INV08.CONFIG.ACTIVATION_FAILED", f"{sid} failed post-activation verification",
                         outcome=Outcome.OPERATOR_REQUIRED, remediation="candidate quarantined; previous restored",
                         details={"sid": sid})

    def _restore(self, prev: dict | None) -> None:
        if prev is None:
            (self.dir / "active.json").unlink(missing_ok=True)
        else:
            self._write(self.dir / "active.json", prev)

    def rollback(self) -> dict:
        lkg = self._read(self.dir / "lkg.json")
        if lkg is None:
            raise Inv08Error("INV08.CONFIG.NO_LKG", "no last-known-good config", outcome=Outcome.OPERATOR_REQUIRED)
        self._write(self.dir / "active.json", lkg)
        if self.active()["provenance"]["digest"] != lkg["provenance"]["digest"]:
            raise Inv08Error("INV08.CONFIG.ROLLBACK_VERIFY", "rollback verification failed",
                             outcome=Outcome.OPERATOR_REQUIRED)
        self._log("config.rollback", lkg["provenance"]["digest"], "SUCCESS")
        return lkg
