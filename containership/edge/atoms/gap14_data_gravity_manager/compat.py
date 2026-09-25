"""pk_core compatibility handshake and gate-result integrity (G14-P0-01).

The conformance runtime is external.  This module never fabricates it; it
decides whether the *installed* runtime is the certified one and guarantees a
missing, untrusted, incompatible or partially-executed gate can never be
reported as PASS.

Pinning: ``PKCORE_PIN`` records the certified semantic-version range, required
API surface and (once the estate publishes it) the sha256 of the certified
distribution.  ``digest`` of ``None`` means "not yet pinned" and yields
``UNPINNED`` status, which is itself non-certifying.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import re
import site
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

PKCORE_PIN: Mapping[str, Any] = {
    "range_min": (1, 0, 0),         # inclusive
    "range_max": (2, 0, 0),         # exclusive: next major is incompatible
    "conformance_schema": "PK_CHECKLIST/1",
    "required_api": ("pk_core.checklist:ChecklistItem", "pk_core.checklist:Finding",
                     "pk_core.component:Component", "pk_core.contract:Contract",
                     "pk_core.contract:Dependency", "pk_core.contract:Slo"),
    "digest": None,                 # sha256 of certified wheel/tree - set by release engineering
}
EXPECTED_CHECKS = 100

PASS, FAIL = "PASS", "FAIL"


@dataclass
class Handshake:
    status: str                       # OK | UNPINNED | error code
    version: str | None = None
    location: str | None = None
    capabilities: list[str] = field(default_factory=list)
    tree_digest: str | None = None
    duration_s: float = 0.0
    detail: str = ""

    @property
    def certifying(self) -> bool:
        return self.status == "OK"

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in ("status", "version", "location", "capabilities", "tree_digest", "duration_s", "detail")}


def _vtuple(v: str) -> tuple[int, int, int] | None:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None  # type: ignore[return-value]


def _user_global_paths() -> list[str]:
    paths = []
    try:
        paths.append(site.getusersitepackages())
    except Exception:
        pass
    return [os.path.realpath(p) for p in paths if p]


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return "sha256:" + h.hexdigest()


def handshake(pin: Mapping[str, Any] = PKCORE_PIN, *, allowed_roots: list[str] | None = None,
              importer: Callable[[str], Any] = importlib.import_module) -> Handshake:
    t0 = time.perf_counter()
    hs = Handshake("G14_PKCORE_MISSING")
    try:
        spec = importlib.util.find_spec("pk_core")
        if spec is None or not spec.origin:
            hs.detail = "pk_core not importable"
            return hs
        loc = os.path.realpath(os.path.dirname(spec.origin))
        hs.location = loc
        if any(loc.startswith(u) for u in _user_global_paths()) or (
                allowed_roots is not None and not any(loc.startswith(os.path.realpath(r)) for r in allowed_roots)):
            hs.status, hs.detail = "G14_PKCORE_UNTRUSTED_PATH", "pk_core resolved outside the locked environment"
            return hs
        mod = importer("pk_core")
        hs.version = str(getattr(mod, "__version__", ""))
        vt = _vtuple(hs.version)
        if vt is None or not (tuple(pin["range_min"]) <= vt < tuple(pin["range_max"])):
            hs.status, hs.detail = "G14_PKCORE_INCOMPATIBLE", f"version {hs.version!r} outside certified range"
            return hs
        schema = getattr(mod, "CONFORMANCE_SCHEMA", pin["conformance_schema"])
        if schema != pin["conformance_schema"]:
            hs.status, hs.detail = "G14_PKCORE_INCOMPATIBLE", f"conformance schema {schema!r}"
            return hs
        for ref in pin["required_api"]:
            modname, attr = ref.split(":")
            try:
                if not hasattr(importer(modname), attr):
                    raise AttributeError(attr)
            except Exception:
                hs.status, hs.detail = "G14_PKCORE_INCOMPATIBLE", f"missing API {ref}"
                return hs
            hs.capabilities.append(ref)
        hs.tree_digest = tree_digest(Path(loc))
        if pin.get("digest") is None:
            hs.status, hs.detail = "UNPINNED", "certified digest not yet recorded; non-certifying"
        elif hs.tree_digest != pin["digest"]:
            hs.status, hs.detail = "G14_PKCORE_DIGEST_MISMATCH", "installed tree differs from pinned digest"
        else:
            hs.status = "OK"
        return hs
    finally:
        hs.duration_s = round(time.perf_counter() - t0, 6)


@dataclass
class GateResult:
    verdict: str
    reason_code: str | None
    attempted: int
    passed: int
    failed: int
    skipped: int
    skip_reasons: dict[str, str]
    handshake: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def evaluate_gate(hs: Handshake, results: list[Mapping[str, Any]] | None, *,
                  approved_skips: Mapping[str, str] | None = None) -> GateResult:
    """Turn raw per-check results into a verdict that cannot overstate coverage.

    ``results`` items: {"check_id", "status": pass|fail|skip, "reason"?}.
    PASS requires: certifying handshake, exactly EXPECTED_CHECKS unique checks
    attempted, zero failures, and every skip listed in ``approved_skips``.
    """
    approved_skips = approved_skips or {}
    results = results or []
    ids = [r.get("check_id") for r in results]
    passed = sum(r.get("status") == "pass" for r in results)
    failed = sum(r.get("status") == "fail" for r in results)
    skips = {r["check_id"]: str(r.get("reason", "")) for r in results if r.get("status") == "skip"}
    base = dict(attempted=len(set(ids)), passed=passed, failed=failed, skipped=len(skips), skip_reasons=skips,
                handshake=hs.as_dict())
    if not hs.certifying:
        return GateResult(FAIL, hs.status if hs.status.startswith("G14_") else "G14_PKCORE_INCOMPATIBLE", **base)
    if len(ids) != len(set(ids)) or len(set(ids)) != EXPECTED_CHECKS:
        return GateResult(FAIL, "G14_GATE_PARTIAL", **base)
    if any(c not in approved_skips for c in skips):
        return GateResult(FAIL, "G14_GATE_PARTIAL", **base)
    if failed:
        return GateResult(FAIL, None, **base)
    return GateResult(PASS, None, **base)
