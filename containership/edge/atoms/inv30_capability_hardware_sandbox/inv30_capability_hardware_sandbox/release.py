# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Release evidence generator and formal production exit gate (GAP-060, GAP-069, GAP-047).

``python -m pk_components.inv30_capability_hardware_sandbox.release --out evidence/``

Runs every suite as a subprocess (normal and ``python -O``), records pass/fail/
skip counts, binds everything to the package tree digest, and evaluates the exit
gate. Policy (no exceptions):

* a MANDATORY suite that skipped any test is **not passed** (it is BLOCKED);
* a zero-budget invariant failure is NO_GO and has no waiver path;
* the hardware-conformance suite is mandatory for a *hardware* production claim;
  without it the best achievable verdict is ``GO_MODEL_ONLY`` for workloads that
  do not require the hardware tier, and ``NO_GO`` for the hardware tier;
* human sign-offs (owner, independent reviewer) are read from
  ``evidence/SIGNOFFS.json``; missing sign-offs are conditions, never passes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import bench, integrity
from .deps import pk_core_status
from .discovery import environment_report

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent.parent  # folder holding pk_core and pk_components

SUITES = [
    # name, module pattern, mandatory, zero_budget
    ("model-core", "test_capability_core", True, True),
    ("model-properties", "test_properties", True, True),
    ("concurrency", "test_concurrency", True, True),
    ("contracts", "test_contracts", True, False),
    ("security-adversarial", "test_security", True, True),
    ("service", "test_service", True, False),
    ("resilience-faults", "test_resilience", True, False),
    ("config-supplychain", "test_config_integrity", True, False),
    ("ops-tooling", "test_ops", True, False),
    ("framework-conformance", "test_component", True, False),
    ("framework-integration", "test_framework_integration", True, False),
    ("hardware-conformance", "test_hardware_backend", False, True),  # mandatory only for hardware claims
]
_RAN = re.compile(r"Ran (\d+) tests?")
_SUM = re.compile(r"(failures|errors|skipped|expected failures|unexpected successes)=(\d+)")


def run_suite(module: str, optimized: bool) -> dict:
    cmd = [sys.executable] + (["-O"] if optimized else []) + [
        "-m", "unittest", "-v", f"pk_components.{PKG.name}.tests.{module}"]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
    out = p.stderr + p.stdout
    ran = int(_RAN.search(out).group(1)) if _RAN.search(out) else 0
    counts = {k: int(v) for k, v in _SUM.findall(out)}
    skipped = counts.get("skipped", 0)
    failed = counts.get("failures", 0) + counts.get("errors", 0) + counts.get("unexpected successes", 0)
    if p.returncode != 0 and failed == 0:
        failed = 1
    return {"ran": ran, "passed": ran - failed - skipped - counts.get("expected failures", 0),
            "failed": failed, "skipped": skipped, "returncode": p.returncode,
            "skip_reasons": sorted(set(re.findall(r"skipped '([^']+)'", out)))}


def git_rev() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "no-vcs"
    except OSError:
        return "no-vcs"


def expired_waivers(today: str | None = None) -> list[str]:
    w = json.loads((PKG / "WAIVERS.json").read_text(encoding="utf-8"))
    today = today or dt.date.today().isoformat()
    out = [f"waiver {x['id']} expired {x['expires']}" for x in w.get("approved_waivers", []) if x["expires"] < today]
    out += [f"waiver {x['id']} targets unwaivable class" for x in w.get("approved_waivers", [])
            if x.get("constraint_class") in w["rules"]["unwaivable_classes"]]
    return out


def evaluate(suites: dict, bench_fail: list[str], signoffs: dict, env: dict, license_bad: list[str],
             waiver_problems: list[str] | None = None, secret_hits: list[str] | None = None) -> dict:
    blockers, conditions, invariant_fail = list(waiver_problems or []), [], []
    if secret_hits:
        blockers.append(f"secret scan hits: {secret_hits[:5]}")
    for name, (mod, mandatory, zero) in {s[0]: s[1:] for s in SUITES}.items():
        for mode in ("normal", "optimized"):
            r = suites[name][mode]
            if r["failed"]:
                (invariant_fail if zero else blockers).append(f"{name}[{mode}]: {r['failed']} failed")
            elif mandatory and (r["skipped"] or r["ran"] == 0):
                blockers.append(f"{name}[{mode}]: mandatory suite skipped {r['skipped']} / ran {r['ran']} "
                                f"({'; '.join(r['skip_reasons']) or 'no tests ran'})")
    if bench_fail:
        blockers += [f"perf-regression: {f}" for f in bench_fail]
    if license_bad:
        blockers.append(f"license headers missing: {license_bad[:5]}")
    hw = suites["hardware-conformance"]
    hw_ok = all(hw[m]["ran"] > 0 and hw[m]["skipped"] == 0 and hw[m]["failed"] == 0 for m in ("normal", "optimized"))
    for role in ("owner", "security_reviewer", "independent_verifier"):
        s = signoffs.get(role)
        if not s or not s.get("name") or not s.get("date"):
            conditions.append(f"sign-off missing: {role}")
    if invariant_fail:
        verdict = "NO_GO"
    elif blockers:
        verdict = "NO_GO"
    elif not hw_ok:
        verdict = "GO_MODEL_ONLY" if not conditions else "CONDITIONAL_GO_MODEL_ONLY"
    else:
        verdict = "GO" if not conditions else "CONDITIONAL_GO"
    return {"verdict": verdict,
            "hardware_tier_verdict": "GO" if hw_ok and not invariant_fail and not blockers else "NO_GO",
            "hardware_tier_reason": "hardware-conformance suite passed on a CHERI backend" if hw_ok else
            f"no CHERI backend evidence: {env['cheri']['state']} ({env['cheri']['signal']})",
            "zero_budget_invariant_failures": invariant_fail, "blockers": blockers, "conditions": conditions,
            "waivable": {"zero_budget_invariant_failures": False}}


