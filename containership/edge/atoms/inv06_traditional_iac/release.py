"""Benchmarks/SLOs, acceptance evidence, staged rollout and the production exit gate.

* MC-051/MC-052 — ``run_benchmarks`` measures plan/apply/drift/backend-commit
  latency percentiles and throughput at several state sizes;
  ``SLO_THRESHOLDS`` are release-blocking via ``check_slos``.
* MC-053/MC-054 — ``capacity_model`` derives per-resource cost and a size
  ceiling from benchmark output; ``copy_audit`` counts the bytes the engine
  deep-copies per operation.
* MC-062 — ``build_evidence`` binds source digests (MANIFEST), interpreter,
  platform, test results and benchmark results into a signed
  ``PK_IAC_EVIDENCE/1`` record; ``verify_evidence`` re-checks it.
* MC-063 — ``CanaryRollout`` promotes a version through stages with health
  gates, halt criteria and automatic rollback.
* MC-069 — ``production_gate`` aggregates checklist status, readiness items
  and evidence into a deterministic GO / CONDITIONAL_GO / NO_GO verdict.  It
  never returns GO while an owner-sign-off or external item is open.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import statistics
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from typing import Any

from .state import IacState, _canonical_bytes

EVIDENCE_SCHEMA = "PK_IAC_EVIDENCE/1"
GATE_SCHEMA = "PK_IAC_GATE/1"
PKG = pathlib.Path(__file__).resolve().parent

# Release-blocking reference thresholds (seconds) for the reference engine on
# a developer-class host.  Estate SLOs (MC-070) are set by the owner.
SLO_THRESHOLDS = {
    "plan_p99_1k": 0.25,
    "apply_p99_1k": 0.25,
    "drift_p99_1k": 0.25,
    "commit_p99_1k": 1.0,
}


def _pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = min(len(xs) - 1, max(0, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def _resources(n: int, rev: int = 0) -> dict[str, Any]:
    return {f"vm.r{i:06d}": {"size": "small" if (i + rev) % 3 else "large", "tags": ["a", "b"], "n": i} for i in range(n)}


def run_benchmarks(sizes: tuple[int, ...] = (100, 1000), iterations: int = 15) -> dict[str, Any]:
    out: dict[str, Any] = {"schema": "PK_IAC_BENCH/1", "host": platform.platform(), "python": platform.python_version(), "results": {}}
    from .durable import FileStateBackend

    for n in sizes:
        lat: dict[str, list[float]] = {"plan": [], "apply": [], "drift": [], "commit": []}
        with tempfile.TemporaryDirectory() as td:
            be = FileStateBackend(td)
            s = IacState(_resources(n))
            for it in range(iterations):
                desired = _resources(n, it + 1)
                t = time.perf_counter(); p = s.plan(desired); lat["plan"].append(time.perf_counter() - t)
                t = time.perf_counter(); s.apply(p); lat["apply"].append(time.perf_counter() - t)
                t = time.perf_counter(); s.drift(desired); lat["drift"].append(time.perf_counter() - t)
                t = time.perf_counter(); be.commit_state(s, expected_serial=be.head_serial()); lat["commit"].append(time.perf_counter() - t)
            state_bytes = len(_canonical_bytes(s.snapshot()))
        out["results"][str(n)] = {
            op: {"p50": _pct(v, 50), "p95": _pct(v, 95), "p99": _pct(v, 99), "max": max(v), "mean": statistics.fmean(v), "ops_per_s": 1 / statistics.fmean(v)}
            for op, v in lat.items()
        } | {"state_bytes": state_bytes}
    return out


def check_slos(bench: Mapping[str, Any], thresholds: Mapping[str, float] = SLO_THRESHOLDS) -> dict[str, Any]:
    r = bench["results"].get("1000")
    if r is None:
        return {"pass": False, "violations": ["benchmark lacks 1000-resource tier"]}
    violations = []
    for key, limit in thresholds.items():
        op = key.split("_")[0]
        got = r[op]["p99"]
        if got > limit:
            violations.append(f"{key}: {got:.4f}s > {limit}s")
    return {"pass": not violations, "violations": violations}


def capacity_model(bench: Mapping[str, Any]) -> dict[str, Any]:
    tiers = sorted((int(k), v) for k, v in bench["results"].items())
    (n1, a), (n2, b) = tiers[0], tiers[-1]
    per_res = {op: (b[op]["p99"] - a[op]["p99"]) / max(1, n2 - n1) for op in ("plan", "apply", "drift", "commit")}
    bytes_per_res = (b["state_bytes"] - a["state_bytes"]) / max(1, n2 - n1)
    budget = SLO_THRESHOLDS["apply_p99_1k"]
    ceiling = int(budget / per_res["apply"]) if per_res["apply"] > 0 else None
    return {"per_resource_p99_s": per_res, "bytes_per_resource": bytes_per_res, "apply_ceiling_resources_within_slo": ceiling}


def copy_audit(n: int = 1000) -> dict[str, Any]:
    """Bytes of resource data copied per operation (engine defends against aliasing by copying)."""
    import copy as _copy

    counter = {"calls": 0, "bytes": 0}
    orig = _copy.deepcopy

    def counting(x: Any, memo: Any = None, _nil: Any = []) -> Any:  # noqa: B006
        counter["calls"] += 1
        try:
            counter["bytes"] += len(json.dumps(x, default=str))
        except Exception:  # noqa: BLE001
            pass
        return orig(x, memo)

    mod = sys.modules[IacState.__module__]
    report = {}
    s = IacState(_resources(n))
    mod.deepcopy = counting  # type: ignore[attr-defined]
    try:
        for name, fn in (("plan", lambda: s.plan(_resources(n, 1))), ("resources_view", lambda: s.resources), ("snapshot", s.snapshot)):
            counter.update(calls=0, bytes=0)
            fn()
            report[name] = dict(counter)
    finally:
        mod.deepcopy = orig  # type: ignore[attr-defined]
    return report


# ------------------------------------------------------------------ evidence
def file_digests(root: pathlib.Path = PKG) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name not in ("MANIFEST.sha256", "EXECUTION_REPORT.md") and not p.name.endswith(".pyc") and "evidence" not in p.parts:
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def build_evidence(*, version: str, tests: Mapping[str, Any], bench: Mapping[str, Any] | None, signer: Any, source_revision: str = "archive") -> dict[str, Any]:
    body = {
        "schema": EVIDENCE_SCHEMA,
        "component": "INV-06",
        "version": version,
        "source_revision": source_revision,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation(), "platform": sys.platform, "machine": platform.machine()},
        "dependencies": {"third_party": [], "pk_core": "not bundled"},
        "files": file_digests(),
        "tests": dict(tests),
        "benchmarks": dict(bench) if bench else None,
    }
    body["digest"] = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    return {**body, "signature": signer.sign({"digest": body["digest"]})}


def verify_evidence(ev: Mapping[str, Any], signer: Any, *, check_files: bool = True) -> None:
    body = {k: v for k, v in ev.items() if k not in ("digest", "signature")}
    if hashlib.sha256(_canonical_bytes(body)).hexdigest() != ev.get("digest"):
        raise ValueError("evidence digest mismatch")
    signer.verify({"digest": ev["digest"]}, ev["signature"])
    if check_files:
        cur = file_digests()
        changed = sorted(k for k in set(cur) | set(ev["files"]) if cur.get(k) != ev["files"].get(k))
        if changed:
            raise ValueError(f"package differs from evidence: {changed[:10]}")


# ------------------------------------------------------------------- rollout
class CanaryRollout:
    STAGES = (("canary", 0.01), ("early", 0.10), ("half", 0.50), ("full", 1.0))

    def __init__(self, version: str, previous: str, *, health: Callable[[str, float], Mapping[str, float]],
                 max_error_rate: float = 0.01, max_p99: float = 1.0, audit: Callable[..., Any] | None = None) -> None:
        self.version, self.previous, self.health = version, previous, health
        self.max_error_rate, self.max_p99 = max_error_rate, max_p99
        self.audit = audit or (lambda *a, **k: None)
        self.history: list[dict[str, Any]] = []
        self.disabled = False

    def emergency_disable(self, actor: str, reason: str) -> None:
        self.disabled = True
        self.audit("rollout.disable", actor, {"version": self.version, "reason": reason})

    def run(self) -> dict[str, Any]:
        for stage, fraction in self.STAGES:
            if self.disabled:
                return self._rollback("emergency disable")
            h = self.health(stage, fraction)
            rec = {"stage": stage, "fraction": fraction, **h}
            self.history.append(rec)
            if h.get("error_rate", 1) > self.max_error_rate or h.get("p99", 1e9) > self.max_p99 or h.get("drift", 0) > 0:
                return self._rollback(f"health gate failed at {stage}")
        return {"result": "promoted", "version": self.version, "history": self.history}

    def _rollback(self, why: str) -> dict[str, Any]:
        self.audit("rollout.rollback", "controller", {"from": self.version, "to": self.previous, "why": why})
        return {"result": "rolled_back", "version": self.previous, "reason": why, "history": self.history}


# --------------------------------------------------------------------- gate
def production_gate(*, checklist_status: Mapping[str, Any], readiness: Mapping[str, Any], evidence_ok: bool, tests_ok: bool, slo_ok: bool) -> dict[str, Any]:
    blockers, conditions = [], []
    if not tests_ok:
        blockers.append("test suite failing")
    if not evidence_ok:
        blockers.append("acceptance evidence missing or unverifiable")
    if not slo_ok:
        blockers.append("reference SLO thresholds violated")
    for item in readiness.get("items", []):
        if item["status"] in ("blocked", "external"):
            blockers.append(f"{item['id']}: {item['title']} ({item['status']})")
        elif item["status"] in ("owner-required", "draft"):
            conditions.append(f"{item['id']}: {item['title']} ({item['status']})")
    totals = checklist_status.get("totals", {})
    open_checks = totals.get("open", 0) + totals.get("owner-required", 0) + totals.get("external", 0)
    if open_checks:
        conditions.append(f"{open_checks} checklist controls not yet evidenced")
    verdict = "NO_GO" if blockers else ("CONDITIONAL_GO" if conditions else "GO")
    return {"schema": GATE_SCHEMA, "verdict": verdict, "blockers": blockers, "conditions": conditions, "checklist_totals": dict(totals)}
