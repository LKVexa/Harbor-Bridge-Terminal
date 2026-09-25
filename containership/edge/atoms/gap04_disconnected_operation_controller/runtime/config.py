"""Declarative configuration, atomic activation/rollback (GAP04-C21, C22, C23).

A configuration is a PK_GAP04_CONFIG/1 document (JSON; canonical-encodable).
``validate_config`` is strict: unknown keys, wrong types, out-of-range values,
and unsafe combinations are rejected with GAP04-E0800 and a list of problems.
``ConfigManager`` activates a validated document atomically, records
provenance (author, approver, reason, activation time, digest, optional
signature), retains every previous version, and supports rollback to the
immediately previous or a named version.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from . import canonical, crypto
from ..controller import PERMITTED, validate_tier_schedule
from .errors import ConfigInvalid, Gap04Error
from .storage import atomic_write
from .trust import TrustStore

CONFIG_VERSION = "PK_GAP04_CONFIG/1"

DEFAULTS: dict[str, Any] = {
    "version": CONFIG_VERSION,
    "config_version": 1,
    "scope": {"site": "site-a", "tenant": "t0", "cluster": "c0", "node_class": "edge", "environment": "prod"},
    "lease": {"max_lifetime_s": 86400, "renew_before_s": 3600},
    "tier_schedule": [[0, "full"], [1800, "sustain"], [7200, "freeze"]],
    "max_policy_staleness_s": 86400,
    "max_decisions_per_partition": 10000,
    "journal": {"max_bytes": 64 * 1024 * 1024, "reserve_bytes": 1024 * 1024, "min_disk_free_bytes": 16 * 1024 * 1024},
    "clock": {"max_drift_s": 30, "tolerance_s": 2, "persist_interval_s": 10, "allow_rtc_after_reboot": False},
    "reachability": {"up_after": 3, "down_after": 2, "flap_window_s": 300, "flap_threshold": 6},
    "admission": {"max_concurrency": 16, "max_queue": 256, "retry_budget_percent": 10},
    "overrides": {"two_person_required": True, "max_ttl_s": 86400},
    "reconcile": {"batch_size": 200, "max_attempts": 5},
    "quotas": {"decisions_per_minute": 600},
}

_SCHEMA: dict[str, Any] = {
    "version": str, "config_version": int, "scope": dict, "lease": dict, "tier_schedule": list,
    "max_policy_staleness_s": int, "max_decisions_per_partition": int, "journal": dict, "clock": dict,
    "reachability": dict, "admission": dict, "overrides": dict, "reconcile": dict, "quotas": dict,
}


def validate_config(doc: Any) -> dict:
    problems: list[str] = []
    if not isinstance(doc, dict):
        raise ConfigInvalid("config must be an object")
    try:
        canonical.dumps(doc)
    except canonical.CanonicalError as e:
        problems.append(f"non-canonical: {e}")
    for k in doc:
        if k not in _SCHEMA:
            problems.append(f"unknown key {k}")
    for k, t in _SCHEMA.items():
        if k not in doc:
            problems.append(f"missing key {k}")
        elif not isinstance(doc[k], t) or (t is int and isinstance(doc[k], bool)):
            problems.append(f"{k} must be {t.__name__}")
    if problems:
        raise ConfigInvalid("configuration invalid", details={"problems": problems})
    if doc["version"] != CONFIG_VERSION:
        problems.append("unsupported config version")
    for sect, ref in DEFAULTS.items():
        if isinstance(ref, dict):
            if set(doc[sect]) != set(ref):
                problems.append(f"{sect} keys must be exactly {sorted(ref)}")
            for kk, vv in doc[sect].items():
                if kk in ref and type(vv) is not type(ref[kk]) and not (isinstance(ref[kk], float) and isinstance(vv, int)):
                    problems.append(f"{sect}.{kk} has wrong type")
    try:
        validate_tier_schedule(doc["tier_schedule"])
    except ValueError as e:
        problems.append(f"tier_schedule: {e}")
    def pos(path, v, lo=1, hi=None):
        if not isinstance(v, int) or isinstance(v, bool) or v < lo or (hi is not None and v > hi):
            problems.append(f"{path} out of range [{lo},{hi}]")
    if not problems:
        pos("config_version", doc["config_version"])
        pos("lease.max_lifetime_s", doc["lease"]["max_lifetime_s"], 60, 7 * 86400)
        pos("max_policy_staleness_s", doc["max_policy_staleness_s"], 60, 30 * 86400)
        pos("max_decisions_per_partition", doc["max_decisions_per_partition"], 1, 10_000_000)
        j = doc["journal"]
        pos("journal.max_bytes", j["max_bytes"], 64 * 1024)
        if j["reserve_bytes"] >= j["max_bytes"] // 2 or j["reserve_bytes"] < 4096:
            problems.append("journal.reserve_bytes must be >=4096 and < half of max_bytes")
        pos("clock.max_drift_s", doc["clock"]["max_drift_s"], 1, 3600)
        pos("admission.max_concurrency", doc["admission"]["max_concurrency"], 1, 4096)
        pos("admission.max_queue", doc["admission"]["max_queue"], 0, 1_000_000)
        pos("overrides.max_ttl_s", doc["overrides"]["max_ttl_s"], 60, 7 * 86400)
        if doc["tier_schedule"][-1][0] >= doc["lease"]["max_lifetime_s"]:
            problems.append("last tier threshold must be below lease.max_lifetime_s (else freeze is unreachable)")
        if doc["scope"].keys() != DEFAULTS["scope"].keys() or not all(isinstance(v, str) and v for v in doc["scope"].values()):
            problems.append("scope must name site/tenant/cluster/node_class/environment")
        if doc["scope"]["environment"] == "prod" and not doc["overrides"]["two_person_required"]:
            problems.append("prod environment requires two-person override control")
    if problems:
        raise ConfigInvalid("configuration invalid", details={"problems": problems})
    return doc


def default_config(**scope) -> dict:
    d = copy.deepcopy(DEFAULTS)
    d["scope"].update(scope)
    return d


class ConfigManager:
    """Atomic activation with retained history. Layout: <dir>/active.json, <dir>/history/<v>.json"""

    def __init__(self, directory: Path, trust: TrustStore | None = None, require_signature: bool = False):
        self.dir = Path(directory)
        (self.dir / "history").mkdir(parents=True, exist_ok=True)
        self.trust = trust
        self.require_signature = require_signature

    def active(self) -> dict | None:
        p = self.dir / "active.json"
        return json.loads(p.read_text()) if p.exists() else None

    def history(self) -> list[int]:
        return sorted(int(p.stem) for p in (self.dir / "history").glob("*.json"))

    def activate(self, doc: dict, *, author: str, approver: str, reason: str, now: int,
                 signature: dict | None = None) -> dict:
        validate_config(doc)
        if not author or not approver or author == approver:
            raise Gap04Error("activation requires distinct author and approver", code="GAP04-E0802")
        if not reason.strip():
            raise ConfigInvalid("activation reason required")
        cur = self.active()
        if cur is not None and doc["config_version"] <= cur["config"]["config_version"]:
            raise Gap04Error("config_version must increase (use rollback for older versions)", code="GAP04-E0801")
        digest = canonical.digest(doc)
        if self.require_signature:
            self._verify_sig(doc, signature, now)
        rec = {"config": doc, "provenance": {"author": author, "approver": approver, "reason": reason,
                                             "activated_at": now, "digest": digest,
                                             "signed_by": signature.get("key_id") if signature else None,
                                             "previous": cur["config"]["config_version"] if cur else None}}
        atomic_write(self.dir / "history" / f"{doc['config_version']}.json", json.dumps(rec, sort_keys=True).encode())
        atomic_write(self.dir / "active.json", json.dumps(rec, sort_keys=True).encode())
        return rec

    def _verify_sig(self, doc: dict, sig: dict | None, now: int) -> None:
        if not sig or self.trust is None:
            raise Gap04Error("signed configuration required", code="GAP04-E0800")
        key = self.trust.resolve(sig["key_id"], sig["issuer"], sig["alg"], "config", now)
        if not crypto.verify(key.public_key, canonical.dumps(doc), sig["sig"]):
            raise Gap04Error("configuration signature invalid", code="GAP04-E0800")

    def rollback(self, *, to_version: int | None = None, author: str, approver: str, reason: str, now: int) -> dict:
        cur = self.active()
        if cur is None:
            raise Gap04Error("no active configuration", code="GAP04-E0801")
        target = to_version if to_version is not None else cur["provenance"]["previous"]
        p = self.dir / "history" / f"{target}.json"
        if target is None or not p.exists():
            raise Gap04Error("rollback target unavailable", code="GAP04-E0801", details={"target": target})
        old = json.loads(p.read_text())
        validate_config(old["config"])
        if author == approver:
            raise Gap04Error("rollback requires distinct author and approver", code="GAP04-E0802")
        rec = {"config": old["config"], "provenance": {"author": author, "approver": approver, "reason": reason,
                                                       "activated_at": now, "digest": canonical.digest(old["config"]),
                                                       "rollback_from": cur["config"]["config_version"],
                                                       "previous": cur["config"]["config_version"]}}
        atomic_write(self.dir / "active.json", json.dumps(rec, sort_keys=True).encode())
        return rec


if __name__ == "__main__":  # config linter / dry-run (C21-017)
    import sys
    try:
        doc = validate_config(json.loads(Path(sys.argv[1]).read_text()))
        print(json.dumps({"valid": True, "config_version": doc["config_version"], "digest": canonical.digest(doc)}))
    except Gap04Error as e:
        print(json.dumps(e.to_dict(), indent=2)); sys.exit(2)