def generate(out_dir: Path, *, iterations: int = 2000) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    man = integrity.manifest()
    suites = {}
    for name, module, *_ in SUITES:
        suites[name] = {"normal": run_suite(module, False), "optimized": run_suite(module, True)}
    b = bench.run(iterations=iterations)
    bench_fail = bench.regression(b)
    env = environment_report()
    sign_path = PKG / "evidence" / "SIGNOFFS.json"
    signoffs = json.loads(sign_path.read_text(encoding="utf-8")).get("signoffs", {}) if sign_path.exists() else {}
    lic = integrity.license_check()
    gate = evaluate(suites, bench_fail, signoffs, env, lic, expired_waivers(), integrity.secret_scan())
    pk = pk_core_status()
    evidence = {
        "schema": "INV30_RELEASE_EVIDENCE/1",
        "element": "INV-30", "version": __version__,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": f"inv30.release {__version__}", "python": sys.version.split()[0],
        "source_revision": git_rev(), "tree_digest": man["tree_digest"],
        "environment": env, "suites": suites,
        "benchmark": {k: v for k, v in b.items() if k != "raw_us"}, "benchmark_regressions": bench_fail,
        "benchmark_raw_ref": "BENCH_RAW.json", "schema_digests": {p.name: integrity.sha256(p)
                                                                 for p in sorted((PKG / "schemas").glob("*.json"))},
        "traceability_ref": "../docs/TRACEABILITY.json", "waivers_ref": "../WAIVERS.json",
        "sbom_ref": "SBOM.cdx.json", "manifest_ref": "MANIFEST.sha256.json",
        "gate": gate,
    }
    (out_dir / "MANIFEST.sha256.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    (out_dir / "SBOM.cdx.json").write_text(json.dumps(
        integrity.sbom(__version__, pk["version"], integrity.pk_core_digest()), indent=1))
    (out_dir / "RELEASE_EVIDENCE.json").write_text(json.dumps(evidence, indent=1, sort_keys=True))
    (out_dir / "ENVIRONMENT.json").write_text(json.dumps(env, indent=1, sort_keys=True))
    (out_dir / "BENCH_RAW.json").write_text(json.dumps({"seed": b["seed"], "raw_us": b["raw_us"]}))
    if not (out_dir / "BENCH_BASELINE.json").exists():
        (out_dir / "BENCH_BASELINE.json").write_text(json.dumps(evidence["benchmark"], indent=1))
    (out_dir / "GATE_SUMMARY.md").write_text(summary(evidence))
    return evidence


def summary(ev: dict) -> str:
    g = ev["gate"]
    rows = "\n".join(f"| {n} | {s['normal']['passed']}/{s['normal']['ran']} | {s['normal']['skipped']} | "
                     f"{s['optimized']['passed']}/{s['optimized']['ran']} | {s['optimized']['skipped']} |"
                     for n, s in sorted(ev["suites"].items()))
    return (f"# INV-30 {ev['version']} exit gate — {g['verdict']}\n\n"
            f"* Generated {ev['generated_at']} · tree `{ev['tree_digest']}` · source `{ev['source_revision']}`\n"
            f"* Hardware tier: **{g['hardware_tier_verdict']}** — {g['hardware_tier_reason']}\n"
            f"* Zero-budget invariant failures: {len(g['zero_budget_invariant_failures'])} (unwaivable)\n"
            f"* Blockers: {g['blockers'] or 'none'}\n* Conditions: {g['conditions'] or 'none'}\n"
            f"* Benchmark regressions: {ev['benchmark_regressions'] or 'none'}\n\n"
            "| Suite | normal pass/ran | skipped | -O pass/ran | skipped |\n|---|---|---|---|---|\n" + rows + "\n")


def verify_offline(evidence_dir: Path) -> list[str]:
    """Independent/offline check: evidence is bound to *this* tree and self-consistent."""
    ev = json.loads((evidence_dir / "RELEASE_EVIDENCE.json").read_text())
    man = json.loads((evidence_dir / "MANIFEST.sha256.json").read_text())
    probs = integrity.verify_tree(PKG, man)
    if man["tree_digest"] != ev["tree_digest"]:
        probs.append("manifest/evidence tree digest mismatch")
    if integrity.manifest()["tree_digest"] != ev["tree_digest"]:
        probs.append("package tree differs from the evidenced tree")
    return probs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv30-release")
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--iterations", type=int, default=2000)
    a = ap.parse_args(argv)
    if a.verify:
        probs = verify_offline(Path(a.out))
        print(json.dumps({"verified": not probs, "problems": probs}, indent=1))
        return 0 if not probs else 1
    ev = generate(Path(a.out), iterations=a.iterations)
    print(json.dumps(ev["gate"], indent=1))
    return 0 if ev["gate"]["verdict"] in ("GO", "GO_MODEL_ONLY", "CONDITIONAL_GO", "CONDITIONAL_GO_MODEL_ONLY") else 3


if __name__ == "__main__":
    raise SystemExit(main())
