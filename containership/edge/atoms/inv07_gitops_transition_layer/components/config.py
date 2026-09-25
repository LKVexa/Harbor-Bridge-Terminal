"""Typed, versioned configuration (component 29; adapted from the shop's
GAP-09 v5.1.0 ``config.py``).

``PK_GITOPS_CONFIG/1`` documents are validated offline (``python -m ...cli
config-validate FILE``) and in-process before activation:

* unknown keys, wrong types, out-of-range values and dangerous settings are
  refused (``ConfigRejected``) -- never coerced;
* precedence is explicit: ``defaults <- file <- environment <- site`` via
  ``merge`` and the *merged* document is what is validated and digested;
* secure defaults: signatures required, fast-forward only, fail-closed offline
  mode, TLS verification on, metrics authenticated;
* secrets are never inline -- only references ``env:NAME`` or ``file:/path``
  (resolved by ``keys.SecretResolver``);
* ``IMMUTABLE`` settings (repository identity, trust roots, tenant, site) can
  change only through a restart with a new document; a hot reload that touches
  them is rejected and the last-known-good version stays active;
* every activation records version, digest, author, reason and time, and is
  written to the audit ledger when one is attached.
"""
from __future__ import annotations

import copy
import hashlib
import re
import threading
from typing import Any

from .canonical import canonicalize
from .errors import ConfigRejected

SCHEMA_ID = "PK_GITOPS_CONFIG/1"
_SECRET_REF = re.compile(r"^(env:[A-Z_][A-Z0-9_]{0,63}|file:/[^\s]{1,1024})$")
_REF_PAT = re.compile(r"^refs/(heads|tags)/[A-Za-z0-9._/*-]{1,200}$")

# section -> key -> (type, lo, hi) ; lo/hi None when not numeric
SCHEMA: dict[str, dict[str, tuple]] = {
    "repository": {"url": (str, None, None), "root_commit": (str, None, None), "approved_refs": (list, 1, 64),
                   "fetch_depth": (int, 0, 100_000), "timeout_seconds": (int, 1, 3600),
                   "credential_ref": (str, None, None), "allowed_hosts": (list, 0, 64)},
    "trust": {"trust_roots_file": (str, None, None), "require_signed": (bool, None, None),
              "require_provenance": (bool, None, None), "max_commit_age_seconds": (int, 60, 400 * 86_400),
              "algorithms": (list, 1, 4)},
    "controller": {"sync_interval_seconds": (int, 5, 86_400), "lease_ttl_seconds": (int, 5, 3600),
                   "max_resources": (int, 1, 100_000), "prune": (bool, None, None),
                   "state_dir": (str, None, None), "offline_mode": (str, None, None),
                   "max_cached_ref_age_seconds": (int, 60, 30 * 86_400)},
    "tenancy": {"tenant": (str, None, None), "site": (str, None, None), "region": (str, None, None),
                "allowed_namespaces": (list, 1, 1024), "allowed_regions": (list, 1, 64)},
    "limits": {"max_manifest_bytes": (int, 1024, 64 << 20), "max_depth": (int, 4, 128),
               "max_queue": (int, 1, 1_000_000), "retry_max_attempts": (int, 1, 20),
               "retry_base_seconds": (float, 0.01, 60.0), "retry_cap_seconds": (float, 0.1, 3600.0),
               "breaker_threshold": (int, 1, 1000), "breaker_cooldown_seconds": (float, 0.1, 3600.0)},
    "telemetry": {"log_level": (str, None, None), "metrics_require_auth": (bool, None, None),
                  "trace_sample_ratio": (float, 0.0, 1.0), "retention_days": (int, 1, 400)},
    "network": {"tls_min_version": (str, None, None), "verify_tls": (bool, None, None),
                "egress_allowlist": (list, 0, 256), "proxy": (str, None, None)},
}
OPTIONAL = {("repository", "credential_ref"), ("repository", "allowed_hosts"), ("network", "proxy"),
            ("repository", "root_commit")}
IMMUTABLE = {("repository", "url"), ("repository", "root_commit"), ("trust", "trust_roots_file"),
             ("tenancy", "tenant"), ("tenancy", "site"), ("tenancy", "region"), ("controller", "state_dir")}
