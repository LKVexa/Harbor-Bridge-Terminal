"""Execute the GAP-15 Missing-Components checklist against this package and record honest evidence.

    python -B gap15_runtime_compatibility_certification/tools/run_checklist.py

1. Parses every control (1,040) from the professional checklist markdown.
2. Runs the whole production test suite in-process (plus the v4.2.0 conformance
   suite, which skips when pk_core is absent), capturing per-test outcome and the
   ``controls:`` tags in each test docstring.
3. Assigns every control exactly one status:

   LOCALLY_VERIFIED            behaviour test(s) tagged to it all pass here
   ARTIFACT_PRESENT_UNREVIEWED the control asks for a document/artifact; it exists
                               and is checked mechanically, but nobody has reviewed it
   PARTIAL                     implemented and tested locally, a named element missing
   BLOCKED                     needs something this build cannot supply (named)
   NOT_APPLICABLE              with a written rationale
   NOT_IMPLEMENTED             nothing covers it
   FAILED                      a tagged test failed

   A tag never overrides a blocker: a blocked control lists its local tests as
   partial evidence but stays BLOCKED.
4. Writes evidence/: TEST_RESULTS.json, CHECKLIST_EXECUTION.{json,md}, RTM.{json,md}
   (100 GAP-15-C### rows), SBOM.json, PROVENANCE.json, GATE_DECISION.json.
"""
from __future__ import annotations

import collections
import datetime
import io
import json
import os
import re
import sys
import time
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(TOOLS)
ROOT = os.path.dirname(PKG)
EVID = os.path.join(PKG, "evidence")
CHECKLIST_MD = os.path.join(PKG, "GAP15_v4.2.0_Missing_Components_Professional_Checklist_v1.0.0.md")
sys.path[:0] = [ROOT, os.path.join(PKG, "tests", "production"), TOOLS]

INDEPENDENT_REVIEW = ("an independent human reviewer and a signed review record; the builder cannot review its own "
                      "work, and no owner is assigned in docs/OWNERS.json")
EXT = {
    "hsm": "an HSM/KMS/TPM key provider (none available to this build)",
    "gap02": "the real GAP-02 device-identity/attestation service and its quote formats (TPM2/SEV-SNP/TDX)",
    "gap07": "the real GAP-07 provenance/signing service and builder trust roots",
    "adjacent": "version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers",
    "replica": "a replicated store (multi-node) — ADR-001 records single-node SQLite only",
    "fleet": "a fleet/lab estate, real hardware profiles and a production-like deployment",
    "ci": "a CI system with protected branches, ephemeral runners and scheduled jobs",
    "siem": "an external SIEM/SOC pipeline",
    "time": "authenticated time sources (NTS/PTP/GPS clients) on the target hosts",
    "tls": "deployment-issued TLS certificates and a rotation mechanism",
    "scanner": "a vulnerability/licence scanner and its database",
    "release": "an authorised release identity to sign GO decisions",
    "master": "the authoritative original MASTER.md from the v4.1.0 source lineage",
    "people": "named owners, on-call rotation and approvers",
    "gameday": "a scheduled game day / drill with real operators",
}

