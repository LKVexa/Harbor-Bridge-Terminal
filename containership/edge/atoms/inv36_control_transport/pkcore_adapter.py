"""The single boundary between INV-36 and the external estate package ``pk_core`` (MC-01).

Contract (INV-36 side; confirmation by the estate owner is an open governance item):

* distribution/module: ``pk_core``; supported versions ``>=4.0.0,<5.0.0``
  (semantic versioning: minor = additive, major = breaking);
* Python ABI: CPython 3.11-3.13;
* classification: **certification dependency** - never a runtime dependency of
  the transport (declared as the ``estate`` extra in pyproject.toml);
* required symbols are listed in :data:`REQUIRED_SYMBOLS`; nothing else in
  this repository may import ``pk_core`` directly (enforced by a test).

Missing or incompatible ``pk_core`` raises :class:`GateUnavailable` - it is
never reported as a pass.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
from typing import Any

from .errors import ErrorCode, Inv36Error

MODULE = "pk_core"
MIN_VERSION = (4, 0, 0)
MAX_VERSION_EXCLUSIVE = (5, 0, 0)
PYTHON_ABI = ((3, 11), (3, 13))
SUPPORTED_EVIDENCE_SCHEMAS = ("pk_core.findings/1",)
REQUIRED_SYMBOLS: dict[str, dict[str, str]] = {
    "pk_core.contract.Contract": {"kind": "class", "signature": "Contract(element, name, responsibility, owns, "
                                  "not_owns, dependencies, source_of_truth, assumptions, boundaries, mandatory, "
                                  "optional, non_goals, interfaces, threats, failure_modes, slos, signals)",
                                  "returns": "Contract", "side_effects": "none"},
    "pk_core.contract.Dependency": {"kind": "class", "signature": "Dependency(name, direction, purpose)",
                                    "returns": "Dependency", "side_effects": "none"},
    "pk_core.contract.Slo": {"kind": "class", "signature": "Slo(name, objective, budget)", "returns": "Slo",
                             "side_effects": "none"},
    "pk_core.checklist.ChecklistItem": {"kind": "class", "signature": "opaque checklist row",
                                        "returns": "-", "side_effects": "none"},
    "pk_core.checklist.Finding": {"kind": "class", "signature": "Finding(check_id, status, ...)",
                                  "returns": "-", "side_effects": "none"},
    "pk_core.component.Component": {"kind": "class", "signature": "Component.assess_all() -> dict[str, list[Finding]]",
                                    "returns": "findings by dimension", "side_effects": "reads CHECKLIST.json",
                                    "exceptions": "any exception => ERROR"},
}


class GateUnavailable(Inv36Error, RuntimeError):
    code = ErrorCode.GATE_UNAVAILABLE


def _ver(text: str) -> tuple[int, int, int]:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", text or "")
    if not m:
        raise GateUnavailable("pk_core version unparseable", code=ErrorCode.GATE_SCHEMA)
    return int(m[1]), int(m[2]), int(m[3])


def probe() -> dict[str, Any]:
    """Describe pk_core availability without raising."""
    if not PYTHON_ABI[0] <= sys.version_info[:2] <= PYTHON_ABI[1]:
        return {"status": "incompatible", "reason": "python_abi", "python": sys.version.split()[0]}
    try:
        mod = importlib.import_module(MODULE)
    except ModuleNotFoundError:
        return {"status": "unavailable", "reason": "not_installed"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "reason": type(exc).__name__}
    version = getattr(mod, "__version__", "")
    try:
        v = _ver(version)
    except GateUnavailable:
        return {"status": "incompatible", "reason": "version_unparseable", "version": version}
    if not MIN_VERSION <= v < MAX_VERSION_EXCLUSIVE:
        return {"status": "incompatible", "reason": "version_out_of_range", "version": version}
    missing = []
    for sym in REQUIRED_SYMBOLS:
        modname, _, attr = sym.rpartition(".")
        try:
            if not hasattr(importlib.import_module(modname), attr):
                missing.append(sym)
        except Exception:  # noqa: BLE001
            missing.append(sym)
    if missing:
        return {"status": "incompatible", "reason": "missing_symbols", "missing": missing, "version": version}
    return {"status": "available", "version": version}


def require(module: str, *names: str) -> tuple[Any, ...]:
    """Import required pk_core symbols or raise a typed, actionable error."""
    info = probe()
    if info["status"] != "available":
        raise GateUnavailable(f"pk_core required for estate integration: {info.get('reason')}",
                              detail={k: v for k, v in info.items() if k != "missing"})
    mod = importlib.import_module(f"{MODULE}.{module}")
    return tuple(getattr(mod, n) for n in names)


_RUNNER = r"""
import json, sys
sys.path[:0] = json.loads(sys.argv[1])
from inv36_control_transport.component import COMPONENT
out = []
for dim, fs in COMPONENT().assess_all().items():
    for f in fs:
        out.append({"check_id": str(getattr(f, "check_id", "")), "status": str(getattr(f, "status", "")),
                    "dimension": str(dim)})
print(json.dumps({"schema": "pk_core.findings/1", "findings": out}))
"""


def normalize(raw: dict) -> dict:
    """Validate a pk_core findings document; unknown schema revisions are rejected deterministically."""
    if not isinstance(raw, dict) or raw.get("schema") not in SUPPORTED_EVIDENCE_SCHEMAS:
        raise GateUnavailable("unsupported pk_core evidence schema", code=ErrorCode.GATE_SCHEMA,
                              detail={"schema": str(raw.get("schema") if isinstance(raw, dict) else None)})
    findings = raw.get("findings")
    if not isinstance(findings, list):
        raise GateUnavailable("malformed pk_core findings", code=ErrorCode.EVIDENCE_INVALID)
    ids = [f.get("check_id") for f in findings if isinstance(f, dict)]
    if len(ids) != len(findings) or len(set(ids)) != len(ids) or len(ids) != 100:
        raise GateUnavailable("pk_core findings must cover 100 unique controls", code=ErrorCode.EVIDENCE_INVALID,
                              detail={"count": len(ids)})
    statuses: dict[str, int] = {}
    for f in findings:
        s = str(f.get("status", "")).upper()
        statuses[s] = statuses.get(s, 0) + 1
    passed = statuses.get("PASS", 0) + statuses.get("PASSED", 0)
    return {"schema": raw["schema"], "controls": len(ids), "statuses": statuses,
            "all_pass": passed == len(ids)}


def run_gate(timeout_s: float = 300.0, runner: list[str] | None = None) -> dict:
    """Run the estate gate in a subprocess so a hung gate cannot deadlock the pipeline (MC-01.023)."""
    info = probe() if runner is None else {"status": "available", "version": "fake"}
    if info["status"] != "available":
        raise GateUnavailable(f"pk_core {info['status']}: {info.get('reason')}", detail={"reason": info.get("reason")})
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd = runner or [sys.executable, "-c", _RUNNER, json.dumps([root, os.environ.get("PK_CORE_PATH", "")])]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise GateUnavailable("pk_core gate timed out", code=ErrorCode.GATE_TIMEOUT,
                              detail={"timeout_s": timeout_s}) from exc
    if proc.returncode != 0:
        raise GateUnavailable("pk_core gate crashed", detail={"rc": proc.returncode,
                                                             "stderr_tail": proc.stderr[-200:]})
    try:
        raw = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise GateUnavailable("pk_core gate output unparseable", code=ErrorCode.EVIDENCE_INVALID) from exc
    return {"probe": info, "raw": raw, "normalized": normalize(raw)}