DANGEROUS = {("trust", "require_signed"): False, ("network", "verify_tls"): False,
             ("telemetry", "metrics_require_auth"): False}
ENUMS = {("controller", "offline_mode"): {"fail_closed", "read_only", "cache_backed"},
         ("telemetry", "log_level"): {"error", "warning", "info", "debug"},
         ("network", "tls_min_version"): {"TLSv1.2", "TLSv1.3"},
         ("trust", "algorithms"): {"ed25519", "openpgp"}}

DEFAULTS: dict = {
    "schema": SCHEMA_ID,
    "repository": {"url": "", "approved_refs": ["refs/heads/main"], "fetch_depth": 0, "timeout_seconds": 120,
                   "allowed_hosts": []},
    "trust": {"trust_roots_file": "trust_roots.json", "require_signed": True, "require_provenance": True,
              "max_commit_age_seconds": 30 * 86_400, "algorithms": ["ed25519"]},
    "controller": {"sync_interval_seconds": 60, "lease_ttl_seconds": 30, "max_resources": 5000, "prune": False,
                   "state_dir": "state", "offline_mode": "fail_closed", "max_cached_ref_age_seconds": 3600},
    "tenancy": {"tenant": "", "site": "", "region": "", "allowed_namespaces": ["default"],
                "allowed_regions": ["local"]},
    "limits": {"max_manifest_bytes": 1 << 20, "max_depth": 32, "max_queue": 1000, "retry_max_attempts": 5,
               "retry_base_seconds": 0.2, "retry_cap_seconds": 30.0, "breaker_threshold": 5,
               "breaker_cooldown_seconds": 30.0},
    "telemetry": {"log_level": "info", "metrics_require_auth": True, "trace_sample_ratio": 1.0, "retention_days": 30},
    "network": {"tls_min_version": "TLSv1.2", "verify_tls": True, "egress_allowlist": []},
}


def merge(*layers: dict) -> dict:
    """Section-wise precedence: later layers override earlier ones key by key."""
    out: dict = copy.deepcopy(layers[0]) if layers else {}
    for layer in layers[1:]:
        for sec, body in layer.items():
            if isinstance(body, dict) and isinstance(out.get(sec), dict):
                out[sec].update(copy.deepcopy(body))
            else:
                out[sec] = copy.deepcopy(body)
    return out


def from_env(environ: dict, prefix: str = "INV07_") -> dict:
    """``INV07_<SECTION>__<KEY>=value`` -> layer.  Types are parsed strictly."""
    layer: dict = {}
    for k, v in environ.items():
        if not k.startswith(prefix) or "__" not in k:
            continue
        sec, key = k[len(prefix):].lower().split("__", 1)
        if sec not in SCHEMA or key not in SCHEMA[sec]:
            raise ConfigRejected("unknown environment config key", key=k)
        typ = SCHEMA[sec][key][0]
        try:
            if typ is bool:
                if v not in ("true", "false"):
                    raise ValueError
                val: Any = v == "true"
            elif typ is list:
                val = [x for x in v.split(",") if x]
            else:
                val = typ(v)
        except ValueError:
            raise ConfigRejected("environment value has wrong type", key=k) from None
        layer.setdefault(sec, {})[key] = val
    return layer


