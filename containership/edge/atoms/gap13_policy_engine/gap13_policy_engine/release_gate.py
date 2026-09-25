"""G13-MC-040 release regression gate and G13-MC-050 production-exit gate.

python -m gap13_policy_engine.release_gate --profile rc|production [--evidence DIR] [--manifest PATH]

``rc``: engineering regression gate (tests, skips vs approved waivers, performance
vs baseline and ceilings, overload shedding, fixture/golden drift, version
consistency, evidence integrity, secret scan, requirement coverage).
``production``: rc + governance (components DONE or approved-waived, owners
assigned, ADR accepted, P0 all DONE).  Result is written next to the manifest
and bound to its digest; the gate never approves anything by itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

from . import __version__
from .certify import PKG, verify_manifest, manifest_digest

GO, COND, NO = "GO", "CONDITIONAL_GO", "NO_GO"


def _get(d, dotted):
    for part in dotted.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(part)
    return d


def _today():
    return dt.date.today().isoformat()


def evaluate(manifest: dict, *, profile: str = "rc", root: Path = PKG, manifest_path: Path | None = None) -> dict:
    th = json.loads((root / "ops" / "release_gate.json").read_text())
    base = json.loads((root / "ops" / "perf_baseline.json").read_text()) if (root / "ops" / "perf_baseline.json").exists() else None
    waivers = {w["id"]: w for w in manifest.get("waivers", [])}
    approved = {i: w for i, w in waivers.items() if w.get("status") == "APPROVED" and w.get("expires", "") >= _today()}
    checks, blocking, conditional = [], [], []

    def check(name, ok, detail="", *, severity="blocking", waiver_component=None):
        if not ok and waiver_component:
            w = next((w for w in approved.values() if w["component"] == waiver_component), None)
            if w:
                checks.append({"check": name, "result": "waived", "waiver": w["id"], "detail": detail})
                conditional.append(name)
                return
        checks.append({"check": name, "result": "pass" if ok else "fail", "detail": detail})
        if not ok:
            (blocking if severity == "blocking" else conditional).append(name)

    # evidence integrity -------------------------------------------------------------------
    check("manifest digest", manifest_digest(manifest) == manifest.get("manifest_digest"))
    if manifest_path is not None:
        ok, problems = verify_manifest(manifest_path, root=root)
        check("evidence bound to exact artifact bytes", ok, "; ".join(problems[:10]))
    check("release version matches evidence", manifest.get("release") == __version__,
          f"{manifest.get('release')} vs {__version__}")
    check("secret scan clean", not manifest.get("secret_scan"))

    # version consistency ---------------------------------------------------------------------
    v_file = (root / "VERSION").read_text().strip()
    changelog = (root / "CHANGELOG.md").read_text()
    readme = (root / "README.md").read_text()
    check("VERSION / __version__ / CHANGELOG / README consistent",
          v_file == __version__ and f"## {__version__}" in changelog and __version__ in readme)

    # tests ------------------------------------------------------------------------------------
    s = manifest["tests"]["summary"]
    check("no failing tests", s["fail"] <= th["tests"]["max_failures"] and s["error"] <= th["tests"]["max_errors"],
          f"fail={s['fail']} error={s['error']}")
    skip_waived = {t for w in waivers.values() for t in w.get("skip_tests", [])}
    skips = [tid for tid, o in manifest["tests"]["results"].items() if o["status"] == "skip"]
    unexplained = [t for t in skips if not any(t.startswith(p) for p in skip_waived)]
    check("no unexplained skips", len(unexplained) <= th["tests"]["unexplained_skips_allowed"], ", ".join(unexplained[:5]))
    skip_waivers = [w for w in waivers.values() if w.get("skip_tests")]
    for w in skip_waivers:
        hit = [t for t in skips if any(t.startswith(p) for p in w["skip_tests"])]
        if hit:
            if w["id"] in approved:
                checks.append({"check": f"skips covered by {w['id']}", "result": "waived", "waiver": w["id"]})
                conditional.append(f"skips covered by {w['id']}")
            else:
                checks.append({"check": f"skips covered by {w['id']}", "result": "fail",
                               "detail": f"waiver {w['id']} is {w.get('status')}; skip treated as not-passed"})
                blocking.append(f"skips covered by {w['id']}")

    # golden fixtures / schemas are exercised by tests; make it explicit ----------------------
    gold = [t for t in manifest["tests"]["results"] if "GoldenTests" in t or "SchemaArtifactTests" in t]
    check("schema golden fixtures validated", bool(gold) and all(manifest["tests"]["results"][t]["status"] == "pass" for t in gold))

    # requirements -------------------------------------------------------------------------------
    req = manifest.get("requirements", {})
    bad = [r for r, v in req.items() if v["status"] != "pass"]
    check("every SHALL requirement has passing evidence", not bad, ", ".join(bad))

    # performance ----------------------------------------------------------------------------------
    b = manifest["benchmark"]
    for metric, ceiling in {**th["perf"]["absolute_ceilings_ms"], **th["perf"]["load_ceiling_ms"]}.items():
        val = _get(b, metric)
        if val is None:
            checks.append({"check": f"perf ceiling {metric}", "result": "not-measured",
                           "detail": f"benchmark profile {manifest.get('benchmark_profile')}"})
            if profile == "production":
                blocking.append(f"perf ceiling {metric} not measured (run certify --full)")
            continue
        check(f"perf ceiling {metric} <= {ceiling}", val <= ceiling, f"{val}")
    if base:
        for metric in th["perf"]["metrics"]:
            val, ref = _get(b, metric), _get(base, metric)
            if val is not None and ref:
                check(f"perf regression {metric}", val <= ref * th["perf"]["tolerance_ratio"],
                      f"{val} vs baseline {ref} (x{th['perf']['tolerance_ratio']})")
    ov = b.get("overload", {})
    check("overload sheds and never hangs", (ov.get("shed", 0) > 0 or not th["overload"]["require_shed"])
          and ov.get("hung_threads", 1) <= th["overload"]["max_hung_threads"], json.dumps(ov))

    # production governance ---------------------------------------------------------------------------
    if profile == "production":
        comps = manifest["components"]
        prio = {c["id"]: c["priority"] for c in json.loads((root / "COMPONENT_STATUS.json").read_text())["components"]}
        for cid, c in comps.items():
            if c["status"] == "DONE":
                continue
            pri = prio[cid]
            if pri == 0 and not th["production"]["p0_waivers_allowed"]:
                check(f"{cid} accepted (P0)", False, f"status {c['status']}")
            else:
                check(f"{cid} accepted", False, f"status {c['status']}", waiver_component=cid)
        owners = (root / "docs" / "OWNERS.yaml").read_text()
        check("owners assigned", "UNASSIGNED" not in owners, f"{owners.count('UNASSIGNED')} unassigned role fields")
        adr = (root / "docs" / "ADR-001-evaluator-architecture.md").read_text()
        check("ADR-001 accepted", re.search(r"\*\*Status:\*\*\s*Accepted", adr) is not None)

    verdict = NO if blocking else COND if conditional else GO
    return {"schema": "PK_POLICY_GATE_RESULT/1", "profile": profile, "release": __version__,
            "manifest_digest": manifest.get("manifest_digest"), "verdict": verdict,
            "blocking": blocking, "conditional": conditional, "checks": checks,
            "evaluated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=("rc", "production"), default="rc")
    ap.add_argument("--evidence", default=str(PKG.parent / "evidence"))
    ap.add_argument("--manifest")
    a = ap.parse_args(argv)
    mpath = Path(a.manifest) if a.manifest else Path(a.evidence) / __version__ / "manifest.json"
    if not mpath.exists():
        print(json.dumps({"verdict": NO, "blocking": [f"evidence manifest missing: {mpath}"]}))
        return 2
    m = json.loads(mpath.read_text())
    res = evaluate(m, profile=a.profile, manifest_path=mpath)
    out = mpath.parent / f"gate_{a.profile}.json"
    out.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({"verdict": res["verdict"], "blocking": res["blocking"], "conditional": res["conditional"],
                      "result": str(out)}, indent=2))
    return 0 if res["verdict"] != NO else 1


if __name__ == "__main__":
    raise SystemExit(main())
