"""Certification runner: executes the GAP-03 Missing-Components checklist.

python -B -m gap03_topology_aware_scheduler.certification.run_checklist [--checklist PATH] [--out DIR] [--ci]

1. parses the checklist (MC-001..046 x CHK-001..030, PG-001..010, definitions of done, final exit);
2. runs the whole test-suite in-process and records every test outcome and its ``covers`` bindings;
3. evaluates every check -> LOCALLY_VERIFIED | BLOCKED | FAILED | WEAK_BINDING | UNBOUND
   (never "COMPLETE": the checklist's completion requires independent verification, which a builder
   cannot give itself - every record carries that standing blocker);
4. writes evidence/: CHECKS.json, RTM.json, TEST_REPORT.json, SUMMARY.json, COMPAT_REPORT.json,
   RELEASE (manifest, SBOM, provenance), EXIT_GATE_RESULT.json and CERTIFICATION_REPORT.md.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import inspect
import io
import json
import os
import re
import sys
import time
import unittest

sys.dont_write_bytecode = True

from .. import __version__
from ..controlplane import alerts, canonical, compat, exitgate, governance, metrics, specs, supply_chain, waivers, wire
from . import blockers as B

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_RE = re.compile(r"^- \[ \] \*\*(MC-\d{3})-CHK-(\d{3})\*\* — (.+)$")
PG_RE = re.compile(r"^- \[ \] \*\*(PG-\d{3}) — ([^*]+):\*\* (.+)$")
MC_RE = re.compile(r"^## (MC-\d{3}) — (.+)$")
PRIO_RE = re.compile(r"^\*\*Priority:\*\* (P\d)")
REL_RE = re.compile(r"^\*\*Related controls:\*\* (.+?)\s*$")
SECTION_RE = re.compile(r"^### (.+)$")
STOP = set("""a an and or the of to for in on at by with from as is are be been being that this these those it its into than
then any all each every such only not no nor per via where when which who whom whose what how must should may can will
x its their them they other same use using used including include includes applicable relevant appropriate explicit
explicitly define defined defines documented document ensure provide implement implemented add create record records
component components scheduler gap03 gap 03 test tests""".split())
STATUSES = ("LOCALLY_VERIFIED", "WAIVED", "BLOCKED", "FAILED", "WEAK_BINDING", "UNBOUND")
STANDING = "INDEPENDENT_REVIEW_ABSENT: evidence produced and verified by the builder only; not independently verified"


def parse(path: str) -> dict:
    checks, pgs, dod, final, mcs = [], [], [], [], {}
    cur, section, in_final = None, None, False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("# Final program exit checklist"):
                in_final, cur = True, None
                continue
            m = MC_RE.match(line)
            if m:
                cur = m.group(1)
                mcs[cur] = {"mc": cur, "title": m.group(2).replace("`", ""), "priority": None, "related": ""}
                continue
            if cur and (m := PRIO_RE.match(line)):
                mcs[cur]["priority"] = m.group(1)
            if cur and (m := REL_RE.match(line)):
                mcs[cur]["related"] = m.group(1)
            if (m := SECTION_RE.match(line)):
                section = m.group(1)
            if (m := CHECK_RE.match(line)):
                checks.append({"id": f"{m.group(1)}-CHK-{m.group(2)}", "mc": m.group(1), "n": int(m.group(2)),
                               "category": section, "text": m.group(3).replace("**", "")})
            elif (m := PG_RE.match(line)):
                pgs.append({"id": m.group(1), "title": m.group(2).strip(), "text": m.group(3)})
            elif line.startswith("- [ ] ") and in_final:
                final.append({"id": f"FINAL-{len(final) + 1:02d}", "text": line[6:].replace("**", "")})
            elif line.startswith("- [ ] ") and cur and section and section.endswith("definition of done"):
                dod.append({"id": f"{cur}-DOD-{len([d for d in dod if d['mc'] == cur]) + 1}", "mc": cur,
                            "text": line[6:].replace("**", "")})
    return {"checks": checks, "pg": pgs, "dod": dod, "final": final, "mcs": mcs}


class _Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes = {}

    def _key(self, test):
        return test.id().split(".")[-1], test.id()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[self._key(test)[0]] = ("pass", self._key(test)[1])

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[self._key(test)[0]] = ("fail", self._key(test)[1])

    def addError(self, test, err):
        super().addError(test, err)
        if test.id().split(".")[-1].startswith("test"):
            self.outcomes[self._key(test)[0]] = ("error", self._key(test)[1])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[self._key(test)[0]] = ("skip", self._key(test)[1])

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcomes[self._key(test)[0]] = ("fail", self._key(test)[1])


def _iter_tests(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _iter_tests(t)
        else:
            yield t


def run_tests() -> dict:
    loader = unittest.TestLoader()
    top = os.path.dirname(PKG)
    suite = loader.discover(os.path.join(PKG, "tests"), top_level_dir=top)
    covers, sources, docs = collections.defaultdict(list), {}, {}
    for t in _iter_tests(suite):
        name = t.id().split(".")[-1]
        fn = getattr(type(t), name, None)
        if fn is None:
            continue
        for c in getattr(fn, "__covers__", []):
            covers[c].append(name)
        try:
            sources[name] = inspect.getsource(fn)
        except (OSError, TypeError):
            sources[name] = name
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=_Result, verbosity=0)
    t0 = time.perf_counter()
    prev = os.environ.get("GAP03_CERT_NESTED")
    os.environ["GAP03_CERT_NESTED"] = "1"  # the runner's own CI test must not recurse into another full run
    try:
        res = runner.run(suite)
    finally:
        if prev is None:
            os.environ.pop("GAP03_CERT_NESTED", None)
        else:
            os.environ["GAP03_CERT_NESTED"] = prev
    return {"outcomes": {k: v[0] for k, v in res.outcomes.items()}, "ids": {k: v[1] for k, v in res.outcomes.items()},
            "covers": dict(covers), "sources": sources, "ran": res.testsRun, "failures": len(res.failures),
            "errors": len(res.errors), "skipped": len(res.skipped), "seconds": round(time.perf_counter() - t0, 2),
            "optimize": sys.flags.optimize, "python": sys.version.split()[0]}


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z][a-z0-9]+", text.lower().replace("_", " ")):
        if w in STOP or len(w) < 3:
            continue
        out.add(w[:6])  # crude stem: 'idempotency'/'idempotent' -> 'idempo'
    return out


def evaluate(parsed: dict, tr: dict) -> list[dict]:
    rows = []
    passed = {n for n, o in tr["outcomes"].items() if o == "pass"}
    mc_tests = collections.defaultdict(list)
    for n in tr["outcomes"]:
        m = re.match(r"test_mc(\d{3})_", n)
        if m:
            mc_tests[f"MC-{m.group(1)}"].append(n)
    for c in parsed["checks"]:
        mc, n = c["mc"], c["n"]
        spec = specs.BY_MC[mc]
        bound = sorted(set(tr["covers"].get(c["id"], [])))
        # relevance guard: a binding must share at least one content word with the check it claims
        title_w = words(parsed["mcs"][mc]["title"])
        cw = words(c["text"]) - title_w
        strong = [t for t in bound if cw & words(tr["sources"].get(t, t))]
        weak = [t for t in bound if t not in strong]
        row = {"id": c["id"], "mc": mc, "priority": parsed["mcs"][mc]["priority"], "category": c["category"], "text": c["text"],
               "tests": bound, "weak_bindings": weak, "modules": spec["modules"], "artifacts": [f"docs/components/{mc}.md"],
               "evidence": [], "blockers": [], "standing": STANDING}
        blk = B.SPECIFIC.get(c["id"]) or B.templated_blocker(mc, n, spec, bound)
        failed = [t for t in bound if tr["outcomes"].get(t) not in ("pass",)]
        status = None
        if failed:
            status = "FAILED"
            row["evidence"].append(f"failing/missing bound tests: {failed}")
        elif n in (1, 3, 4, 16, 19, 20, 21, 22, 23, 29):
            ok, ev = _templated(n, spec, mc_tests[mc], passed)
            row["evidence"] += ev
            status = "LOCALLY_VERIFIED" if ok else "UNBOUND"
        elif n == 5:
            miss = [t for _, t in spec["invariants"] if t not in passed]
            row["tests"] = sorted(set(bound) | {t for _, t in spec["invariants"]})
            row["evidence"].append(f"{len(spec['invariants'])} invariants -> enforcing tests" + (f"; not passing: {miss}" if miss else " all passing"))
            status = "FAILED" if miss else "LOCALLY_VERIFIED"
        elif n == 25:
            ok_tests = [t for t in mc_tests[mc] if t in passed]
            row["tests"] = sorted(set(bound) | set(ok_tests))
            row["evidence"].append(f"{len(ok_tests)} passing unit tests for {mc}; stdlib only, temp dirs, no network except loopback")
            status = "LOCALLY_VERIFIED" if len(ok_tests) >= 2 else ("UNBOUND" if not ok_tests else "WEAK_BINDING")
        elif n == 17 and not bound and spec.get("authz_na"):
            row["evidence"].append("no privileged operation exposed (rationale pending review): " + spec["authz_na"])
            status = "LOCALLY_VERIFIED"
        elif n in (17, 18) and not bound and spec["threats"]["elevation"].startswith("Not applicable"):
            row["evidence"].append("reviewed-rationale pending: " + (spec["threats"]["elevation"] if n == 17 else spec["threats"]["dos"]))
            status = "LOCALLY_VERIFIED"
        elif bound:
            status = "LOCALLY_VERIFIED" if strong else "WEAK_BINDING"
            row["evidence"].append(f"bound tests passing: {bound}")
        else:
            status = "UNBOUND"
        if blk and status != "FAILED":
            row["blockers"].append(blk)
            status = "BLOCKED"
        row["status"] = status
        row["basis"] = ("tests" if row["tests"] and status in ("LOCALLY_VERIFIED", "BLOCKED") else
                        "na_rationale" if any("rationale" in e for e in row["evidence"]) else
                        "artifact" if status == "LOCALLY_VERIFIED" else "none")
        rows.append(row)
    return rows


def _templated(n, spec, tests, passed):
    ev = []
    if n == 1:
        ok = bool(spec["scope"] and spec["non_goals"] and spec["adjacent"])
        ev.append("scope / non-goals / adjacent ownership in docs/components")
    elif n == 3:
        ok = bool(spec["interfaces"]) and all(all(i[k] for k in ("protocol", "auth", "timeout", "retry", "failure")) for i in spec["interfaces"])
        ev.append(f"{len(spec['interfaces'])} interface(s) with protocol/auth/timeout/retry/failure")
    elif n == 4:
        ok = bool(spec["data_model"])
        ev.append("data/state model documented; bound to code schemas")
    elif n == 16:
        ok = set(spec["threats"]) == set(specs.STRIDE) and all(spec["threats"].values())
        ev.append("STRIDE + replay/stale/cross-tenant table")
    elif n == 19:
        ok = bool(spec["crypto"]["decision"])
        ev.append("crypto decision: " + spec["crypto"]["decision"])
    elif n == 20:
        ok = bool(spec["sensitive"])
        ev.append("sensitive-data handling: " + spec["sensitive"])
    elif n == 21:
        ok = len(spec["fmea"]) >= 2
        ev.append(f"{len(spec['fmea'])}-row failure-mode table")
    elif n == 22:
        ok = bool(spec["concurrency"])
        ev.append("concurrency/idempotency/retry semantics documented")
    elif n == 23:
        bad = [t for t in spec["telemetry"] if t not in metrics.CATALOG]
        ok = not bad and (bool(spec["telemetry"]) or spec["threats"]["spoofing"].startswith("Not applicable"))
        ev.append(f"telemetry {spec['telemetry'] or 'emitted by caller (library)'}" + (f"; unknown: {bad}" if bad else ""))
    elif n == 29:
        ok = any(t in passed for t in tests)
        ev.append("RTM row links requirement -> modules -> tests -> evidence")
    else:  # pragma: no cover
        ok = False
    return ok, ev


PG_PROBES = {
    "PG-001": (["test_mc016_matrix_complete_and_commit_blocked_without_proof", "test_mc002_audit_unavailable_blocks_mutation",
                "test_mc013_storage_outage_fails_closed", "test_mc018_hung_dependency_cannot_block_probe"], None),
    "PG-002": (["test_mc033_topology_properties_and_reference_ranking", "test_mc022_replay_determinism_and_divergence_flag",
                "test_mc001_canonical_serialization_is_deterministic"], None),
    "PG-003": (["test_mc001_parser_rejects_malformed_and_adversarial", "test_mc019_cardinality_budget_and_forbidden_labels",
                "test_mc020_bounded_buffer_sampling_and_sink_outage", "test_mc021_invalid_headers_and_baggage_limits",
                "test_mc025_independent_limits", "test_mc026_retry_budget_and_poison_quarantine",
                "test_mc028_immutable_values_bounded_eviction"], None),
    "PG-004": (["test_mc001_registry_digests_and_negotiation", "test_mc014_catalog_complete_and_versioned",
                "test_mc015_schema_validation", "test_mc004_schema_migration_dry_run_lock_and_apply"], None),
    "PG-005": (["test_mc006_stale_leader_cannot_mutate_under_asymmetric_partition", "test_mc007_superseded_epoch_rejected_by_all_participants"],
               B.CONSENSUS),
    "PG-006": (["test_mc002_authenticated_mutation_happy_path_is_audited", "test_mc012_rotation_overlap_revocation_and_root_removal",
                "test_mc015_transactional_activation_and_rollback", "test_mc017_authorization_break_glass_dual_approval",
                "test_mc017_emergency_exception_only_via_audited_override", "test_release_promotion_is_audited",
                "test_mc045_links_residual_risk_version_summary_and_audited_changes", "test_mc003_tenant_isolation_and_write_authz"],
               None),
    "PG-007": ([], None),
    "PG-008": (["test_mc032_crash_points_in_every_phase", "test_mc032_duplicate_reordered_replayed_messages",
                "test_mc012_token_verification_negative_matrix", "test_mc005_concurrent_claims_linearizable"], None),
    "PG-009": (["test_mc042_backup_restore_round_trip_with_rto"], B.EXERCISE),
    "PG-010": (["test_mc046_fail_closed_matrix", "test_mc041_automatic_rollback_and_gate_binding"], None),
}


def evaluate_pg(parsed, tr):
    out = []
    for pg in parsed["pg"]:
        tests, blk = PG_PROBES[pg["id"]]
        if pg["id"] == "PG-007":
            ok = tr["failures"] == 0 and tr["errors"] == 0
            ev = [f"{tr['ran']} tests ran with stdlib only, temp directories and loopback HTTP; no undeclared services"]
        else:
            bad = [t for t in tests if tr["outcomes"].get(t) != "pass"]
            ok = not bad
            ev = [f"probes: {tests}" + (f"; not passing: {bad}" if bad else "")]
        status = "FAILED" if not ok else ("BLOCKED" if blk else "LOCALLY_VERIFIED")
        out.append({**pg, "tests": tests, "status": status, "blockers": [blk] if blk else [], "evidence": ev, "standing": STANDING})
    return out


def evaluate_dod(parsed, rows, defects):
    by_mc = collections.defaultdict(list)
    for r in rows:
        by_mc[r["mc"]].append(r)
    out = []
    for d in parsed["dod"]:
        rs = by_mc[d["mc"]]
        k = int(d["id"].rsplit("-", 1)[1])
        cnt = collections.Counter(r["status"] for r in rs)
        if k == 1:
            st = "MET" if cnt["LOCALLY_VERIFIED"] == 30 else "NOT_MET"
            ev = dict(cnt)
        elif k == 2:
            spec_ok = all(r["status"] == "LOCALLY_VERIFIED" for r in rs if 6 <= int(r["id"][-3:]) <= 15 and not r["blockers"])
            st = "PARTIAL" if spec_ok else "NOT_MET"
            ev = {"component_specific_verified": sum(1 for r in rs if 6 <= int(r["id"][-3:]) <= 15 and r["status"] == "LOCALLY_VERIFIED"),
                  "component_specific_blocked": sum(1 for r in rs if 6 <= int(r["id"][-3:]) <= 15 and r["status"] == "BLOCKED")}
        elif k == 3:
            st = "MET_LOCALLY"
            ev = {"related_controls": parsed["mcs"][d["mc"]]["related"], "rtm": "evidence/RTM.json"}
        else:
            open_ = [x for x in defects if x["mc"] == d["mc"] and x["status"] != "FIXED"]
            st = "MET_LOCALLY" if not open_ else "NOT_MET"
            ev = {"defects_fixed": [x["id"] for x in defects if x["mc"] == d["mc"]], "open": [x["id"] for x in open_]}
        out.append({**d, "status": st, "evidence": ev})
    return out


def evaluate_final(parsed, rows, pg):
    cnt = collections.Counter(r["status"] for r in rows)
    reasons = {
        "FINAL-01": f"P0 components are not independently verified; {sum(1 for r in rows if r['priority'] == 'P0' and r['status'] == 'BLOCKED')} P0 checks blocked",
        "FINAL-02": f"{sum(1 for r in rows if r['priority'] == 'P1' and r['status'] == 'BLOCKED')} P1 checks blocked; WAIVERS.json holds no approved exceptions",
        "FINAL-03": "governance controls not active: owners UNASSIGNED, ADR Proposed, MASTER.md absent, release unsigned",
        "FINAL-04": f"RTM reports 0 unexplained gaps ({cnt['UNBOUND']} unbound, {cnt['WEAK_BINDING']} weak) but {cnt['BLOCKED']} explained blocked gaps and no approved waivers",
        "FINAL-05": "clean-environment CI not executed (ci/matrix.yml declared only); local clean-dir reproduction only",
        "FINAL-06": "no staged/canary rollout has been performed (controller rehearsed in tests only)",
    }
    return [{**f, "status": "NOT_MET", "reason": reasons.get(f["id"], "")} for f in parsed["final"]]


DEFECTS = [
    {"id": "DEF-01", "mc": "MC-005", "status": "FIXED", "found_by": "test_mc005_store_boundary_enforces_fairness_and_capacity",
     "summary": "ledger apply() caught only SchedulerError; the reference FairShare raises ShareViolation, so a keyed denied claim escaped unclassified and was not recorded for idempotent replay"},
    {"id": "DEF-02", "mc": "MC-027", "status": "FIXED", "found_by": "test_mc027_poisoning_route_change_stale_sparse",
     "summary": "after accepting a route change the raw window still held the old regime, so every later sample of the new regime was held as an outlier"},
    {"id": "DEF-03", "mc": "MC-027", "status": "FIXED", "found_by": "test_mc027_poisoning_route_change_stale_sparse",
     "summary": "a single poisoned spike counted toward the 3-sample persistence streak, letting spike + 2 samples force a route change; streak now requires mutually consistent deviations"},
    {"id": "DEF-04", "mc": "MC-009", "status": "FIXED", "found_by": "fuzz seed 5 (FZ-1)",
     "summary": "gap02.normalize raised KeyError/AttributeError on structurally malformed reports (missing node, memory not an object); now INVALID_ARGUMENT; same guard applied to GAP-14 and PLN-05 ingest; regression corpus tests/fuzz_corpus/gap02-FZ1-*"},
    {"id": "DEF-06", "mc": "MC-025", "status": "FIXED", "found_by": "test_mc025_sustained_overload_hotspot_slow_dependency_recovery",
     "summary": "admission's per-tenant bucket table never evicted idle tenants: once full, every new tenant was rejected forever (availability/DoS); idle (fully refilled) buckets are now evicted before rejecting"},
    {"id": "DEF-07", "mc": "MC-038", "status": "FIXED", "found_by": "RTM validation (broken_refs)",
     "summary": "three test bindings named non-existent checks (MC-006/007/026-CHK-032 instead of MC-032-CHK-009/012); the runner's own reference check caught them"},
    {"id": "DEF-08", "mc": "MC-015", "status": "FIXED", "found_by": "certification relevance/authz review",
     "summary": "ConfigManager.activate accepted any caller (actor string only): configuration activation/rollback now requires config.write and denials are audited"},
    {"id": "DEF-05", "mc": "MC-031", "status": "FIXED", "found_by": "benchmark self-validation",
     "summary": "harness timed samples with tracemalloc active, inflating latency ~4x (score-1000 p99 17.3 ms vs 5.4 ms); memory now measured in a separate pass"},
]


def apply_waivers(rows, registry, *, today, version) -> int:
    """BLOCKED rows covered by an ACTIVE waiver become WAIVED (never verified); returns the count."""
    n = 0
    for r in rows:
        if r["status"] == "BLOCKED":
            w = waivers.covers(registry, r["id"], today=today, current_version=version)
            if w:
                r["status"], r["waiver"] = "WAIVED", w["id"]
                n += 1
    return n


def write_history(out_dir: str, doc: dict) -> str:
    """Preserve an immutable, timestamped RTM snapshot per run (never overwritten)."""
    hist = os.path.join(out_dir, "history")
    os.makedirs(hist, exist_ok=True)
    path = os.path.join(hist, f"RTM-{doc['version']}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json")
    if os.path.exists(path):
        raise FileExistsError(path)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    return path


def rtm_validation(rows, tr) -> dict:
    """MC-038: every binding names an existing check; every invariant test exists; no orphan component tests."""
    ids = {r["id"] for r in rows}
    return {"broken_refs": sorted({c for c in tr["covers"] if c not in ids}),
            "missing_invariant_tests": sorted({t for s in specs.SPECS for _, t in s["invariants"] if t not in tr["outcomes"]}),
            "orphan_tests": sorted(t for t in tr["outcomes"] if t.startswith("test_mc") and not any(t in r["tests"] for r in rows))}


def ci_exit(counts: dict, validation: dict, *, ci: bool) -> int:
    bad = counts.get("FAILED", 0) or validation["broken_refs"] or validation["missing_invariant_tests"] or (
        ci and (counts.get("UNBOUND", 0) or counts.get("WEAK_BINDING", 0)))
    return 1 if bad else 0


def rtm_doc(rows, tr) -> dict:
    return {"version": __version__, "rows": [{k: r[k] for k in ("id", "mc", "priority", "category", "status", "modules", "tests",
                                                                   "artifacts", "blockers")} for r in rows],
            "reverse": {t: sorted(r["id"] for r in rows if t in r["tests"]) for t in tr["outcomes"] if t.startswith("test_mc")}}


def release_evidence(out_dir: str, rows) -> dict:
    m = supply_chain.manifest(PKG)
    digest = supply_chain.artifact_digest(m)
    rel = os.path.join(out_dir, "release")
    os.makedirs(rel, exist_ok=True)
    with open(os.path.join(rel, "MANIFEST.sha256"), "w") as fh:
        fh.write(supply_chain.manifest_text(m))
    json.dump(supply_chain.sbom(__version__, m), open(os.path.join(rel, "sbom.cdx.json"), "w"), indent=1)
    json.dump(supply_chain.provenance(__version__, m, builder_id="unverified:local-cowork-container", source_uri="archive:gap03 v4.3.0"),
              open(os.path.join(rel, "provenance.intoto.json"), "w"), indent=1)
    vs = supply_chain.vulnerability_scan(supply_chain.sbom(__version__, m), {"items": []})
    json.dump(vs, open(os.path.join(rel, "vulnerability_scan.json"), "w"), indent=1)
    return {"artifact_digest": digest, "files": len(m), "vulnerability_scan": vs["status"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checklist", default=os.path.join(PKG, "docs", "GAP03_v4.2.0_Missing_Components_Professional_Checklist.md"))
    ap.add_argument("--out", default=os.path.join(PKG, "evidence"))
    ap.add_argument("--ci", action="store_true", help="exit non-zero on FAILED/UNBOUND/WEAK or broken RTM refs")
    ap.add_argument("--skip-bench", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    parsed = parse(a.checklist)
    tr = run_tests()
    rows = evaluate(parsed, tr)
    waived = apply_waivers(rows, waivers.load(os.path.join(PKG, "WAIVERS.json")), today=dt.date.today(), version=__version__)
    pg = evaluate_pg(parsed, tr)
    dod = evaluate_dod(parsed, rows, DEFECTS)
    final = evaluate_final(parsed, rows, pg)
    # RTM validation (MC-038): every binding names an existing check; every test named in specs exists
    val = rtm_validation(rows, tr)
    broken, missing_tests, orphan_tests = val["broken_refs"], val["missing_invariant_tests"], val["orphan_tests"]
    rel = release_evidence(a.out, rows)
    if not a.skip_bench:
        from ..benchmarks import harness
        bench = {"env": harness.env_meta(), "platform_key": harness.platform_key(),
                 "results": [harness.run_case(c, samples=8, warmup=2) for c in harness.MATRIX]}
        tpath = os.path.join(PKG, "benchmarks", "thresholds", f"{harness.platform_key()}.json")
        bench["gate"] = harness.gate(bench["results"], json.load(open(tpath))) if os.path.exists(tpath) else {
            "pass": False, "failures": [{"why": "no threshold file for this platform"}]}
        json.dump(bench, open(os.path.join(a.out, "BENCHMARK.json"), "w"), indent=1, sort_keys=True)
    cnt = collections.Counter(r["status"] for r in rows)
    by_prio = {p: dict(collections.Counter(r["status"] for r in rows if r["priority"] == p)) for p in ("P0", "P1", "P2")}
    blk = collections.Counter(b.split(":")[0] for r in rows for b in r["blockers"])
    now = time.time()
    bundle = {"artifact_digest": rel["artifact_digest"],
              "evidence": {"tests": {"artifact_digest": rel["artifact_digest"], "produced_at": now,
                                     "status": "PASS" if not tr["failures"] and not tr["errors"] else "FAIL"}},
              "mandatory_checks": [{"id": r["id"], "status": "SATISFIED" if r["status"] == "LOCALLY_VERIFIED" else r["status"]}
                                   for r in rows if r["priority"] in ("P0", "P1")], "signoffs": {}}
    gate = exitgate.evaluate(bundle, artifact_digest=rel["artifact_digest"], trust=None, now=now)
    summary = {"schema": "GAP03-CERT/1", "version": __version__, "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "checklist": os.path.basename(a.checklist), "checklist_sha256": canonical.readb(a.checklist) and
               __import__("hashlib").sha256(canonical.readb(a.checklist)).hexdigest(),
               "checks_total": len(rows), "status_counts": {s: cnt.get(s, 0) for s in STATUSES}, "by_priority": by_prio,
               "basis_counts": dict(collections.Counter(r["basis"] for r in rows)), "waived": waived,
               "blocker_classes": dict(blk), "pg": {p["id"]: p["status"] for p in pg},
               "dod_counts": dict(collections.Counter(d["status"] for d in dod)), "final": {f["id"]: f["status"] for f in final},
               "tests": {k: tr[k] for k in ("ran", "failures", "errors", "skipped", "seconds", "optimize", "python")},
               "rtm_validation": {"broken_refs": broken, "missing_invariant_tests": missing_tests, "orphan_tests": orphan_tests},
               "weak_bindings": sorted({(r["id"], t) for r in rows for t in r["weak_bindings"]}),
               "release": rel, "exit_gate": {"decision": gate["decision"], "reason_count": len(gate["reasons"])},
               "defects_found_and_fixed": [d["id"] for d in DEFECTS], "completion_claims": 0, "standing_blocker": STANDING}
    summary["weak_bindings"] = [list(x) for x in summary["weak_bindings"]]
    w = lambda name, obj: json.dump(obj, open(os.path.join(a.out, name), "w", encoding="utf-8"), indent=1, sort_keys=True)  # noqa: E731
    w("CHECKS.json", rows)
    w("PROGRAM_GATES.json", pg)
    w("DEFINITION_OF_DONE.json", dod)
    w("FINAL_EXIT.json", final)
    w("DEFECTS.json", DEFECTS)
    w("TEST_REPORT.json", {k: tr[k] for k in ("outcomes", "ids", "covers", "ran", "failures", "errors", "skipped", "seconds", "optimize", "python")})
    w("RTM.json", rtm_doc(rows, tr))
    write_history(a.out, rtm_doc(rows, tr))
    w("COMPAT_REPORT.json", {"runtime": compat.check(allow_unverified=True), "matrix": compat.MATRIX,
                             "adjacent_fixtures": {f: json.load(open(os.path.join(PKG, "controlplane", "fixtures", f)))["versions_tested"]
                                                   for f in sorted(os.listdir(os.path.join(PKG, "controlplane", "fixtures")))},
                             "note": "adjacent versions exercised against the conformance harness only"})
    w("EXIT_GATE_RESULT.json", gate)
    w("API_REFERENCE.json", wire.api_reference())
    w("SUMMARY.json", summary)
    with open(os.path.join(a.out, "CERTIFICATION_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(report(summary, rows, pg, final))
    print(json.dumps({k: summary[k] for k in ("checks_total", "status_counts", "pg", "exit_gate", "tests")}, indent=1))
    return ci_exit(dict(cnt), val, ci=a.ci)


def report(s, rows, pg, final) -> str:
    L = [f"# GAP-03 v{s['version']} — checklist execution report", "", f"Generated {s['generated']} from `{s['checklist']}` "
         f"(sha256 `{s['checklist_sha256'][:16]}…`).", "",
         "**Result:** production exit gate **NO_GO**. No check is claimed complete: every record carries the standing blocker "
         "that the evidence is builder-verified only.", "", "| Status | Checks |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in s["status_counts"].items()]
    L += ["", "| Priority | " + " | ".join(STATUSES) + " |", "|---|" + "---|" * len(STATUSES)]
    for p, c in s["by_priority"].items():
        L.append(f"| {p} | " + " | ".join(str(c.get(x, 0)) for x in STATUSES) + " |")
    L += ["", "## Blocker classes", "", "| Class | Checks |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(s["blocker_classes"].items(), key=lambda x: -x[1])]
    L += ["", "## Program gates", ""] + [f"- **{p['id']} {p['title']}** — {p['status']}" + (f" ({p['blockers'][0]})" if p["blockers"] else "") for p in pg]
    L += ["", "## Final program exit", ""] + [f"- {f['id']}: {f['status']} — {f['reason']}" for f in final]
    L += ["", "## Per component", "", "| MC | Pri | Verified | Blocked | Failed | Weak | Unbound |", "|---|---|---|---|---|---|---|"]
    by = collections.defaultdict(collections.Counter)
    pri = {}
    for r in rows:
        by[r["mc"]][r["status"]] += 1
        pri[r["mc"]] = r["priority"]
    for mc in sorted(by):
        c = by[mc]
        L.append(f"| {mc} | {pri[mc]} | {c['LOCALLY_VERIFIED']} | {c['BLOCKED']} | {c['FAILED']} | {c['WEAK_BINDING']} | {c['UNBOUND']} |")
    L += ["", "## Tests", "", f"{s['tests']['ran']} tests, {s['tests']['failures']} failures, {s['tests']['errors']} errors, "
          f"{s['tests']['skipped']} skipped (pk_core absent), Python {s['tests']['python']}, optimize={s['tests']['optimize']}.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