def validate(doc: dict) -> dict:
    if not isinstance(doc, dict):
        raise ConfigRejected("config must be an object")
    if doc.get("schema") != SCHEMA_ID:
        raise ConfigRejected("unsupported config schema", expected=SCHEMA_ID, got=str(doc.get("schema")))
    unknown = set(doc) - set(SCHEMA) - {"schema"}
    if unknown:
        raise ConfigRejected("unknown config sections", sections=sorted(unknown))
    for sec, keys in SCHEMA.items():
        body = doc.get(sec)
        if not isinstance(body, dict):
            raise ConfigRejected("missing config section", section=sec)
        extra = set(body) - set(keys)
        if extra:
            raise ConfigRejected("unknown config keys", section=sec, keys=sorted(extra))
        for key, (typ, lo, hi) in keys.items():
            if key not in body:
                if (sec, key) in OPTIONAL:
                    continue
                raise ConfigRejected("missing config key", section=sec, key=key)
            v = body[key]
            if typ is float and isinstance(v, int) and not isinstance(v, bool):
                v = float(v)
            if (typ is not bool and isinstance(v, bool)) or not isinstance(v, typ):
                raise ConfigRejected("wrong type", section=sec, key=key)
            if typ is list:
                if not (lo <= len(v) <= hi) or not all(isinstance(x, str) and x for x in v):
                    raise ConfigRejected("list size or item type out of bounds", section=sec, key=key)
            elif lo is not None and not (lo <= v <= hi):
                raise ConfigRejected("out of range", section=sec, key=key)
            if (sec, key) in DANGEROUS and v == DANGEROUS[(sec, key)]:
                raise ConfigRejected("dangerous setting refused", section=sec, key=key)
            allowed = ENUMS.get((sec, key))
            if allowed is not None:
                vals = v if isinstance(v, list) else [v]
                if any(x not in allowed for x in vals):
                    raise ConfigRejected("value not in allowed set", section=sec, key=key)
    repo = doc["repository"]
    if not repo["url"]:
        raise ConfigRejected("repository.url is required")
    if any(not _REF_PAT.match(r) for r in repo["approved_refs"]):
        raise ConfigRejected("approved_refs must be full refs/heads/* or refs/tags/*")
    cred = repo.get("credential_ref")
    if cred is not None and not _SECRET_REF.match(cred):
        raise ConfigRejected("credential_ref must be env:NAME or file:/path (no inline secrets)")
    if "@" in repo["url"].split("://", 1)[-1].split("/", 1)[0] and repo["url"].startswith(("http", "https")):
        raise ConfigRejected("credentials must not be embedded in repository.url")
    rc = repo.get("root_commit")
    if rc is not None and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", rc):
        raise ConfigRejected("root_commit must be a full commit OID")
    ten = doc["tenancy"]
    for k in ("tenant", "site", "region"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", ten[k] or ""):
            raise ConfigRejected("tenancy identifiers must be DNS-label-like", key=k)
    if ten["region"] not in ten["allowed_regions"]:
        raise ConfigRejected("configured region is outside allowed_regions")
    lim = doc["limits"]
    if lim["retry_cap_seconds"] < lim["retry_base_seconds"]:
        raise ConfigRejected("retry cap must be >= base")
    return doc


def digest(doc: dict) -> str:
    return hashlib.sha256(canonicalize(doc).encode()).hexdigest()


class ConfigManager:
    """Atomic activation, last-known-good preservation and audited rollback."""

    def __init__(self, initial: dict, *, author: str, audit=None, keep: int = 10, at: int = 0,
                 source: str = "initial") -> None:
        self._lock = threading.Lock()
        self._audit = audit
        self._keep = keep
        self._history: list[dict] = []
        self._activate(initial, author=author, at=at, reason="initial", source=source)

    def _activate(self, doc: dict, *, author: str, at: int, reason: str, source: str) -> dict:
        validate(doc)
        rec = {"version": (self._history[-1]["version"] + 1) if self._history else 1, "digest": digest(doc),
               "author": author, "activated_at": at, "reason": reason, "source": source,
               "config": copy.deepcopy(doc)}
        self._history.append(rec)
        del self._history[:-self._keep]
        if self._audit:
            self._audit.append("config.activate", {"version": rec["version"], "digest": rec["digest"],
                                                   "reason": reason, "source": source}, actor=author)
        return rec

    def reload(self, doc: dict, *, author: str, at: int, reason: str, source: str = "reload") -> dict:
        with self._lock:
            cur = self._history[-1]["config"]
            for sec, key in IMMUTABLE:
                if cur.get(sec, {}).get(key) != doc.get(sec, {}).get(key):
                    raise ConfigRejected("immutable setting changed by hot reload; restart required",
                                         section=sec, key=key)
            return self._activate(doc, author=author, at=at, reason=reason, source=source)

    def rollback(self, *, author: str, at: int) -> dict:
        with self._lock:
            if len(self._history) < 2:
                raise ConfigRejected("no previous version to roll back to")
            prev = self._history[-2]
            return self._activate(prev["config"], author=author, at=at,
                                  reason=f"rollback-to-v{prev['version']}", source="rollback")

    @property
    def active(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._history[-1])