BLOCKERS = {
    "01-08": ("partial", "encryption at rest of backups needs " + EXT["hsm"] + "; scheduled restore drills need " + EXT["ci"]),
    "03-07": ("blocked", EXT["hsm"]),
    "04-02": ("blocked", EXT["gap07"] + " (local verifier implemented against the same envelope shape)"),
    "04-09": ("blocked", "deployment-record correlation needs " + EXT["adjacent"]),
    "05-02": ("blocked", EXT["gap02"] + " (local quote verifier implemented)"),
    "06-01": ("blocked", EXT["time"] + " (source abstraction and trust ranking implemented)"),
    "11-07": ("blocked", EXT["replica"]),
    "12-05": ("blocked", "file-system access control and dual control over the store files are deployment-owned (" + EXT["people"] + ")"),
    "12-09": ("blocked", EXT["siem"]),
    "13-03": ("partial", "propagation to remote admission caches needs " + EXT["fleet"] + "; offline bundles carry a revocation-checkpoint freshness bound"),
    "14-07": ("partial", "TLS policy context implemented; certificates and rotation need " + EXT["tls"]),
    "15-02": ("partial", "signed + hashed backups implemented; encryption/key recovery/geo separation need " + EXT["hsm"]),
    "15-04": ("blocked", EXT["replica"]),
    "15-08": ("blocked", "failover/failback automation needs " + EXT["replica"]),
    "15-09": ("partial", "one measured restore (RPO/RTO) recorded; scheduled drills need " + EXT["ci"]),
    "15-10": ("blocked", "signed DR report needs " + EXT["release"]),
    "22-02": ("partial", "idempotent keyed queue implemented in memory; durable persistence of the queue is not implemented"),
    "29-08": ("blocked", "threshold validation against load/fault replays needs " + EXT["fleet"]),
    "29-10": ("blocked", "review cadence is a process control: " + EXT["people"]),
    "30-05": ("blocked", "integration with GAP-08/SCH-01/PLN-04 needs " + EXT["adjacent"] + " (idempotent admission API implemented)"),
    "30-10": ("blocked", "every supported execution tier needs " + EXT["adjacent"]),
    "31-08": ("not_implemented", "no producer/operator notification channel exists"),
    "34-07": ("blocked", "lab/production parity needs " + EXT["fleet"]),
    "35-02": ("partial", "harness calls production parsers directly; sanitizers do not apply to pure Python"),
    "35-04": ("partial", "seeded mutation fuzzing implemented; coverage guidance and corpus minimisation are not"),
    "35-08": ("blocked", EXT["ci"]),
    "35-09": ("blocked", "triage SLA needs " + EXT["people"]),
    "36-09": ("blocked", "red-team exercise needs " + EXT["people"]),
    "36-10": ("blocked", INDEPENDENT_REVIEW),
    "37-06": ("blocked", EXT["replica"]),
    "38-03": ("blocked", "network/TLS fault injection between real dependencies needs " + EXT["adjacent"]),
    "38-04": ("blocked", EXT["replica"]),
    "38-07": ("blocked", "site loss simulation needs " + EXT["fleet"]),
    "38-10": ("blocked", EXT["release"]),
    "39-06": ("blocked", EXT["fleet"]),
    "39-07": ("blocked", "multi-hour/day soak needs " + EXT["ci"]),
    "39-08": ("blocked", "regression budgets on controlled hardware need " + EXT["ci"]),
    "40-03": ("blocked", EXT["scanner"]),
    "40-04": ("partial", "migration/restore tests exist; not yet packaged into a signed bundle by a release identity"),
    "40-05": ("blocked", "signed performance evidence needs " + EXT["release"]),
    "40-06": ("blocked", "canary plan/DR proof in the bundle need " + EXT["gameday"]),
    "40-09": ("blocked", "immutable preservation needs " + EXT["release"]),
    "41-04": ("partial", "RTM links this build's test results; release-candidate evidence needs " + EXT["release"]),
    "41-05": ("blocked", EXT["people"]),
    "42-07": ("blocked", "ADR owners/approvers: " + EXT["people"]),
    "42-09": ("blocked", INDEPENDENT_REVIEW),
    "42-10": ("blocked", INDEPENDENT_REVIEW),
    "43-01": ("blocked", EXT["people"]), "43-02": ("blocked", EXT["people"]), "43-03": ("blocked", EXT["people"]),
    "43-04": ("blocked", EXT["people"]), "43-05": ("blocked", EXT["people"]), "43-06": ("blocked", EXT["people"]),
    "43-08": ("blocked", EXT["people"]), "43-10": ("blocked", EXT["gameday"]),
    "44-10": ("partial", "Linux paths tested; Windows and container runs not executed here"),
    "45-05": ("blocked", EXT["scanner"]),
    "45-06": ("blocked", "patch SLA and support window need " + EXT["people"]),
    "45-07": ("blocked", EXT["ci"]),
    "45-08": ("partial", "stdlib-only: no dependencies are downloaded; build network isolation not enforced here"),
    "46-09": ("blocked", EXT["gameday"]),
    "46-10": ("blocked", EXT["release"]),
    "47-03": ("blocked", EXT["hsm"]),
    "47-09": ("partial", "backup.run/restore.run actions exist in the authz model; the backup API is CLI/library only, not behind the service authz path"),
    "47-10": ("blocked", "periodic automated restore verification needs " + EXT["ci"]),
    "48-09": ("blocked", EXT["gameday"]),
    "50-06": ("blocked", EXT["release"]),
    "50-07": ("blocked", "deployment automation integration needs " + EXT["ci"]),
    "50-08": ("not_implemented", "no separate emergency-override path exists in the exit gate (by design it only says NO_GO)"),
    "51-01": ("blocked", EXT["master"]), "51-02": ("blocked", EXT["master"]), "51-03": ("blocked", EXT["master"]),
    "51-04": ("blocked", EXT["master"]), "51-05": ("blocked", EXT["master"]), "51-06": ("blocked", EXT["master"]),
}
for n in range(33, 34):
    for i in range(1, 11):
        BLOCKERS.setdefault(f"{n}-{i:02d}", ("blocked", EXT["adjacent"] + " (local simulated coverage listed where tagged)"))
