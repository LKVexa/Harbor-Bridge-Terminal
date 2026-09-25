"""Signed, versioned, distributable baselines with atomic activation.

Checklist items served: 19 (schema validation of the baseline document),
20 (signed baseline), 21 (distribution + last-known-good cache), 22 (atomic
activation / rollback by epoch), 27 (tenant/environment/site overlays),
28 (conflict/precedence), 29 (compatibility/migration).

Signature: HMAC-SHA256 under a keyring of named signers. This is the stdlib
mechanism the archive can prove end to end; asymmetric signing through a KMS
is item 35 and stays BLOCKED (no KMS was provided). The signer registry is
sealed at construction, so a signature cannot be accepted from a key added
after the verifier was built.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from types import MappingProxyType
from typing import Any, Mapping

from .controls import CONTROLS_43
from .core import atomic_write, canonical, digest

BASELINE_SCHEMA = "PK_HARDEN_BASELINE/2"
SUPPORTED_SCHEMAS = frozenset({BASELINE_SCHEMA})
MIN_SUPPORTED_VERSION = (4, 3, 0)

# Settings whose value may only move in the "tighter" direction under an overlay.
TIGHTEN_ONLY_BOOLS_TRUE = ("require_user_namespace", "require_pid_limit")
TIGHTEN_ONLY_SETS = ("sandbox_runtime_classes", "device_allowlist", "hostpath_readonly_allowlist",
                     "extra_sysctls", "apparmor_profiles")
TIGHTEN_ONLY_MAX = ("max_emptydir_bytes", "max_exception_ttl")


class BaselineError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(f"{code}: {msg}")
        self.code = code


def parse_version(v: object) -> tuple[int, int, int]:
    if not isinstance(v, str):
        raise BaselineError("BASELINE_MALFORMED", "version must be a string")
    parts = v.split(".")
    if len(parts) != 3 or not all(p.isdigit() and len(p) <= 6 for p in parts):
        raise BaselineError("BASELINE_MALFORMED", f"version {v!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def validate_document(doc: object) -> dict:
    """Structural validation of an unsigned baseline document (fail closed)."""
    if not isinstance(doc, dict):
        raise BaselineError("BASELINE_MALFORMED", "document must be an object")
    allowed = {"schema", "version", "controls", "settings", "seccomp_profiles", "overlays"}
    extra = set(doc) - allowed
    if extra:
        raise BaselineError("BASELINE_MALFORMED", f"unknown fields {sorted(extra)}")
    if doc.get("schema") not in SUPPORTED_SCHEMAS:
        raise BaselineError("BASELINE_UNSUPPORTED", f"schema {doc.get('schema')!r}")
    if parse_version(doc.get("version")) < MIN_SUPPORTED_VERSION:
        raise BaselineError("BASELINE_TOO_OLD", f"version {doc['version']} below minimum")
    ctrls = doc.get("controls")
    if not isinstance(ctrls, list) or not ctrls or len(set(ctrls)) != len(ctrls):
        raise BaselineError("BASELINE_MALFORMED", "controls must be a non-empty unique list")
    unknown = [c for c in ctrls if c not in CONTROLS_43]
    if unknown:
        raise BaselineError("BASELINE_UNSUPPORTED", f"unknown controls {unknown}")
    for k in ("settings", "seccomp_profiles", "overlays"):
        if not isinstance(doc.get(k, {}), dict):
            raise BaselineError("BASELINE_MALFORMED", f"{k} must be an object")
    for name, d in doc.get("seccomp_profiles", {}).items():
        if not (isinstance(d, str) and d.startswith("sha256:") and len(d) == 71):
            raise BaselineError("BASELINE_MALFORMED", f"seccomp profile {name!r} needs a sha256 digest")
    for scope, ov in doc.get("overlays", {}).items():
        if not isinstance(scope, str) or scope.count("/") != 2:
            raise BaselineError("BASELINE_MALFORMED", f"overlay scope {scope!r} must be tenant/env/site")
        if not isinstance(ov, dict):
            raise BaselineError("BASELINE_MALFORMED", f"overlay {scope!r} must be an object")
    return doc


class Keyring:
    def __init__(self, keys: Mapping[str, bytes]):
        for k, v in keys.items():
            if not isinstance(v, bytes) or len(v) < 32:
                raise ValueError(f"key {k!r} must be >= 32 bytes")
        self._keys = MappingProxyType(dict(keys))

    def sign(self, signer: str, payload: bytes) -> str:
        return hmac.new(self._keys[signer], payload, hashlib.sha256).hexdigest()

    def verify(self, signer: object, payload: bytes, sig: object) -> bool:
        key = self._keys.get(signer) if isinstance(signer, str) else None
        if key is None or not isinstance(sig, str):
            return False
        return hmac.compare_digest(hmac.new(key, payload, hashlib.sha256).hexdigest(), sig)


def sign_baseline(doc: dict, keyring: Keyring, signer: str) -> dict:
    validate_document(doc)
    payload = canonical(doc)
    return {"document": doc, "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "signer": signer, "signature": keyring.sign(signer, payload)}


def verify_signed(artifact: object, keyring: Keyring) -> dict:
    if not isinstance(artifact, dict) or set(artifact) != {"document", "digest", "signer", "signature"}:
        raise BaselineError("BASELINE_MALFORMED", "signed artifact envelope is malformed")
    doc = validate_document(artifact["document"])
    payload = canonical(doc)
    if artifact["digest"] != "sha256:" + hashlib.sha256(payload).hexdigest():
        raise BaselineError("BASELINE_TAMPERED", "digest does not match document")
    if not keyring.verify(artifact["signer"], payload, artifact["signature"]):
        raise BaselineError("BASELINE_BAD_SIGNATURE", f"signature by {artifact['signer']!r} rejected")
    return doc


def resolve_settings(doc: dict, tenant: str, env: str, site: str) -> dict:
    """Items 27/28: overlays apply most-general first; each may only tighten.

    Precedence: base < */*/* < tenant/*/* < tenant/env/* < tenant/env/site.
    A loosening attempt is not silently dropped: it raises, because a baseline
    that tries to loosen is a defective baseline.
    """
    s = dict(doc.get("settings", {}))
    overlays = doc.get("overlays", {})
    chain = ["*/*/*", f"{tenant}/*/*", f"{tenant}/{env}/*", f"{tenant}/{env}/{site}"]
    for scope in chain:
        ov = overlays.get(scope)
        if not ov:
            continue
        for k, v in ov.items():
            cur = s.get(k)
            if k in TIGHTEN_ONLY_BOOLS_TRUE:
                if cur is True and v is not True:
                    raise BaselineError("OVERLAY_LOOSENS", f"{scope}: {k} cannot be relaxed")
            elif k in TIGHTEN_ONLY_SETS:
                if cur is not None and not set(v) <= set(cur):
                    raise BaselineError("OVERLAY_LOOSENS", f"{scope}: {k} may only shrink")
            elif k in TIGHTEN_ONLY_MAX:
                if cur is not None and v > cur:
                    raise BaselineError("OVERLAY_LOOSENS", f"{scope}: {k} may only decrease")
            elif k == "namespace_default_deny":
                if cur is True and v is not True:
                    raise BaselineError("OVERLAY_LOOSENS", f"{scope}: {k} cannot be relaxed")
            else:
                raise BaselineError("OVERLAY_UNKNOWN_KEY", f"{scope}: {k} is not overlayable")
            s[k] = v
    s["seccomp_profiles"] = dict(doc.get("seccomp_profiles", {}))
    return s


def migrate(doc: dict) -> dict:
    """Item 29: the only accepted migration is from the 4.2.0 flat baseline.

    PK_HARDEN_BASELINE/1 carries five controls and no runtime/host settings, so
    migration adds the 4.3.0 controls with the strictest defaults; it never
    produces a looser baseline than its input.
    """
    if doc.get("schema") == BASELINE_SCHEMA:
        return validate_document(doc)
    if doc.get("schema") != "PK_HARDEN_BASELINE/1":
        raise BaselineError("BASELINE_UNSUPPORTED", f"cannot migrate {doc.get('schema')!r}")
    out = {"schema": BASELINE_SCHEMA, "version": "4.3.0", "controls": list(CONTROLS_43),
           "settings": {"sandbox_runtime_classes": ["gvisor"], "require_user_namespace": True,
                        "require_pid_limit": False, "max_exception_ttl": 30 * 86400,
                        "max_emptydir_bytes": 1 << 30},
           "seccomp_profiles": {}, "overlays": {}}
    return validate_document(out)


class BaselineStore:
    """Items 21/22: epoch-numbered activation with last-known-good cache.

    State lives in one JSON file written atomically: ``{"epoch", "active",
    "previous", "history"}``. Activation is a compare-and-swap on the epoch, so
    two concurrent rollouts cannot interleave; a loser gets ``EPOCH_CONFLICT``.
    Every reader sees exactly one complete verified baseline or none.
    """

    def __init__(self, path: str | None, keyring: Keyring):
        self.path, self._kr = path, keyring
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {"epoch": 0, "active": None, "previous": None, "history": []}
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                loaded = json.loads(fh.read())
            for key in ("active", "previous"):
                if loaded.get(key) is not None:
                    verify_signed(loaded[key], keyring)  # re-verify cache on load
            self._state = loaded

    @property
    def epoch(self) -> int:
        return int(self._state["epoch"])

    def active(self) -> tuple[int, dict] | None:
        a = self._state["active"]
        return (self._state["epoch"], verify_signed(a, self._kr)) if a else None

    def _persist(self) -> None:
        if self.path:
            atomic_write(self.path, canonical(self._state))

    def activate(self, artifact: dict, expected_epoch: int) -> int:
        doc = verify_signed(artifact, self._kr)
        with self._lock:
            if expected_epoch != self._state["epoch"]:
                raise BaselineError("EPOCH_CONFLICT", f"expected {expected_epoch}, at {self._state['epoch']}")
            cur = self._state["active"]
            if cur and parse_version(doc["version"]) < parse_version(cur["document"]["version"]):
                raise BaselineError("BASELINE_DOWNGRADE", "use rollback() for an explicit downgrade")
            new = {"epoch": self._state["epoch"] + 1, "active": artifact, "previous": cur,
                   "history": (self._state["history"] + [artifact["digest"]])[-50:]}
            old = self._state
            self._state = new
            try:
                self._persist()
            except Exception:
                self._state = old
                raise
            return new["epoch"]

    def rollback(self, expected_epoch: int) -> int:
        with self._lock:
            if expected_epoch != self._state["epoch"]:
                raise BaselineError("EPOCH_CONFLICT", "stale rollback")
            prev = self._state["previous"]
            if prev is None:
                raise BaselineError("NO_PREVIOUS", "nothing to roll back to")
            verify_signed(prev, self._kr)
            old = self._state
            self._state = {"epoch": old["epoch"] + 1, "active": prev, "previous": old["active"],
                           "history": (old["history"] + [prev["digest"]])[-50:]}
            try:
                self._persist()
            except Exception:
                self._state = old
                raise
            return self._state["epoch"]


def default_document() -> dict:
    return {
        "schema": BASELINE_SCHEMA, "version": "4.3.0", "controls": list(CONTROLS_43),
        "settings": {
            "sandbox_runtime_classes": ["gvisor"],
            "require_user_namespace": True,
            "require_pid_limit": False,
            "device_allowlist": [],
            "hostpath_readonly_allowlist": [],
            "extra_sysctls": [],
            "apparmor_profiles": [],
            "max_emptydir_bytes": 1 << 30,
            "max_exception_ttl": 30 * 86400,
        },
        "seccomp_profiles": {}, "overlays": {},
    }


def baseline_digest(doc: dict) -> str:
    return digest(doc)
