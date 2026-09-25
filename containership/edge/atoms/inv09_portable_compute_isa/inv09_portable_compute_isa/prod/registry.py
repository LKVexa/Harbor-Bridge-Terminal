"""M05 specification registry, M06 engine capability registry, M22 profile schema.

All three are carried in one versioned, content-addressed *policy bundle*
(``PK_ISA_POLICY_BUNDLE/1``).  The bundle is strictly schema-checked (unknown
fields refused), every feature a profile names must be registered in the pinned
spec, and the bundle revision is the SHA-256 of its canonical JSON - that
revision is bound into every attestation (M08) and cache key (M09).
Signature verification of a distributed bundle lives in :mod:`attest`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .errors import Code, InvalidModule

BUNDLE_SCHEMA = "PK_ISA_POLICY_BUNDLE/1"
DETERMINISM_CLASSES = ("deterministic", "extended", "permissive")


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    status: str             # standard | phase-4 | unsupported
    deterministic: bool     # can it cause cross-host divergence on its own?
    validator_supported: bool  # does M02 type-check it?


@dataclass(frozen=True)
class Profile:
    id: str
    determinism: str
    features: frozenset[str]
    require_nan_canonicalization: bool
    allowed_import_classes: frozenset[str]


@dataclass(frozen=True)
class Engine:
    id: str
    version: str
    features: frozenset[str]
    nan_canonicalization: bool
    fuel_metering: bool
    status: str  # supported | deprecated | revoked


@dataclass(frozen=True)
class PolicyBundle:
    revision: str
    spec_id: str
    features: Mapping[str, FeatureSpec]
    profiles: Mapping[str, Profile]
    engines: Mapping[str, Engine]
    epoch: int
    raw: bytes

    @property
    def known_features(self) -> frozenset[str]:
        return frozenset(self.features)


def _need(d: Mapping, keys: set[str], where: str) -> None:
    if not isinstance(d, dict):
        raise InvalidModule(Code.REGISTRY_INVALID, f"{where} must be an object")
    extra, missing = set(d) - keys, keys - set(d)
    if extra or missing:
        raise InvalidModule(Code.REGISTRY_INVALID,
                            f"{where}: unknown fields {sorted(extra)} missing {sorted(missing)}")


def _strs(v, where) -> frozenset[str]:
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v) or len(set(v)) != len(v):
        raise InvalidModule(Code.REGISTRY_INVALID, f"{where} must be a list of unique strings")
    return frozenset(v)


def load_bundle(raw: bytes) -> PolicyBundle:
    """Parse and strictly validate a policy bundle (fail closed)."""
    if len(raw) > 1_000_000:
        raise InvalidModule(Code.REGISTRY_INVALID, "bundle too large")
    try:
        doc = json.loads(raw.decode("utf-8"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (UnicodeDecodeError, ValueError) as exc:
        raise InvalidModule(Code.REGISTRY_INVALID, f"bundle is not strict JSON: {exc}") from None
    _need(doc, {"schema", "spec_id", "epoch", "features", "profiles", "engines"}, "bundle")
    if doc["schema"] != BUNDLE_SCHEMA:
        raise InvalidModule(Code.REGISTRY_INVALID, f"unsupported bundle schema {doc['schema']!r}")
    if not isinstance(doc["epoch"], int) or isinstance(doc["epoch"], bool) or doc["epoch"] < 0:
        raise InvalidModule(Code.REGISTRY_INVALID, "epoch must be a non-negative int")
    feats: dict[str, FeatureSpec] = {}
    for name, f in doc["features"].items():
        _need(f, {"status", "deterministic", "validator_supported"}, f"feature {name}")
        if f["status"] not in ("standard", "phase-4", "unsupported"):
            raise InvalidModule(Code.REGISTRY_INVALID, f"feature {name}: bad status")
        if not all(isinstance(f[k], bool) for k in ("deterministic", "validator_supported")):
            raise InvalidModule(Code.REGISTRY_INVALID, f"feature {name}: flags must be bool")
        feats[name] = FeatureSpec(name, f["status"], f["deterministic"], f["validator_supported"])
    profiles: dict[str, Profile] = {}
    for pid, p in doc["profiles"].items():
        _need(p, {"determinism", "features", "require_nan_canonicalization", "allowed_import_classes"},
              f"profile {pid}")
        pf = _strs(p["features"], f"profile {pid}.features")
        unknown = pf - set(feats)
        if unknown:
            raise InvalidModule(Code.REGISTRY_INVALID, f"profile {pid} names unregistered {sorted(unknown)}")
        if p["determinism"] not in DETERMINISM_CLASSES:
            raise InvalidModule(Code.REGISTRY_INVALID, f"profile {pid}: bad determinism class")
        if p["determinism"] == "deterministic":
            nd = sorted(x for x in pf if not feats[x].deterministic)
            if nd:
                raise InvalidModule(Code.REGISTRY_INVALID,
                                    f"deterministic profile {pid} permits non-deterministic {nd}")
            if not p["require_nan_canonicalization"]:
                raise InvalidModule(Code.REGISTRY_INVALID,
                                    f"deterministic profile {pid} must require NaN canonicalization")
        profiles[pid] = Profile(pid, p["determinism"], pf, bool(p["require_nan_canonicalization"]),
                                _strs(p["allowed_import_classes"], f"profile {pid}.imports"))
    engines: dict[str, Engine] = {}
    for eid, e in doc["engines"].items():
        _need(e, {"version", "features", "nan_canonicalization", "fuel_metering", "status"}, f"engine {eid}")
        ef = _strs(e["features"], f"engine {eid}.features")
        if ef - set(feats):
            raise InvalidModule(Code.REGISTRY_INVALID, f"engine {eid} names unregistered features")
        if e["status"] not in ("supported", "deprecated", "revoked"):
            raise InvalidModule(Code.REGISTRY_INVALID, f"engine {eid}: bad status")
        engines[eid] = Engine(eid, str(e["version"]), ef, bool(e["nan_canonicalization"]),
                              bool(e["fuel_metering"]), e["status"])
    rev = "bundle:sha256:" + hashlib.sha256(canonical_json(doc)).hexdigest()
    return PolicyBundle(rev, str(doc["spec_id"]), MappingProxyType(feats), MappingProxyType(profiles),
                        MappingProxyType(engines), doc["epoch"], canonical_json(doc))


#: Reference bundle shipped with v4.3.0.  Production deployments MUST replace
#: the engine entries with engines actually certified under M21, and distribute
#: the bundle signed (M22).  The engine below is a placeholder identity.
DEFAULT_BUNDLE_DOC: dict[str, Any] = {
    "schema": BUNDLE_SCHEMA,
    "spec_id": "wasm-core-2.0",
    "epoch": 1,
    "features": {
        "core": {"status": "standard", "deterministic": True, "validator_supported": True},
        "mutable-globals-import": {"status": "standard", "deterministic": True, "validator_supported": True},
        "sign-ext": {"status": "standard", "deterministic": True, "validator_supported": True},
        "sat-float-to-int": {"status": "standard", "deterministic": True, "validator_supported": True},
        "multi-value": {"status": "standard", "deterministic": True, "validator_supported": True},
        "bulk-memory": {"status": "standard", "deterministic": True, "validator_supported": True},
        "reference-types": {"status": "standard", "deterministic": True, "validator_supported": True},
        "simd": {"status": "standard", "deterministic": True, "validator_supported": False},
        "simd-relaxed": {"status": "phase-4", "deterministic": False, "validator_supported": False},
        "threads": {"status": "phase-4", "deterministic": False, "validator_supported": False},
        "float-relaxed": {"status": "unsupported", "deterministic": False, "validator_supported": False},
        "wall-clock": {"status": "standard", "deterministic": False, "validator_supported": True},
    },
    "profiles": {
        "deterministic": {
            "determinism": "deterministic",
            "features": ["core", "mutable-globals-import", "sign-ext", "sat-float-to-int",
                         "multi-value", "bulk-memory", "reference-types"],
            "require_nan_canonicalization": True,
            "allowed_import_classes": ["pure"],
        },
        "extended": {
            "determinism": "extended",
            "features": ["core", "mutable-globals-import", "sign-ext", "sat-float-to-int",
                         "multi-value", "bulk-memory", "reference-types", "simd"],
            "require_nan_canonicalization": False,
            "allowed_import_classes": ["pure", "io-deterministic"],
        },
        "permissive": {
            "determinism": "permissive",
            "features": ["core", "mutable-globals-import", "sign-ext", "sat-float-to-int",
                         "multi-value", "bulk-memory", "reference-types", "simd", "simd-relaxed",
                         "threads", "float-relaxed", "wall-clock"],
            "require_nan_canonicalization": False,
            "allowed_import_classes": ["pure", "io-deterministic", "nondeterministic"],
        },
    },
    "engines": {
        "reference-engine": {
            "version": "0.0.0-placeholder",
            "features": ["core", "mutable-globals-import", "sign-ext", "sat-float-to-int",
                         "multi-value", "bulk-memory", "reference-types", "simd", "wall-clock"],
            "nan_canonicalization": True,
            "fuel_metering": True,
            "status": "supported",
        }
    },
}


def default_bundle() -> PolicyBundle:
    return load_bundle(canonical_json(DEFAULT_BUNDLE_DOC))