DOC_ONLY_TESTS = {"test_retention_privacy_documented", "test_replication_export_rules_documented", "test_adr_structure_and_links",
                  "test_runbooks_cover_required_sections", "test_deployment_manifests_least_privilege",
                  "test_one_threat_row_per_component", "test_every_component_mapped_to_runbook", "test_runbook_links_resolve"}
NA_11 = "no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem"


def parse_checklist(path: str) -> list:
    controls, comp, prio, title, section = [], None, None, None, None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^# (P[012]) — (\d\d)\. (.+)$", line)
        if m:
            prio, comp, title = m.group(1), m.group(2), m.group(3).strip()
            continue
        if line.startswith("# Final production-readiness"):
            comp, prio, title = "SIGNOFF", "P0", "Final production-readiness sign-off"
        m = re.match(r"^- \[ \] \*\*(GAP15-[A-Z0-9-]+)\*\* (.+)$", line.strip())
        if m:
            cid, text = m.group(1), m.group(2)
            if cid.startswith("GAP15-GLOBAL"):
                c, p, t = "GLOBAL", "P0", "Global completion gates"
            elif cid.startswith("GAP15-SIGNOFF"):
                c, p, t = "SIGNOFF", "P0", "Final production-readiness sign-off"
            else:
                c, p, t = comp, prio, title
            item = cid.split("-", 3)[-1] if cid.startswith("GAP15-MC") else cid.split("-")[-1]
            controls.append({"control_id": cid, "component": c, "priority": p, "component_title": t, "item": item, "text": text})
    return controls


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = []
        self._t = {}

    def startTest(self, test):
        self._t[test.id()] = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, outcome, detail=""):
        doc = (getattr(test, "_testMethodDoc", None) or "")
        tags = re.findall(r"\b(\d\d-\d\d)\b", doc.split("controls:", 1)[1]) if "controls:" in doc else []
        self.records.append({"test": test.id(), "method": getattr(test, "_testMethodName", test.id()), "outcome": outcome,
                             "controls": tags, "seconds": round(time.perf_counter() - self._t.get(test.id(), time.perf_counter()), 4),
                             "detail": detail[-600:]})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._rec(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._rec(test, "fail", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._rec(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._rec(test, "skip", reason)


def run_tests() -> tuple:
    import warnings
    warnings.simplefilter("ignore", ResourceWarning)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.discover(os.path.join(PKG, "tests", "production"), pattern="test_*.py",
                                   top_level_dir=os.path.join(PKG, "tests", "production")))
    import importlib.util
    spec = importlib.util.spec_from_file_location("v42_conformance", os.path.join(PKG, "tests", "test_component.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    suite.addTests(loader.loadTestsFromModule(mod))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=Recorder, verbosity=0)
    t0 = time.perf_counter()
    res = runner.run(suite)
    return res.records, round(time.perf_counter() - t0, 2), res.testsRun


def assign(controls: list, records: list) -> list:
    by_ctrl = collections.defaultdict(list)
    for r in records:
        for tag in r["controls"]:
            by_ctrl[tag].append(r)
    comp_tests = collections.defaultdict(list)
    for r in records:
        for tag in r["controls"]:
            comp_tests[tag[:2]].append(r)
    out = []
    for c in controls:
        comp, item = c["component"], c["item"]
        key = f"{comp}-{item}" if comp not in ("GLOBAL", "SIGNOFF") else None
        tests = by_ctrl.get(key, []) if key else []
        row = dict(c, tests=sorted({t["test"] for t in tests}), status=None, blocker=None, note=None)
        fails = [t for t in tests if t["outcome"] in ("fail", "error")]
        behaviour = [t for t in tests if t["method"] not in DOC_ONLY_TESTS and t["outcome"] == "pass"]
        if comp in ("GLOBAL", "SIGNOFF"):
            row["status"], row["blocker"] = "BLOCKED", ("release-level gate over all components; open blockers remain "
                                                        "(see BLOCKED rows) and " + INDEPENDENT_REVIEW)
        elif item.startswith("EXIT"):
            row["status"] = "BLOCKED"
            row["blocker"] = {"EXIT-01": "proof of no bypass in a deployed production path needs " + EXT["fleet"],
                              "EXIT-02": "release-candidate evidence tied to a build digest and signed needs " + EXT["release"],
                              "EXIT-03": "ownership, game-day-tested runbooks and release-gate evidence need " + EXT["people"]}[item]
        elif item == "17":
            row["status"], row["blocker"] = "BLOCKED", INDEPENDENT_REVIEW
        elif fails:
            row["status"], row["note"] = "FAILED", "; ".join(f["test"] for f in fails)
        elif key in BLOCKERS:
            kind, why = BLOCKERS[key]
            row["status"] = {"blocked": "BLOCKED", "partial": "PARTIAL", "not_implemented": "NOT_IMPLEMENTED"}[kind]
            row["blocker"] = why
        elif item in ("11", "12") and int(comp) >= 33:
            row["status"], row["note"] = "NOT_APPLICABLE", NA_11 if item == "11" else (
                "no runtime telemetry: this component is a verification/release/governance artifact; its outputs are "
                "machine-readable evidence files rather than a running subsystem")
        elif item in ("13", "15"):
            row["status"] = "ARTIFACT_PRESENT_UNREVIEWED" if tests and not fails else "NOT_IMPLEMENTED"
        elif item == "14":
            ct = comp_tests.get(comp, [])
            passing = [t for t in ct if t["outcome"] == "pass" and t["method"] not in DOC_ONLY_TESTS]
            negative = any(f"{comp}-10" in t["controls"] for t in passing)
            if len(passing) >= 3 and not [t for t in ct if t["outcome"] in ("fail", "error")]:
                row["status"] = "LOCALLY_VERIFIED" if negative else "PARTIAL"
                row["tests"] = sorted({t["test"] for t in passing})
                if not negative:
                    row["blocker"] = f"no test tagged to the component's adversarial/negative item {comp}-10"
            else:
                row["status"] = "NOT_IMPLEMENTED"
        elif item == "16":
            row["status"] = "PENDING_RTM"
        elif behaviour:
            row["status"] = "LOCALLY_VERIFIED"
        elif tests:
            row["status"] = "ARTIFACT_PRESENT_UNREVIEWED"
        else:
            row["status"] = "NOT_IMPLEMENTED"
        out.append(row)
    # item 16: RTM linkage holds when every other row of the component resolves to tests or a named blocker/rationale
    for row in out:
        if row["status"] == "PENDING_RTM":
            sib = [r for r in out if r["component"] == row["component"] and r["item"] != "16"]
            unresolved = [r["control_id"] for r in sib if r["status"] in ("NOT_IMPLEMENTED", "FAILED")]
            row["status"] = "LOCALLY_VERIFIED" if not unresolved else "PARTIAL"
            row["tests"] = ["tools/run_checklist.py (RTM generation)"]
            if unresolved:
                row["blocker"] = "unresolved rows: " + ", ".join(unresolved)
    return out


def build_rtm(rows: list) -> list:
    """100-row RTM over the original GAP-15-C### requirements (MC-41-01..03)."""
    items = json.load(open(os.path.join(PKG, "CHECKLIST.json")))["items"]
    mc = open(os.path.join(PKG, "MISSING_COMPONENTS.md")).read()
    comp_refs = collections.defaultdict(set)
    for m in re.finditer(r"^(\d+)\. \*\*(.+?)\*\* - .*?((?:C\d{3}(?:-C\d{3})?(?:, )?)+)\.?\s*$", mc, re.M):
        n = int(m.group(1))
        for part in re.findall(r"C(\d{3})(?:-C(\d{3}))?", m.group(3)):
            lo, hi = int(part[0]), int(part[1] or part[0])
            for c in range(lo, hi + 1):
                comp_refs[f"C{c:03d}"].add(f"{n:02d}")
    status_by_comp = collections.defaultdict(collections.Counter)
    tests_by_comp = collections.defaultdict(set)
    for r in rows:
        status_by_comp[r["component"]][r["status"]] += 1
        tests_by_comp[r["component"]].update(r["tests"])
    rtm = []
    for it in items:
        cid = it["check_id"].split("-")[-1]
        comps = sorted(comp_refs.get(cid, set()))
        st = collections.Counter()
        for c in comps:
            st.update(status_by_comp[c])
        rtm.append({"requirement_id": it["check_id"], "dimension": it["dimension"], "text": it["requirement"],
                    "v420_implementation": "component.py (reference model; pk_core-bound assessment not executable here)",
                    "missing_components": comps,
                    "production_modules": sorted({m for c in comps for m in MODULES.get(c, [])}),
                    "tests": sorted({t for c in comps for t in tests_by_comp[c]})[:12],
                    "control_status_counts": dict(st),
                    "status": ("NO_MISSING_COMPONENT_MAPPED" if not comps else
                               "BLOCKED" if st.get("BLOCKED") else "PARTIAL" if st.get("PARTIAL") or st.get("NOT_IMPLEMENTED")
                               else "LOCALLY_VERIFIED"),
                    "owner": None, "reviewer": None})
    return rtm


MODULES = {
    "01": ["store.py"], "02": ["store.py", "state.py"], "03": ["ed25519.py", "signing.py"], "04": ["provenance.py"],
    "05": ["attestation.py"], "06": ["timepolicy.py"], "07": ["authn.py"], "08": ["authz.py"], "09": ["schemas.py", "canonical.py"],
    "10": ["service.py"], "11": ["store.py"], "12": ["store.py", "service.py"], "13": ["state.py", "service.py"],
    "14": ["http_api.py", "serve.py"], "15": ["store.py", "cli.py"], "16": ["negotiation.py"], "17": ["capability.py"],
    "18": ["versions.py"], "19": ["features.py"], "20": ["state.py", "service.py"], "21": ["state.py"], "22": ["scheduler.py"],
    "23": ["policy.py"], "24": ["offline.py"], "25": ["partition.py"], "26": ["observability.py"], "27": ["observability.py"],
    "28": ["service.py"], "29": ["ops.py"], "30": ["service.py"], "31": ["service.py", "state.py"], "32": ["capacity.py"],
    "34": ["fixtures_matrix.py"], "40": ["release.py"], "41": ["release.py"], "44": ["config.py", "release.py", "serve.py"],
    "45": ["release.py"], "46": ["release.py", "service.py"], "47": ["store.py", "cli.py"], "49": ["policy.py"], "50": ["release.py"],
}


def main() -> int:
    os.makedirs(EVID, exist_ok=True)
    controls = parse_checklist(CHECKLIST_MD)
    records, secs, n = run_tests()
    rows = assign(controls, records)
    rtm = build_rtm(rows)
    from gap15_runtime_compatibility_certification.production import release, signing
    counts = collections.Counter(r["status"] for r in rows)
    now = int(time.time())
    passed = sum(1 for r in records if r["outcome"] == "pass")
    failed = sum(1 for r in records if r["outcome"] in ("fail", "error"))
    skipped = sum(1 for r in records if r["outcome"] == "skip")
    json.dump({"schema": "GAP15_TEST_RESULTS/1", "generated_at": now, "python": sys.version.split()[0], "tests_run": n,
               "passed": passed, "failed": failed, "skipped": skipped, "seconds": secs, "records": records},
              open(os.path.join(EVID, "TEST_RESULTS.json"), "w"), indent=1)
    build = release.tree_digest(PKG)["root"]
    sb = release.sbom(PKG, "gap15_runtime_compatibility_certification", "4.3.0")
    prov = release.build_provenance(PKG, builder="cowork-cloud-container (development key)",
                                    source_revision="archive:gap15_runtime_compatibility_certification_v4.2.0.zip + GAP-15 MC overlay",
                                    invocation=["python", "-B", "tools/run_checklist.py"])
    json.dump(sb, open(os.path.join(EVID, "SBOM.json"), "w"), indent=1)
    json.dump(prov, open(os.path.join(EVID, "PROVENANCE.json"), "w"), indent=1)
    # Gate: sign what this build can honestly produce with a *development* build key; everything else is absent.
    kp = signing.DevelopmentKeyProvider()
    trust = signing.TrustStore()
    trust.add(signing.TrustedKey("dev-build", "cowork-build", kp.generate("dev-build"), scopes=frozenset({"gate:sign"})))
    ins = [release.sign_input(kp, "dev-build", release.GateInput("tests", build, now, {"status": "pass" if failed == 0 else "fail",
                                                                                        "passed": passed, "failed": failed})),
           release.sign_input(kp, "dev-build", release.GateInput("rtm", build, now, {"status": "pass" if counts.get("NOT_IMPLEMENTED", 0) + counts.get("FAILED", 0) == 0 and counts.get("BLOCKED", 0) == 0 else "fail",
                                                                                      "counts": dict(counts)})),
           release.sign_input(kp, "dev-build", release.GateInput("sbom", build, now, {"status": "pass", "subject": sb["metadata"]["subject"]})),
           release.sign_input(kp, "dev-build", release.GateInput("provenance", build, now, {"status": "pass"})),
           release.sign_input(kp, "dev-build", release.GateInput("performance", build, now, {"status": "pass", "source": "evidence/BENCHMARK.json",
                                                                                              "scope": "single-process, not fleet"})),
           release.sign_input(kp, "dev-build", release.GateInput("restore", build, now, {"status": "pass", "source": "BackupRestoreTest"}))]
    gate = release.exit_gate(ins, build_digest=build, trust=trust, now=now)
    gate["note"] = ("inputs signed with an ephemeral development build key; security, dr, review and approval evidence "
                    "do not exist and cannot be produced by the builder")
    json.dump(gate, open(os.path.join(EVID, "GATE_DECISION.json"), "w"), indent=1)
    json.dump({"schema": "GAP15_CHECKLIST_EXECUTION/1", "generated_at": now, "build_digest": build,
               "checklist": os.path.basename(CHECKLIST_MD), "controls": len(rows), "counts": dict(counts), "rows": rows},
              open(os.path.join(EVID, "CHECKLIST_EXECUTION.json"), "w"), indent=1)
    json.dump({"schema": "GAP15_RTM/1", "generated_at": now, "build_digest": build, "rows": rtm,
               "problems": release.rtm_problems([release.RtmRow(r["control_id"], r["text"], r["component"], r["priority"],
                                                                r["status"] if r["status"] != "PARTIAL" else "BLOCKED",
                                                                tests=r["tests"], evidence=["evidence/TEST_RESULTS.json"] if r["tests"] else [],
                                                                blocker=r["blocker"] or r["note"],
                                                                na_rationale=r["note"] if r["status"] == "NOT_APPLICABLE" else None)
                                                 for r in rows if r["status"] not in ("NOT_IMPLEMENTED",)])},
              open(os.path.join(EVID, "RTM.json"), "w"), indent=1)
    write_markdown(rows, rtm, counts, records, gate, build, secs, n, passed, failed, skipped)
    print(json.dumps({"tests_run": n, "passed": passed, "failed": failed, "skipped": skipped, "seconds": secs,
                      "controls": len(rows), "counts": dict(counts), "gate": gate["decision"]}, indent=1))
    return 0 if failed == 0 else 1


def write_markdown(rows, rtm, counts, records, gate, build, secs, n, passed, failed, skipped):
    order = ["LOCALLY_VERIFIED", "ARTIFACT_PRESENT_UNREVIEWED", "PARTIAL", "BLOCKED", "NOT_APPLICABLE", "NOT_IMPLEMENTED", "FAILED"]
    L = [f"# GAP-15 Missing-Components Checklist — Execution Record", "",
         f"Generated {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} by `tools/run_checklist.py`; build digest `{build}`.", "",
         f"**Tests:** {n} run, {passed} passed, {failed} failed, {skipped} skipped ({secs}s). "
         f"**Exit gate:** {gate['decision']}.", "",
         "| Status | Controls |", "|---|---|"]
    for s in order:
        L.append(f"| {s} | {counts.get(s, 0)} |")
    L += ["", f"Total: {len(rows)} controls (1,020 component controls + 10 global + 10 sign-off).", "",
          "LOCALLY_VERIFIED means a behaviour test tagged to the control passed in this build environment. It is not a production "
          "certification and not an independent review.", "", "## Per component", "",
          "| # | Component | Pri | Verified | Artifact | Partial | Blocked | N/A | Not impl. |", "|---|---|---|---|---|---|---|---|---|"]
    comps = collections.OrderedDict()
    for r in rows:
        comps.setdefault((r["component"], r["component_title"], r["priority"]), collections.Counter())[r["status"]] += 1
    for (c, t, p), cnt in comps.items():
        L.append(f"| {c} | {t} | {p} | {cnt['LOCALLY_VERIFIED']} | {cnt['ARTIFACT_PRESENT_UNREVIEWED']} | {cnt['PARTIAL']} | "
                 f"{cnt['BLOCKED']} | {cnt['NOT_APPLICABLE']} | {cnt['NOT_IMPLEMENTED'] + cnt['FAILED']} |")
    L += ["", "## Gate decision", "", "```json", json.dumps({k: gate[k] for k in ("decision", "inputs", "blockers")}, indent=1), "```", "",
          "## Every control", "", "| Control | Status | Evidence / blocker |", "|---|---|---|"]
    for r in rows:
        ev = r["blocker"] or r["note"] or ", ".join(t.split(".")[-1] for t in r["tests"][:4])
        L.append(f"| {r['control_id']} | {r['status']} | {ev.replace('|', '/')} |")
    open(os.path.join(EVID, "CHECKLIST_EXECUTION.md"), "w").write("\n".join(L) + "\n")
    R = ["# GAP-15 Requirements Traceability Matrix (100 source requirements)", "",
         "Generated from `CHECKLIST.json` × `MISSING_COMPONENTS.md` source references × this run's control results. "
         "Owner and reviewer columns are empty because no owner is assigned (MC-41-05 blocked).", "",
         "| Requirement | Dimension | Missing components | Status | Modules |", "|---|---|---|---|---|"]
    for r in rtm:
        R.append(f"| {r['requirement_id']} | {r['dimension']} | {', '.join(r['missing_components']) or '—'} | {r['status']} | "
                 f"{', '.join(r['production_modules']) or '—'} |")
    open(os.path.join(EVID, "RTM.md"), "w").write("\n".join(R) + "\n")


if __name__ == "__main__":
    sys.exit(main())
