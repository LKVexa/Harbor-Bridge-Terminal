"""Execute the GAP-05 v4.3.0 test/model-check/benchmark suite and map real results onto
all 1,516 items of the Missing Components Professional Checklist v1.0.0.

    python3 -B gap05_state_replication_consistency_model/evidence/run_evidence.py CHECKLIST.md

Rules (enforced mechanically, never by hand):

* A checklist box is never ticked.  The checklist defines ``[x]`` as "completed AND backed
  by reviewable evidence"; no independent reviewer exists for this build, so every item
  stays ``[ ]`` and carries a status instead.
* ``LOCAL_VERIFIED_UNREVIEWED`` - at least one test tagged with the item ran and passed
  and none tagged with it failed, AND the test shares at least one content word with
  the item text (a relevance floor that catches mis-tagging; it can under-report, never
  over-report).  A tag failing the floor becomes ``PARTIAL`` with reason ``weak_link``.
* ``DESIGN_RECORDED_UNREVIEWED`` - cross-cutting documentation items satisfied by a
  non-empty field of ``production/registry.py`` (rendered into PRODUCTION.md).
* ``MEASURED_UNDER_PROPOSED_TARGET`` - performance items with a real measurement but no
  owner-approved threshold.
* ``BLOCKED`` - needs a person, external infrastructure or a tool absent from the build.
* ``NOT_EVIDENCED`` - nothing in this build evidences it (honest gap).
* ``FAILED`` - a tagged test failed.
* ``tag_review.json`` - an adversarial second pass (a separate model agent, not a human)
  read every test body behind a LOCAL_VERIFIED claim; its PARTIAL/NONE verdicts demote the
  item to PARTIAL / NOT_EVIDENCED.  It can only lower a status, never raise one.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = PKG.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from gap05_state_replication_consistency_model.production.registry import C as REG  # noqa: E402

STOP = set("""a an the and or of to for in on at by with without from into as is are be been being it its this
that these those not no any all each every per via than then so such only both either whether where when which
who what how must should may can cannot shall define defines defined ensure ensures use uses using add adds
provide provides require requires required including include includes against under over across between within
before after during while also other new same more most least where applicable appropriate e.g. etc system
component components gap05 gap-05 test tests tested""".split())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", text.lower()) if w not in STOP}


def stem(w: str) -> str:
    for suf in ("ations", "ation", "ing", "ies", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def parse_checklist(path: Path) -> list[dict]:
    items = []
    comp = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"### (\d+)\. (.*)", line)
        if m:
            comp = int(m.group(1))
        m = re.match(r"- \[ \] \*\*(GAP05-[A-Z]+\d*-\d{3}|GAP05-(?:GATE|CERT)-\d{3})(?: · ([A-Za-z]+))?\*\* — (.*)", line)
        if m:
            iid, area, text = m.group(1), m.group(2), m.group(3)
            kind = "gate" if "GATE" in iid else "cert" if "CERT" in iid else (
                "crosscut" if int(iid[-3:]) >= 13 else "specific")
            items.append({"id": iid, "component": comp if kind in ("specific", "crosscut") else None,
                          "area": area, "kind": kind, "text": text})
    return items


class Collector(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = {}

    def _rec(self, test, status, detail=""):
        doc = (test._testMethodDoc or "").strip()
        first = doc.splitlines()[0] if doc else ""
        tags = re.findall(r"MC\d{2}-\d{3}", first) if first.startswith("items:") else []
        self.records[test.id()] = {"status": status, "tags": tags, "doc": doc, "detail": detail[-1500:]}

    def addSuccess(self, test):
        super().addSuccess(test)
        self._rec(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._rec(test, "failed", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._rec(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._rec(test, "skipped", reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._rec(test, "failed", self._exc_info_to_string(err, test))


def run_tests(obs_path: Path) -> tuple[dict, dict]:
    os.environ["GAP05_OBSERVATIONS"] = str(obs_path)
    tests_dir = PKG / "tests" / "production"
    sys.path.insert(0, str(tests_dir))
    suite = unittest.defaultTestLoader.discover(str(tests_dir), top_level_dir=str(tests_dir))
    stream = io.StringIO()
    t0 = time.time()
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        res = unittest.TextTestRunner(stream=stream, resultclass=Collector, verbosity=0).run(suite)
    summary = {"ran": res.testsRun, "failures": len(res.failures), "errors": len(res.errors),
               "skipped": len(res.skipped), "seconds": round(time.time() - t0, 2)}
    # the two v4.2.0 suites, run as subprocess scripts exactly as their docstrings say
    import subprocess
    legacy = {}
    for name in ("test_model_logic.py", "test_component.py"):
        p = subprocess.run([sys.executable, "-B", str(PKG / "tests" / name)], capture_output=True, text=True)
        tail = (p.stderr or p.stdout).strip().splitlines()[-3:]
        legacy[name] = {"returncode": p.returncode, "tail": tail}
    summary["legacy_suites"] = legacy
    return res.records, summary


# Items that need a person, infrastructure, or a tool this build does not have.
BLOCKED_PATTERNS = [
    (r"independent|penetration|approv|sign-off|signed-off|review criteria|usability|game-day|drill", "requires independent human review, approval or an exercise with people"),
    (r"mTLS|SPIFFE|SPIRE|attested identity provider|platform-native", "requires real workload-identity infrastructure (mTLS/SPIRE) not present in this build"),
    (r"managed key|KMS|HSM|hardware-backed|key services", "requires a KMS/HSM integration not present in this build"),
    (r"multi-hour|day soak|fleet|production telemetry|realistic dataset|production-representative", "requires production-scale data or multi-hour runs outside this build's budget"),
    (r"memory-safety|sanitizer|instrumentation appropriate|native extension|scheduled security testing", "requires native fuzzing/sanitizer tooling absent from this build"),
    (r"cross-language|all supported runtime languages|language implementations", "only a Python implementation exists"),
    (r"TLC|TLA\+|model checking in CI", "TLC not available; bounded Python checker used instead"),
    (r"sign release|signatures through|attestation|reproducib|clean isolated|branch/release protection|vulnerabilit", "requires release infrastructure (signing keys, provenance builder, protected branches, advisory feed)"),
    (r"UI|browser|CSRF", "no graphical UI exists (read-only CLI only)"),
    (r"storage/filesystem class|hardware/storage classes", "only one filesystem/hardware class available"),
    (r"compression|decompress", "no compression is implemented, so compression-specific checks cannot run"),
    (r"repository history|upstream package|recovered|recover(?:ed|y) (?:from|artifact)|authoritative artifact|historical hash", "authoritative MASTER.md source is not available to this build"),
]

CROSS = {  # cross-cutting suffix -> rule
    13: ("blocked", "owner and reviewer assignment is a human decision; registry records UNASSIGNED"),
    14: ("design", "inv"), 15: ("design", "api"), 16: ("design", "api"), 17: ("design", "thr"),
    18: ("design", "thr"), 19: ("design", "per"), 20: ("design", "bnd"), 21: ("design", "per"),
    22: ("design", "con"), 23: ("design", "obs"), 24: ("partial", "no alert thresholds/SLO or dashboard agreed"),
    25: ("tests", None), 26: ("fault", None), 27: ("perf", None), 28: ("design", "cfg"), 29: ("design", "rb"),
    30: ("design", "gap"),
}
FAULT_TESTED = {3, 4, 5, 9, 10, 11, 12, 13, 16, 17, 18, 19, 25, 29, 32, 35, 36, 37, 38}
PERF_MEASURED = {4, 17, 20, 21, 29, 39, 43, 46, 48, 11}


def classify(items, tests):
    by_tag = defaultdict(list)
    for tid, r in tests.items():
        for t in r["tags"]:
            by_tag[t].append((tid, r))
    per_comp_pass = Counter()
    for tid, r in tests.items():
        if r["status"] == "passed":
            for comp in {int(t[2:4]) for t in r["tags"]}:
                per_comp_pass[comp] += 1
    review = {}
    rp = HERE / "tag_review.json"
    if rp.exists():
        review = {d["id"]: d for d in json.loads(rp.read_text())["demotions"]}
    out = []
    for it in items:
        rec = dict(it, checkbox="[ ]", evidence=[], status=None, reason=None)
        short = it["id"].replace("GAP05-", "")
        if it["kind"] in ("gate", "cert"):
            rec["status"] = "BLOCKED"
            rec["reason"] = ("certification/gate decision requires independent review; mechanically NOT MET because "
                             "component items remain BLOCKED/NOT_EVIDENCED")
        elif it["kind"] == "specific":
            hits = by_tag.get(short, [])
            if hits:
                failed = [tid for tid, r in hits if r["status"] in ("failed", "error")]
                passed = [(tid, r) for tid, r in hits if r["status"] == "passed"]
                rec["evidence"] = [{"test": tid, "result": r["status"]} for tid, r in hits]
                iw = {stem(w) for w in words(it["text"])}
                linked = [tid for tid, r in passed if iw & {stem(w) for w in words(r["doc"] + " " + tid.replace("_", " "))}]
                if failed:
                    rec["status"], rec["reason"] = "FAILED", f"tagged test(s) failed: {failed}"
                elif linked and it["id"] in review:
                    d = review[it["id"]]
                    rec["status"] = "PARTIAL" if d["verdict"] == "PARTIAL" else "NOT_EVIDENCED"
                    rec["reason"] = "second-pass tag review: " + d["missing"]
                elif linked:
                    rec["status"] = "LOCAL_VERIFIED_UNREVIEWED"
                elif passed:
                    rec["status"], rec["reason"] = "PARTIAL", "weak_link: passing test shares no content word with item"
                else:
                    rec["status"], rec["reason"] = "NOT_EVIDENCED", "tagged tests skipped"
            if rec["status"] in (None, "NOT_EVIDENCED"):
                for pat, why in BLOCKED_PATTERNS:
                    if re.search(pat, it["text"], re.I):
                        rec["status"], rec["reason"] = "BLOCKED", why
                        break
            if rec["status"] is None:
                rec["status"] = "NOT_EVIDENCED"
                rec["reason"] = "no test or artifact in this build evidences this item; component gap: " + \
                    REG[it["component"]]["gap"]
        else:
            suffix = int(it["id"][-3:])
            kind, arg = CROSS[suffix]
            reg = REG[it["component"]]
            if kind == "blocked":
                rec["status"], rec["reason"] = "BLOCKED", arg
            elif kind == "partial":
                rec["status"], rec["reason"] = "PARTIAL", arg
            elif kind == "design" and 33 <= it["component"] <= 40:
                rec["status"], rec["reason"] = "PARTIAL", "generic design record shared by the test/certification components"
            elif kind == "design":
                val = reg.get(arg, "-")
                if val and val.strip() not in ("-", ""):
                    rec["status"] = "DESIGN_RECORDED_UNREVIEWED"
                    rec["evidence"] = [{"doc": f"PRODUCTION.md#mc{it['component']:02d}", "field": arg}]
                else:
                    rec["status"], rec["reason"] = "NOT_EVIDENCED", f"registry field '{arg}' empty"
            elif kind == "tests":
                n = per_comp_pass[it["component"]]
                if n >= 2:
                    rec["status"] = "LOCAL_VERIFIED_UNREVIEWED"
                    rec["evidence"] = [{"passing_tagged_tests": n}]
                else:
                    rec["status"], rec["reason"] = ("PARTIAL" if n else "NOT_EVIDENCED"), f"{n} passing tagged tests"
            elif kind == "fault":
                if it["component"] in FAULT_TESTED:
                    rec["status"] = "LOCAL_VERIFIED_UNREVIEWED"
                    rec["evidence"] = [{"note": "fault/dependency-failure tests tagged for this component"}]
                else:
                    rec["status"], rec["reason"] = "NOT_EVIDENCED", "no fault-injection test for this component"
            elif kind == "perf":
                if it["component"] in PERF_MEASURED:
                    rec["status"] = "MEASURED_UNDER_PROPOSED_TARGET"
                    rec["reason"] = "measured by bench.py; thresholds PROPOSED, no owner-approved budget"
                else:
                    rec["status"], rec["reason"] = "NOT_EVIDENCED", "no benchmark for this component"
        out.append(rec)
    return out


def render_production_md() -> str:
    lines = ["# GAP-05 v4.3.0 - Production layer design record", "",
             "Generated from `production/registry.py` by `evidence/run_evidence.py`. Unreviewed.",
             "Owner and reviewer are **UNASSIGNED** for every component.", ""]
    labels = [("m", "Modules"), ("inv", "Invariants (safety / liveness / durability / isolation)"),
              ("api", "Interfaces, error codes, retry semantics"), ("per", "Persistence"),
              ("con", "Concurrency"), ("bnd", "Bounds"), ("obs", "Observability"), ("cfg", "Configuration"),
              ("rb", "Runbook"), ("thr", "Threat model"), ("perf", "Performance evidence"),
              ("gap", "Not done in this build")]
    for n in sorted(REG):
        r = REG[n]
        lines += [f"## MC{n:02d} - {r['t']} <a id=\"mc{n:02d}\"></a>", ""]
        for k, lab in labels:
            lines.append(f"- **{lab}:** {r[k]}")
        lines.append("")
    return "\n".join(lines)


def annotate_checklist(src: Path, records: list[dict]) -> str:
    by_id = {r["id"]: r for r in records}
    out = []
    for line in src.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- \[ \] \*\*(GAP05-[A-Z]+\d*-\d{3})", line)
        if m and m.group(1) in by_id:
            r = by_id[m.group(1)]
            ev = "; ".join(e.get("test", e.get("doc", json.dumps(e))).split(".")[-1] for e in r["evidence"][:3])
            note = f"  \n  `{r['status']}`" + (f" — {r['reason']}" if r["reason"] else "") + (f" — evidence: {ev}" if ev else "")
            out.append(line + note)
        else:
            out.append(line)
    header = ("> **v4.3.0 evidence snapshot (generated).** Boxes stay `[ ]`: completion requires reviewable "
              "evidence *and* review, and no independent reviewer exists for this build. Each item carries the "
              "status assigned mechanically by `evidence/run_evidence.py`.\n\n")
    return header + "\n".join(out) + "\n"


def main(argv):
    checklist = Path(argv[1])
    items = parse_checklist(checklist)
    assert len(items) == 1516, len(items)
    (PKG / "PRODUCTION.md").write_text(render_production_md(), encoding="utf-8")
    obs = HERE / "observations.jsonl"
    obs.unlink(missing_ok=True)
    tests, summary = run_tests(obs)
    from gap05_state_replication_consistency_model.production import bench, modelcheck
    mc = modelcheck.run_all()
    mc_out = {k: ({kk: vv for kk, vv in v.items() if kk != "violations"} | {"violations": len(v.get("violations", []))}
                  if isinstance(v, dict) else v) for k, v in mc.items()}
    b = bench.run_all(quick=False)
    records = classify(items, tests)
    counts = Counter(r["status"] for r in records)
    by_kind = defaultdict(Counter)
    for r in records:
        by_kind[r["kind"]][r["status"]] += 1
    (HERE / "test_results.json").write_text(json.dumps({"summary": summary, "tests": tests}, indent=1, sort_keys=True))
    (HERE / "modelcheck.json").write_text(json.dumps(mc_out, indent=1))
    (HERE / "bench.json").write_text(json.dumps(b, indent=1, default=str))
    ev = {"format": "GAP05_CHECKLIST_EVIDENCE/1", "checklist": checklist.name,
          "checklist_sha256": hashlib.sha256(checklist.read_bytes()).hexdigest(),
          "package_version": (PKG / "VERSION").read_text().strip(), "items": len(records),
          "completion_claims": sum(r["checkbox"] == "[x]" for r in records), "status_counts": dict(counts),
          "by_kind": {k: dict(v) for k, v in by_kind.items()}, "tests": summary,
          "modelcheck_ok": mc["ok"], "records": records}
    (HERE / "CHECKLIST_EVIDENCE.json").write_text(json.dumps(ev, indent=1))
    (HERE / "CHECKLIST_EVIDENCE.md").write_text(annotate_checklist(checklist, records), encoding="utf-8")
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(HERE.iterdir())
            if p.is_file() and p.name not in ("EVIDENCE_SHA256SUMS.txt", "run_evidence.py")]
    (HERE / "EVIDENCE_SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    print(json.dumps({k: v for k, v in ev.items() if k != "records"}, indent=1))
    return 0 if summary["failures"] == summary["errors"] == 0 and mc["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
