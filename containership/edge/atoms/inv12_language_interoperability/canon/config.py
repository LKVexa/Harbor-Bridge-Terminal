"""MC-043 declarative config schema, MC-044 validator/transaction manager,
MC-045 mapping-policy provenance.

Configuration document ``PK_INTEROP_CONFIG/1`` (all keys required, no extras)::

    {"schema": "PK_INTEROP_CONFIG/1",
     "revision": 1,                                  # strictly increasing
     "languages": ["go", "javascript", "python", "rust"],
     "mapping_profile": {"id": "inv12-mapping", "version": "2.0.0", "digest": "sha256:..."},
     "limits": {<canon.limits.Limits fields, may only tighten the hard ceiling>},
     "features": {"async": false, "zero_copy": false, "lazy_lift": false},
     "runtime": {"canonical_abi": "1", "string_encoding": "utf8"},
     "environment": "prod", "site": "any"}

Secure defaults (:func:`default_config`): every optional feature off, limits at
the hard ceiling, only the four certified languages, and the mapping-profile
digest pinned to the shipped registry.

:class:`ConfigManager` activates a new document only after full validation *and*
a provenance check (quorum of distinct approvers whose HMAC approvals cover the
document digest).  Activation swaps one immutable :class:`Snapshot` reference
under a lock, so every operation that reads ``manager.current`` once sees one
consistent revision.  ``rollback()`` restores the previous snapshot
deterministically; history and approvals are retained for audit.

Limitation: approvals are HMAC-SHA256 (stdlib only).  Asymmetric signatures
(Sigstore / Ed25519 with a transparency log) are the production target; see
``docs/ADR-0001.md``.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from types import MappingProxyType

from .errors import ConfigError, InteropError, ProvenanceError
from .limits import HARD_CEILING, Limits
from .registry import PROFILE_DIGEST, PROFILE_ID, PROFILE_VERSION, SUPPORTED_LANGUAGES

SCHEMA = "PK_INTEROP_CONFIG/1"
FEATURES = ("async", "zero_copy", "lazy_lift")
ENVIRONMENTS = ("dev", "test", "staging", "prod")


def default_config() -> dict:
    return {
        "schema": SCHEMA, "revision": 1,
        "languages": sorted(SUPPORTED_LANGUAGES),
        "mapping_profile": {"id": PROFILE_ID, "version": PROFILE_VERSION, "digest": PROFILE_DIGEST},
        "limits": HARD_CEILING.as_dict(),
        "features": {f: False for f in FEATURES},
        "runtime": {"canonical_abi": "1", "string_encoding": "utf8"},
        "environment": "prod", "site": "any",
    }


def digest(doc: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_config(doc: object) -> dict:
    keys = set(default_config())
    if type(doc) is not dict:
        raise ConfigError("config must be an object")
    if set(doc) != keys:
        extra, missing = set(doc) - keys, keys - set(doc)
        raise ConfigError("unknown or missing config keys",
                          path=[sorted(extra or missing)[0]])
    if doc["schema"] != SCHEMA:
        raise ConfigError("unsupported config schema", path=["schema"])
    if type(doc["revision"]) is not int or doc["revision"] < 1:
        raise ConfigError("revision must be a positive int", path=["revision"])
    langs = doc["languages"]
    if type(langs) is not list or not langs or len(set(langs)) != len(langs) \
            or not set(langs) <= SUPPORTED_LANGUAGES:
        raise ConfigError("languages must be a non-empty unique subset of the registry",
                          path=["languages"])
    mp = doc["mapping_profile"]
    if type(mp) is not dict or mp != {"id": PROFILE_ID, "version": PROFILE_VERSION,
                                      "digest": PROFILE_DIGEST}:
        raise ConfigError("mapping profile does not match the pinned registry digest",
                          path=["mapping_profile"])
    if type(doc["limits"]) is not dict:
        raise ConfigError("limits must be an object", path=["limits"])
    try:
        HARD_CEILING.tightened(**doc["limits"])
    except TypeError:
        raise ConfigError("unknown limit key", path=["limits"]) from None
    feats = doc["features"]
    if type(feats) is not dict or set(feats) != set(FEATURES) \
            or not all(type(v) is bool for v in feats.values()):
        raise ConfigError("features must set every known gate to a bool", path=["features"])
    if feats["zero_copy"]:
        raise ConfigError("zero_copy is not certified and may not be enabled", path=["features", "zero_copy"])
    if doc["runtime"] != {"canonical_abi": "1", "string_encoding": "utf8"}:
        raise ConfigError("unsupported runtime settings", path=["runtime"])
    if doc["environment"] not in ENVIRONMENTS or type(doc["site"]) is not str or not doc["site"]:
        raise ConfigError("invalid environment/site", path=["environment"])
    return copy.deepcopy(doc)


@dataclass(frozen=True)
class Snapshot:
    revision: int
    digest: str
    doc: MappingProxyType
    limits: Limits
    languages: frozenset
    activated_at: float
    provenance: tuple


def approve(doc: dict, approver: str, key: bytes) -> dict:
    d = digest(doc)
    return {"approver": approver, "digest": d,
            "mac": hmac.new(key, d.encode(), hashlib.sha256).hexdigest()}


class ConfigManager:
    def __init__(self, keyring: dict, *, quorum: int = 2, audit=None, initial: dict | None = None):
        if quorum < 1 or len(keyring) < quorum:
            raise ConfigError("keyring must hold at least quorum approvers")
        self._keyring = dict(keyring)
        self.quorum = quorum
        self.audit = audit
        self._lock = threading.Lock()
        self.history: list[Snapshot] = []
        doc = validate_config(initial or default_config())
        self._current = self._snap(doc, ("bootstrap",))
        self.history.append(self._current)

    def rotate_approver_key(self, approver: str, key: bytes, *, actor: str = "security"):
        """Replace an approver's key; approvals made with the old key stop verifying."""
        if type(key) is not bytes or len(key) < 32:
            raise ConfigError("approver key must be >= 32 bytes")
        with self._lock:
            self._keyring[approver] = key
        if self.audit:
            self.audit.emit("mapping_policy_change", actor, action="approver_key_rotated", approver=approver)

    def revoke_approver(self, approver: str, *, actor: str = "security"):
        with self._lock:
            if len(self._keyring) - 1 < self.quorum:
                raise ConfigError("revocation would make the quorum unreachable")
            self._keyring.pop(approver, None)
        if self.audit:
            self.audit.emit("mapping_policy_change", actor, action="approver_revoked", approver=approver)

    @property
    def current(self) -> Snapshot:
        return self._current

    def _snap(self, doc, prov) -> Snapshot:
        return Snapshot(doc["revision"], digest(doc), MappingProxyType(doc),
                        HARD_CEILING.tightened(**doc["limits"]), frozenset(doc["languages"]),
                        time.time(), tuple(prov))

    def verify_approvals(self, doc: dict, approvals: list) -> tuple:
        d = digest(doc)
        ok = set()
        for a in approvals:
            if type(a) is not dict:
                continue
            key = self._keyring.get(a.get("approver"))
            if key is None or a.get("digest") != d:
                continue
            mac = hmac.new(key, d.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(mac, str(a.get("mac", ""))):
                ok.add(a["approver"])
        if len(ok) < self.quorum:
            if self.audit:
                self.audit.emit("trust_check_failed", "config", digest=d, valid=len(ok))
            raise ProvenanceError(f"config approved by {len(ok)} of required {self.quorum} approvers")
        return tuple(sorted(ok))

    def activate(self, doc: dict, approvals: list, *, actor: str = "operator") -> Snapshot:
        """Validate, verify provenance, and atomically activate *doc*."""
        doc = validate_config(doc)
        who = self.verify_approvals(doc, approvals)
        with self._lock:
            if doc["revision"] <= self._current.revision:
                raise ConfigError("revision must increase (replay/downgrade refused)", path=["revision"])
            snap = self._snap(doc, who)
            self.history.append(snap)
            self._current = snap
        if self.audit:
            self.audit.emit("config_activated", actor, revision=snap.revision, digest=snap.digest,
                            approvers=",".join(who))
        return snap

    def rollback(self, *, actor: str = "operator") -> Snapshot:
        with self._lock:
            if len(self.history) < 2:
                raise ConfigError("no previous revision to roll back to")
            idx = self.history.index(self._current)
            if idx == 0:
                raise ConfigError("already at the oldest revision")
            self._current = self.history[idx - 1]
            snap = self._current
        if self.audit:
            self.audit.emit("config_rolled_back", actor, revision=snap.revision, digest=snap.digest)
        return snap

    def provenance(self) -> list:
        return [{"revision": s.revision, "digest": s.digest, "approvers": list(s.provenance),
                 "activated_at": s.activated_at, "environment": s.doc["environment"],
                 "site": s.doc["site"]} for s in self.history]


def require(snapshot: Snapshot, language: str):
    if language not in snapshot.languages:
        raise InteropError("language disabled by configuration", code="PK_INTEROP_UNREPRESENTABLE",
                           target_language=language)
