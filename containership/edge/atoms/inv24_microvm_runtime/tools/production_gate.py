"""MC-064 formal production exit gate.

Deterministic: identical inputs produce byte-identical output (no wall-clock
fields other than those copied from inputs; ``--now`` pins the freshness
clock).  The overall verdict is computed, never read from any file, so a
human-edited verdict cannot bypass failed inputs.  ``--verify`` recomputes the
gate and checks the stored result and its digest.

Verdicts: GO (every mandatory check passes and every component meets its
priority requirement) | CONDITIONAL_GO (only P1/P2 items rely on valid,
unexpired waivers) | NO_GO (anything else).
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def load(rel: str):
    return json.loads((ROOT / rel).read_text())


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def parse_ts(s: str) -> float:
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def evaluate(now: float) -> dict:
    from run_evidence import source_digest  # same digest definition as the evidence producer
    policy = load("release/PRODUCTION_EXIT_GATE.json")
    status = load("release/COMPONENT_STATUS.json")["components"]
    trace = load("traceability/TRACEABILITY.json")["components"]
    tests = load("evidence/test-results.json")
    digests = load("evidence/artifact-digests.json")
    opt = load("evidence/optimized-mode.json")
    bench = load("evidence/benchmarks.json")
    manifest = load("artifacts/firecracker/manifest.json")
    waivers = load("release/WAIVERS.json")
    checks: dict[str, dict] = {}

    def check(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}

    version = (ROOT / "inv24_microvm_runtime/VERSION").read_text().strip()
    init_v = re.search(r'__version__ = "([^"]+)"', (ROOT / "inv24_microvm_runtime/__init__.py").read_text()).group(1)
    py_v = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    seen = {"VERSION": version, "__init__": init_v, "pyproject": py_v, "compatibility": load("release/compatibility.json")["release"],
            "status": load("release/COMPONENT_STATUS.json")["release"], "trace": load("traceability/TRACEABILITY.json")["release"],
            "evidence": tests["release_version"], "digests": digests["release_version"], "sbom": load("evidence/sbom.json")["release"]}
    check("version_consistency", len(set(seen.values())) == 1, seen)
    age_h = (now - parse_ts(tests["ended_at"])) / 3600
    check("evidence_fresh", 0 <= age_h <= policy["evidence_max_age_hours"], {"age_hours": round(age_h, 2)})
    ledger_ok = all(json.loads(l)["evidence_sha256"] == sha("evidence/test-results.json")
                    for l in (ROOT / "evidence/evidence-ledger.jsonl").read_text().splitlines() if l)
    check("evidence_hashes", ledger_ok, "ledger evidence_sha256 == sha256(test-results.json)")
    cur = source_digest()
    check("evidence_bound_to_source", cur == digests["source_tree_sha256"],
          {"evidence": digests["source_tree_sha256"][:16], "current": cur[:16], "commit": digests["source_commit"]})
    check("no_failed_tests", tests["counts"]["FAIL"] == 0, tests["counts"])
    nt = sorted(t for t, r in tests["tests"].items() if r["result"] == "NOT_TESTED")
    check("skips_not_counted_as_pass", not nt, {"not_tested": nt})
    check("optimized_mode_pass", opt["result"] == "PASS", opt["summary"])
    bad_bench = {k: v["result"] for k, v in bench["verdicts"].items() if v["result"] != "PASS"}
    check("benchmark_gate", not bad_bench, bad_bench)
    unpinned = [a["name"] for a in manifest["artifacts"] if not a.get("sha256")]
    check("artifacts_pinned", not unpinned, {"unpinned": unpinned})
    no_owner = sorted(mc for mc, s in status.items() if not s.get("owner") or not s.get("approver"))
    check("owners_assigned", not no_owner, {"missing_owner_or_approver": len(no_owner)})
    unresolved = sorted(mc for mc, t in trace.items() if not t["artifacts_resolved"])
    check("traceability_resolved", not unresolved and len(trace) == 64, {"components": len(trace), "unresolved": unresolved})
    valid_waivers, bad_waivers = {}, []
    for w in waivers["waivers"]:
        ok = all(w.get(k) for k in ("id", "component", "owner", "approver", "rationale", "expires", "compensating_controls"))
        if ok and parse_ts(w["expires"]) > now:
            valid_waivers[w["component"]] = w["id"]
        else:
            bad_waivers.append(w.get("id"))
    check("waivers_valid", not bad_waivers, {"invalid_or_expired": bad_waivers})

    failed_components, conditional = [], []
    for mc, s in sorted(status.items()):
        allowed = policy["require"][s["priority"]]
        st = "WAIVED" if mc in valid_waivers and s["status"] != "PASS" else s["status"]
        if st not in allowed:
            failed_components.append({"id": mc, "priority": s["priority"], "status": s["status"],
                                      "local_verification": s["local_verification"], "blocked_on": s["blocked_on"]})
        elif st == "WAIVED":
            conditional.append({"id": mc, "waiver": valid_waivers[mc]})
    check("component_status", not failed_components, {"failing": len(failed_components)})

    by_pri = {}
    for f in failed_components:
        by_pri[f["priority"]] = by_pri.get(f["priority"], 0) + 1
    domains = {d: {"failing": sorted(set(ids) & {f["id"] for f in failed_components})} for d, ids in policy["domains"].items()}
    failed_checks = sorted(k for k in policy["mandatory_checks"] if not checks[k]["pass"])
    verdict = "NO_GO" if failed_checks else ("CONDITIONAL_GO" if conditional else "GO")
    local = {}
    for s in status.values():
        local[s["local_verification"]] = local.get(s["local_verification"], 0) + 1
    result = {"schema": "PK_MICROVM_GATE_RESULT/1", "release": version, "source_commit": digests["source_commit"],
              "source_tree_sha256": digests["source_tree_sha256"], "policy_sha256": sha("release/PRODUCTION_EXIT_GATE.json"),
              "evidence_ended_at": tests["ended_at"], "verdict": verdict, "failed_checks": failed_checks,
              "checks": checks, "failing_components_by_priority": by_pri, "failing_components": failed_components,
              "conditional": conditional, "domains": domains, "local_verification_summary": local}
    body = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["result_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/production-gate.json")
    ap.add_argument("--now", help="pin evaluation clock, YYYY-MM-DDTHH:MM:SSZ")
    ap.add_argument("--verify", metavar="RESULT")
    a = ap.parse_args()
    if a.verify:
        stored = json.loads((ROOT / a.verify).read_text())
        claimed = stored.pop("result_sha256")
        body = json.dumps(stored, sort_keys=True, separators=(",", ":"))
        ok_digest = hashlib.sha256(body.encode()).hexdigest() == claimed
        fresh = evaluate(parse_ts(stored["evidence_ended_at"]) + 1)
        same = fresh["verdict"] == stored["verdict"] and fresh["failed_checks"] == stored["failed_checks"] \
            and fresh["source_tree_sha256"] == stored["source_tree_sha256"]
        print(json.dumps({"digest_ok": ok_digest, "recomputed_matches": same, "verdict": stored["verdict"]}))
        return 0 if ok_digest and same else 2
    now = parse_ts(a.now) if a.now else time.time()
    res = evaluate(now)
    (ROOT / a.out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": res["verdict"], "failed_checks": res["failed_checks"],
                      "failing_components_by_priority": res["failing_components_by_priority"]}, indent=1))
    return 0 if res["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
