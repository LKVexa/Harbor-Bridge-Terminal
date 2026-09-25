"""Build the machine-readable release evidence bundle (C020, C090, INV71-X004).

    python -B tools/build_evidence.py

Writes evidence/:
  tests.json               every test id with outcome, env fingerprint, source digest
  security/fuzz.json       tools/fuzz.py release seeds
  performance/bench.json   tools/bench.py (reference layer only)
  pk_core_probe.json       tools/pk_core_probe.py
  qualification.json       this host's node qualification (expected REJECT)
  sbom.cdx.json            CycloneDX 1.5 SBOM for this package
  provenance.json          builder, time, inputs by digest (unsigned)
  license-inventory.json   package + dependency licences
  checklist_execution.json one record per checklist line (1,730 lines)
  traceability.json        requirement/control -> items -> evidence(sha256) -> tests(outcome); test -> controls
  release-manifest.json    sha256 of every package file and the tree digest
then runs tools/production_gate.py -> evidence/gate-result.json.
Also regenerates AUDIT_AFTER.json from the traceability, never from prose.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import io
import json
import pathlib
import platform
import re
import subprocess
import sys
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.dont_write_bytecode = True
EV = PKG / "evidence"
CHECKLIST = PKG / "governance" / "INV71_v4.2.0_PRODUCTION_REMEDIATION_MASTER_CHECKLIST.md"
LATE = {"evidence/release-manifest.json", "evidence/gate-result.json", "evidence/traceability.json"}
EXCLUDE_DIRS = {"__pycache__", ".git", "fuzz-findings"}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, PKG / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def files(include_evidence: bool) -> list[pathlib.Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        if not p.is_file() or any(part in EXCLUDE_DIRS for part in p.parts) or p.suffix == ".pyc":
            continue
        rel = p.relative_to(PKG).as_posix()
        if rel.startswith("evidence/") and not include_evidence:
            continue
        out.append(p)
    return out


def tree_digest(paths: list[pathlib.Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        rel = p.relative_to(PKG).as_posix().encode()
        d = bytes.fromhex(sha(p))
        h.update(len(rel).to_bytes(8, "big")); h.update(rel); h.update(d)
    return h.hexdigest()


def env() -> dict:
    q = load("qualify_mod", "control/qualify.py")
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(),
            "kvm": q.probe_local().get("kvm"), "optimize_flag": sys.flags.optimize}


# ------------------------------------------------------------------ checklist
ITEM = re.compile(r"^- \[ \] \*\*((?:INV-71-C\d{3}|INV71-X\d{3})-(IMP|DES|VER|GATE)-(\d{2})|GLOBAL-(\d{2})|FINAL-(\d{2}))\*\* (.*)$")


def parse_checklist() -> list[dict]:
    items = []
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        m = ITEM.match(line)
        if not m:
            continue
        iid = m.group(1)
        if iid.startswith("GLOBAL"):
            items.append({"id": iid, "control": "GLOBAL", "kind": "GLOBAL", "n": int(m.group(4)), "text": m.group(6)})
        elif iid.startswith("FINAL"):
            items.append({"id": iid, "control": "FINAL", "kind": "FINAL", "n": int(m.group(5)), "text": m.group(6)})
        else:
            ctl = iid.rsplit("-", 2)[0].replace("INV-71-", "")
            items.append({"id": iid, "control": ctl, "kind": m.group(2), "n": int(m.group(3)), "text": m.group(6)})
    return items


# ------------------------------------------------------------------ tests
class Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = []

    def _rec(self, test, outcome, detail=""):
        self.records.append({"id": test.id(), "outcome": outcome, "detail": detail[:300]})

    def addSuccess(self, test):
        super().addSuccess(test); self._rec(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._rec(test, "FAIL", str(err[1]))

    def addError(self, test, err):
        super().addError(test, err); self._rec(test, "ERROR", str(err[1]))

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._rec(test, "NOT_RUN", reason)


def run_tests() -> tuple[list[dict], dict[str, list[str]]]:
    tests_dir = PKG / "tests"
    sys.path.insert(0, str(tests_dir))
    suite = unittest.defaultTestLoader.discover(str(tests_dir), pattern="test_*.py", top_level_dir=str(tests_dir))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=Collect, verbosity=0)
    res = runner.run(suite)
    # control tags from class docstrings
    tags: dict[str, list[str]] = {}

    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                walk(t)
            else:
                doc = (type(t).__doc__ or "") + " " + (getattr(t, t._testMethodName).__doc__ or "")
                ids = sorted(set(re.findall(r"\[(C\d{3}|INV71-X\d{3})(?:-[A-Z]+-\d+)?\]", doc)))
                tags[t.id()] = ids
    walk(unittest.defaultTestLoader.discover(str(tests_dir), pattern="test_*.py", top_level_dir=str(tests_dir)))
    return res.records, tags


def main() -> int:
    EV.mkdir(exist_ok=True)
    (EV / "security").mkdir(exist_ok=True)
    (EV / "performance").mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    src_files = files(include_evidence=False)
    src_digest = tree_digest(src_files)
    environment = env()

    records, tags = run_tests()
    counts = {k: sum(1 for r in records if r["outcome"] == k) for k in ("PASS", "FAIL", "ERROR", "NOT_RUN")}
    (EV / "tests.json").write_text(json.dumps({"schema": "PK_HEAVYBOX_TEST_EVIDENCE/1", "generated": now,
                                               "source_tree_sha256": src_digest, "environment": environment,
                                               "counts": counts, "tests": records, "tags": tags}, indent=1) + "\n")

    fz = load("fuzz_mod", "tools/fuzz.py").run(20000, 71)
    (EV / "security" / "fuzz.json").write_text(json.dumps(fz, indent=1) + "\n")
    bench = load("bench_mod", "tools/bench.py")
    br = bench.run(300, 3)
    br["gate"] = bench.gate(br, json.loads((PKG / "governance" / "perf_thresholds.json").read_text()))
    (EV / "performance" / "bench.json").write_text(json.dumps(br, indent=1) + "\n")
    (EV / "pk_core_probe.json").write_text(json.dumps(load("probe_mod", "tools/pk_core_probe.py").probe(), indent=1) + "\n")
    q = load("q2", "control/qualify.py")
    (EV / "qualification.json").write_text(json.dumps(q.qualify(q.probe_local(), "cloud"), indent=1) + "\n")

    version = (PKG / "VERSION").read_text().strip()
    (EV / "sbom.cdx.json").write_text(json.dumps({
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"timestamp": now, "component": {"type": "library", "name": "inv71-heavy-agent-sandbox",
                                                     "version": version, "hashes": [{"alg": "SHA-256", "content": src_digest}],
                                                     "licenses": [{"license": {"name": "UNSPECIFIED - see LICENSE_STATUS.md"}}]}},
        "components": [],
        "properties": [{"name": "inv71:runtime-dependencies", "value": "none (Python standard library only)"},
                       {"name": "inv71:optional-test-dependency", "value": "jsonschema (MIT), not redistributed"},
                       {"name": "inv71:vulnerability-scan", "value": "NOT_RUN - no scanner available; zero third-party runtime components"}]},
        indent=1) + "\n")
    (EV / "license-inventory.json").write_text(json.dumps({
        "schema": "PK_HEAVYBOX_LICENSES/1", "package": {"license": None, "status": "UNSPECIFIED", "file_present": (PKG / "LICENSE").exists()},
        "runtime_dependencies": [], "test_dependencies": [{"name": "jsonschema", "license": "MIT"}],
        "vendored": []}, indent=1) + "\n")
    (EV / "provenance.json").write_text(json.dumps({
        "schema": "PK_HEAVYBOX_PROVENANCE/1", "subject": {"name": "inv71_heavy_agent_sandbox", "version": version, "source_tree_sha256": src_digest},
        "builder": {"id": "junkyard-chop-shop remediation pass (cloud container, not a hardened builder)", "environment": environment},
        "inputs": {"baseline_zip": "inv71_heavy_agent_sandbox_v4.2.0.zip sha256 f23a04ad85611d783851965789c7b441fc6d3320b76700a8c2f62955948d0c08",
                   "checklist_md_sha256": sha(CHECKLIST)},
        "vcs_revision": None, "signed": False, "reproducible": "fixtures verified byte-reproducible; package tree not rebuilt independently",
        "generated": now}, indent=1) + "\n")

    # --------------------------------------------------------- checklist execution
    cs = load("cs", "governance/checklist_status.py")
    items = parse_checklist()
    test_ok = {r["id"]: r["outcome"] for r in records}
    by_ctl: dict[str, list[str]] = {}
    for tid, ids in tags.items():
        for c in ids:
            by_ctl.setdefault(c, []).append(tid)
    problems = []
    execution = []
    for it in items:
        c, k, n = it["control"], it["kind"], it["n"]
        if k == "GLOBAL":
            s, note = cs.GLOBAL[n - 1].split(":", 1)
            ev = []
        elif k == "FINAL":
            s, note = cs.FINAL[n - 1].split(":", 1)
            ev = []
        elif k == "IMP":
            lst = cs.IMP.get(c)
            if lst is None or n > len(lst):
                problems.append(f"no IMP status for {it['id']}")
                s, note = "O", "no status recorded"
            else:
                s, note = lst[n - 1].split(":", 1)
            ev = cs.E.get(c, [])
        else:
            kind = "XVER" if c.startswith("INV71-X") and k == "VER" else k
            s, note = cs.rule_status(c, kind, n, bool(by_ctl.get(c)))
            ev = cs.E.get(c, [])
        ev_rec = []
        for rel in ev:
            p = PKG / rel
            if rel in LATE:
                ev_rec.append({"path": rel, "sha256": "see release-manifest"})
            elif p.exists():
                ev_rec.append({"path": rel, "sha256": sha(p)})
            else:
                problems.append(f"{it['id']}: missing evidence {rel}")
        tests = sorted(by_ctl.get(c, []))
        failing = [t for t in tests if test_ok.get(t) not in ("PASS", "NOT_RUN")]
        if failing and s == "I":
            s, note = "P", f"tagged tests failing: {failing[:3]}"
        execution.append({"id": it["id"], "control": c, "kind": k, "status": cs.STATUS[s], "note": note.strip(),
                          "text": it["text"], "evidence": ev_rec,
                          "tests": [{"id": t, "outcome": test_ok.get(t, "MISSING")} for t in tests] if k in ("IMP", "VER") else []})
    (EV / "checklist_execution.json").write_text(json.dumps({"schema": "PK_HEAVYBOX_CHECKLIST_EXECUTION/1", "generated": now,
                                                            "checklist_sha256": sha(CHECKLIST), "items": execution}, indent=1) + "\n")

    # --------------------------------------------------------- traceability + audit
    req = json.loads((PKG / "governance" / "requirements.json").read_text())
    for r in req["requirements"]:
        for t in r["tests"]:
            mod, cls, meth = t.split(".")
            if not any(x["id"].endswith(f"{mod}.{cls}.{meth}") for x in records):
                problems.append(f"{r['id']}: test {t} not found")
    audit = json.loads((PKG / "AUDIT_AFTER.json").read_text())
    ctl_summary = {}
    for ctl in audit["controls"]:
        cid = ctl["check_id"].replace("INV-71-", "")
        its = [e for e in execution if e["control"] == cid]
        st = {v: sum(1 for e in its if e["status"] == v) for v in cs.STATUS.values()}
        ctl_summary[cid] = st
        prev = ctl.get("status_v4_2_0", ctl["status"])
        ctl["status_v4_2_0"] = prev
        if prev == "EVIDENCED":
            new = "EVIDENCED"
        elif any(e["status"] in ("IMPLEMENTED_UNREVIEWED", "PARTIAL") for e in its if e["kind"] == "IMP"):
            # only implementation lines move a control; DES/VER/GATE bookkeeping does not
            new = "PARTIAL"
        else:
            new = "MISSING"
        ctl["status"] = new
        ctl["v4_3_0_items"] = st
        ctl["v4_3_0_evidence"] = cs.E.get(cid, [])
        ctl["v4_3_0_tests"] = len(by_ctl.get(cid, []))
    audit["version"] = version
    audit["audit_basis"] = ("v4.3.0: regenerated by tools/build_evidence.py from evidence/traceability.json. "
                            "Reference-scope implementation raises MISSING to PARTIAL only; no control becomes EVIDENCED "
                            "without the production path and independent review (checklist GATE-01/GATE-03).")
    audit["summary"] = {k: sum(1 for c in audit["controls"] if c["status"] == k) for k in ("EVIDENCED", "PARTIAL", "MISSING")}
    audit["summary_v4_2_0"] = {"EVIDENCED": 10, "PARTIAL": 40, "MISSING": 50}
    (PKG / "AUDIT_AFTER.json").write_text(json.dumps(audit, indent=2) + "\n")

    orphan_tests = sorted(t for t, ids in tags.items() if not ids and "test_component" not in t and "test_sandbox" not in t)
    item_totals = {v: sum(1 for e in execution if e["status"] == v) for v in cs.STATUS.values()}
    trace = {"schema": "PK_HEAVYBOX_TRACEABILITY/1", "generated": now, "source_tree_sha256": src_digest,
             "checklist_sha256": sha(CHECKLIST), "item_totals": item_totals, "items_total": len(execution),
             "controls": ctl_summary,
             "requirements": [{"id": r["id"], "controls": r["controls"], "tests": [{"id": t, "outcome": next((x["outcome"] for x in records if x["id"].endswith(t)), "MISSING")} for t in r["tests"]]} for r in req["requirements"]],
             "tests_to_controls": tags, "orphan_tests": orphan_tests, "problems": problems}
    (EV / "traceability.json").write_text(json.dumps(trace, indent=1) + "\n")

    # --------------------------------------------------------- MISSING_COMPONENTS.md (generated)
    lines = ["# INV-71 missing components after v4.3.0 remediation", "",
             "<!-- GENERATED by tools/build_evidence.py from evidence/traceability.json -->", "",
             f"**Controls:** {audit['summary']['EVIDENCED']} evidenced, {audit['summary']['PARTIAL']} partial, "
             f"{audit['summary']['MISSING']} missing (v4.2.0: 10 / 40 / 50).  ",
             f"**Checklist lines ({len(execution)}):** " + ", ".join(f"{v} {k}" for k, v in item_totals.items()) + ".  ",
             "**Production gate:** see `evidence/gate-result.json`.", "",
             "No control is EVIDENCED by this pass: checklist GATE-01 needs the production path and GATE-03 an operational owner, "
             "and neither exists. Per-line status, notes, evidence digests and test outcomes are in `evidence/checklist_execution.json`.", ""]
    dim = None
    for ctl in audit["controls"]:
        if ctl["status_v4_2_0"] == "EVIDENCED":
            continue
        if ctl["dimension"] != dim:
            dim = ctl["dimension"]
            lines += ["", f"## {dim}", "", "| Control | 4.2.0 | 4.3.0 | Lines I/P/O/B | Remaining blockers (BLOCKED / OPEN lines) |", "|---|---|---|---|---|"]
        cid = ctl["check_id"].replace("INV-71-", "")
        st = ctl["v4_3_0_items"]
        rem = [e["note"] for e in execution if e["control"] == cid and e["kind"] == "IMP" and e["status"] in ("BLOCKED", "OPEN")]
        lines.append(f"| {ctl['check_id']} | {ctl['status_v4_2_0']} | {ctl['status']} | "
                     f"{st['IMPLEMENTED_UNREVIEWED']}/{st['PARTIAL']}/{st['OPEN']}/{st['BLOCKED']} | "
                     + ("; ".join(rem) if rem else "no BLOCKED/OPEN implementation line; PARTIAL lines and GATE-01/03 remain") + " |")
    lines += ["", "## Cross-cutting gaps", "", "| Gap | Lines I/P/O/B | BLOCKED / OPEN |", "|---|---|---|"]
    for x in sorted({e["control"] for e in execution if e["control"].startswith("INV71-X")}):
        its = [e for e in execution if e["control"] == x]
        st = {v: sum(1 for e in its if e["status"] == v) for v in cs.STATUS.values()}
        rem = [e["note"] for e in its if e["kind"] == "IMP" and e["status"] in ("BLOCKED", "OPEN")]
        lines.append(f"| {x} | {st['IMPLEMENTED_UNREVIEWED']}/{st['PARTIAL']}/{st['OPEN']}/{st['BLOCKED']} | {'; '.join(rem) or '-'} |")
    (PKG / "MISSING_COMPONENTS.md").write_text("\n".join(lines) + "\n")

    # --------------------------------------------------------- release manifest
    allf = [p for p in files(include_evidence=True) if p.relative_to(PKG).as_posix() not in
            ("evidence/release-manifest.json", "evidence/gate-result.json")]
    manifest = {"schema": "PK_HEAVYBOX_RELEASE_MANIFEST/1", "version": version, "generated": now,
                "files": {p.relative_to(PKG).as_posix(): sha(p) for p in allf},
                "tree_sha256": tree_digest(allf),
                # approvals sign this digest: the release minus the approval records themselves
                "approval_subject_sha256": tree_digest([p for p in allf if not p.relative_to(PKG).as_posix().startswith("governance/approvals/")]),
                "signature": None,
                "signature_status": "UNSIGNED - no managed signing key exists (INV71-X004-IMP-04 BLOCKED)"}
    (EV / "release-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    gate = subprocess.run([sys.executable, "-B", str(PKG / "tools" / "production_gate.py")], capture_output=True, text=True)
    print(json.dumps({"tests": counts, "items": item_totals, "controls": audit["summary"], "problems": len(problems),
                      "fuzz_findings": fz["total_findings"], "bench": br["gate"]["verdict"],
                      "gate": gate.stdout.strip().splitlines()[-1] if gate.stdout else gate.stderr[-300:]}, indent=1))
    return 1 if problems or counts["FAIL"] or counts["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
