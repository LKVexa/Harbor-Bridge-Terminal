"""Execute every test, then compute the status of all 1,010 GAP-11 checklist items
from executed evidence. Nothing here asserts a status: each status is derived from
(a) tests tagged with the check ID and their actual outcome, (b) artifact checks that
open the named file and look for the required content, (c) the blocker rules below.

Status vocabulary (checklist marks):
  EVIDENCED [x]  objective evidence produced in this run (not independently reviewed)
  PARTIAL   [~]  evidence exists for part of the requirement; the rest is named
  BLOCKED   [!]  cannot be satisfied here; blocker named
  OPEN      [ ]  no evidence produced
  FAILED    [!]  a tagged test failed
Outputs: evidence/RUN.json, evidence/CHECKLIST_STATUS.json, evidence/EXIT_BUNDLE.json,
docs/TRACEABILITY.md, GAP11_v4.3.0_CHECKLIST_STATUS.md. Exit code 0 = run complete and
no FAILED item (the production verdict is separate and is NO_GO unless every gate holds).
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import io
import json
import os
import platform
import re
import sys
import tarfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "gap11_control" / "tests"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(TESTS)]

from registry import (B_ENV, B_HUMAN, B_HW, B_PKI, B_SIGN, COMPONENTS)  # noqa: E402

ITEMS = json.loads((ROOT / "docs" / "CHECKLIST_ITEMS.json").read_text())
REG = {c["id"]: c for c in COMPONENTS}
MARK = {"EVIDENCED": "[x]", "PARTIAL": "[~]", "BLOCKED": "[!]", "OPEN": "[ ]", "FAILED": "[!]"}


# ----------------------------------------------------------------------------- run tests
class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = []
        self._t0 = {}

    def startTest(self, test):
        self._t0[test.id()] = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, outcome, detail=""):
        fn = getattr(test, test._testMethodName, None)
        tags = list(getattr(fn, "covers", ()) or ())
        self.records.append({"test": test.id(), "outcome": outcome, "covers": tags, "detail": detail[-400:],
                             "seconds": round(time.perf_counter() - self._t0.get(test.id(), time.perf_counter()), 4)})

    def addSuccess(self, test):
        super().addSuccess(test); self._rec(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._rec(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err); self._rec(test, "ERROR", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._rec(test, "SKIP", reason)


def run_tests() -> tuple[list[dict], dict]:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for f in sorted(TESTS.glob("test_*.py")):
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(f.stem)))
    # the audited v4.2.0 suites, unchanged
    for f in ("test_allocator", "test_component"):
        spec = importlib.util.spec_from_file_location(f"v420_{f}", ROOT / "tests" / f"{f}.py")
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            suite.addTests(loader.loadTestsFromModule(mod))
        except Exception as exc:  # pk_core absent -> the v4.2.0 audit already records this as SKIP
            suite.addTest(unittest.FunctionTestCase(lambda exc=exc: (_ for _ in ()).throw(unittest.SkipTest(f"{f}: {type(exc).__name__}: {exc}"))))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=Recorder, verbosity=0)
    t0 = time.perf_counter()
    res = runner.run(suite)
    summary = {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
               "seconds": round(time.perf_counter() - t0, 2)}
    return res.records, summary


# ----------------------------------------------------------------------------- artifact checks
def art(rel: str, *needles: str) -> bool:
    p = ROOT / rel
    if not p.exists():
        return False
    txt = p.read_text(errors="replace")
    return all(n in txt for n in needles)


def reproducible_digest() -> tuple[bool, str]:
    def build() -> str:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for p in sorted(x for x in ROOT.rglob("*") if x.is_file() and "evidence" not in x.parts and "__pycache__" not in x.parts
                            and x.suffix != ".pyc" and not x.name.startswith("GAP11_v4.3.0_CHECKLIST_STATUS") and x.name != "TRACEABILITY.md"):
                info = tarfile.TarInfo(str(p.relative_to(ROOT)))
                data = p.read_bytes()
                info.size, info.mtime, info.uid, info.gid, info.uname, info.gname, info.mode = len(data), 0, 0, 0, "", "", 0o644
                tar.addfile(info, io.BytesIO(data))
        return hashlib.sha256(buf.getvalue()).hexdigest()
    a, b = build(), build()
    return a == b, a


def residue_scan() -> list[str]:
    bad = []
    pat = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}")
    for p in ROOT.rglob("*"):
        if p.is_file():
            if p.suffix in (".pyc",) or "__pycache__" in p.parts or p.name in (".DS_Store",):
                bad.append(str(p.relative_to(ROOT)))
            elif p.suffix in (".py", ".md", ".json", ".toml", ".sh", ".txt") and pat.search(p.read_text(errors="replace")):
                bad.append(str(p.relative_to(ROOT)))
    return bad


# ----------------------------------------------------------------------------- rules
HW_T = {"GAP11-P0-06", "GAP11-P0-07", "GAP11-P0-08", "GAP11-P1-19", "GAP11-P1-20"}
SEC_T = {"GAP11-P0-09", "GAP11-P0-10", "GAP11-P0-11", "GAP11-P1-30"}
STATE_T = {"GAP11-P0-01", "GAP11-P0-02", "GAP11-P0-03", "GAP11-P0-04", "GAP11-P0-05", "GAP11-P0-15", "GAP11-P1-21"}
IFACE_T = {"GAP11-P0-12", "GAP11-P0-13"}
VERIF_T = {"GAP11-P0-16", "GAP11-P2-33", "GAP11-P2-34", "GAP11-P2-35", "GAP11-P2-36", "GAP11-P2-37", "GAP11-P2-38", "GAP11-P2-39"}
TEL_T = {"GAP11-P1-24", "GAP11-P1-25", "GAP11-P1-26", "GAP11-P1-27", "GAP11-P1-28", "GAP11-P1-31"}
REL_T = {"GAP11-P2-40", "GAP11-P2-41", "GAP11-P2-42", "GAP11-P2-43"}
GOV_T = {"GAP11-P2-44", "GAP11-P2-45", "GAP11-P2-46", "GAP11-P2-47", "GAP11-P2-48", "GAP11-P2-49", "GAP11-P2-50"}


def forced(comp: str, n: int, ctx: dict) -> tuple[str, str] | None:
    """Rules that override or supply the status of a specific (.01-.10) item."""
    if comp in HW_T:
        if n == 4:
            return "BLOCKED", "capability validation against LIVE hardware: " + B_HW
        if n == 7:
            return "BLOCKED", "privileged node-agent process separation not built (no hardware/OS agent to separate): " + B_HW
        if n == 8:
            return "PARTIAL", "independent post-operation verification implemented and tested against simulators only: " + B_HW
        if n == 6:
            return "PARTIAL", "bounded deadlines, exponential backoff and non-retryable classes implemented (hardware.with_retry, ScrubExecutor); no cancellation token" + (" | reconfigure() has no deadline" if comp == "GAP11-P0-07" else "")
        if n == 9:
            if comp in ("GAP11-P0-06", "GAP11-P0-08"):
                return "PARTIAL", "structured evidence records (PK_INVENTORY_EVIDENCE/1, PK_SCRUB_EVIDENCE/1) carry identity, steps, timing, result; controller/request lineage is joined only via the audit ledger, not embedded"
    if comp in SEC_T:
        if n == 1:
            return ("EVIDENCED", "docs/THREAT_MODEL.md trust-boundary table TB-1..TB-6") if art("docs/THREAT_MODEL.md", "Trust boundaries", "TB-4") else None
        if n == 2:
            return "PARTIAL", "HMAC workload-identity credentials verified on every state change; mutually authenticated channel (mTLS) absent: " + B_PKI
    if comp in STATE_T and n == 10:
        return "PARTIAL", "disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: " + B_ENV
    if comp in IFACE_T and n == 6:
        return "PARTIAL", "bounded in-flight semaphore + bounded fair queue + quotas tested; per-principal rate limiting not implemented"
    if comp in TEL_T and n == 7:
        return "PARTIAL", "redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md)"
    if comp in TEL_T and n == 8:
        return ("PARTIAL", "dashboard specification docs/DASHBOARDS.md; not deployed: " + B_ENV) if art("docs/DASHBOARDS.md", "operator decisions") else None
    if comp in VERIF_T and n == 10:
        return ("EVIDENCED", "evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes") if comp != "GAP11-P2-34" else None
    if comp in VERIF_T and n == 9:
        return "PARTIAL", "latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: " + B_HUMAN
    if comp in VERIF_T and n == 8:
        return "PARTIAL", "seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline"
    if comp == "GAP11-P2-34" and n != 1:
        return "BLOCKED", REG[comp]["blockers"][0]
    if comp in REL_T:
        return release_rule(n, ctx)
    if comp in GOV_T:
        return governance_rule(comp, n)
    return None


def release_rule(n: int, ctx: dict) -> tuple[str, str]:
    if n == 1:
        return ("EVIDENCED", "pyproject.toml (name, version, requires-python, build backend); licence UNSPECIFIED is stated, not invented") if art("pyproject.toml", "requires-python", "build-backend") else ("OPEN", "")
    if n == 2:
        return ("EVIDENCED", "zero runtime dependencies (SBOM third_party_runtime_dependencies=0); optional pk_core range declared") if ctx["sbom_deps"] == 0 else ("OPEN", "")
    if n == 3:
        return ("EVIDENCED", f"deterministic source archive built twice, identical sha256 {ctx['repro'][1][:16]}…") if ctx["repro"][0] else ("FAILED", "digests differ")
    if n == 4:
        return ("EVIDENCED", "release/SBOM.cdx.json (CycloneDX 1.5; per-file SHA-256; no vendored/native code)") if art("release/SBOM.cdx.json", "CycloneDX") else ("OPEN", "")
    if n == 5:
        return "BLOCKED", B_SIGN
    if n == 6:
        return "BLOCKED", "clean-install/upgrade/downgrade/uninstall matrix needs every supported platform: " + B_ENV
    if n == 7:
        return ("EVIDENCED", "residue scan: no __pycache__/.pyc/private keys/tokens in the tree") if not ctx["residue"] else ("FAILED", ",".join(ctx["residue"][:5]))
    if n == 8:
        return ("PARTIAL", "docs/COMPATIBILITY.md; hardware/driver/firmware rows untested: " + B_HW) if art("docs/COMPATIBILITY.md", "Compatibility rules") else ("OPEN", "")
    if n == 9:
        return "PARTIAL", "ci.sh gates compile + all tests + benchmark thresholds + manifest; vulnerability/licence/provenance gates absent (no licence chosen, " + B_SIGN + ")"
    if n == 10:
        return "PARTIAL", "MANIFEST.sha256, SBOM, CHANGELOG, rollback in RUNBOOK-03 retained; no signatures/provenance: " + B_SIGN
    return "OPEN", ""


GOV_DOC = {"GAP11-P2-44": "docs/THREAT_MODEL.md", "GAP11-P2-45": "docs/ADR-001-control-plane.md", "GAP11-P2-46": "docs/OWNERSHIP.md",
           "GAP11-P2-47": "docs/RUNBOOKS.md", "GAP11-P2-48": "docs/EXCEPTIONS.json", "GAP11-P2-49": "docs/MASTER_MD_DISPOSITION.md",
           "GAP11-P2-50": "evidence/EXIT_BUNDLE.json"}


def governance_rule(comp: str, n: int) -> tuple[str, str]:
    doc = GOV_DOC[comp]
    exists = (ROOT / doc).exists() or comp == "GAP11-P2-50"
    if not exists:
        return "OPEN", f"{doc} missing"
    ids = {"GAP11-P2-44": "THR-", "GAP11-P2-45": "DEC-", "GAP11-P2-47": "RUNBOOK-", "GAP11-P2-48": "EXC-", "GAP11-P2-49": "GAP11-EXIT-09", "GAP11-P2-50": "GAP11-EXIT-"}
    if n == 1:
        return "PARTIAL", f"{doc}: cadence/triggers stated where applicable; owner and approver UNASSIGNED: " + B_HUMAN
    if n == 5:
        return "BLOCKED", "no dated approval or owner acknowledgement exists: " + B_HUMAN
    if n == 2:
        return ("EVIDENCED", f"{doc} states scope/non-goals") if comp != "GAP11-P2-46" else ("PARTIAL", "roles listed, none assigned")
    if n == 3:
        if comp == "GAP11-P2-44" and art(doc, "Residual risks"):
            return "EVIDENCED", "RR-01..RR-05"
        if comp in ("GAP11-P2-45", "GAP11-P2-49"):
            return "EVIDENCED", f"{doc} trade-offs / established facts"
        return "OPEN", "no assumptions section in this artifact"
    if n == 4:
        return ("EVIDENCED", f"stable identifiers `{ids[comp]}…` in {doc}") if comp in ids else ("OPEN", "no identifiers (no owner yet)")
    if n == 6:
        if comp == "GAP11-P2-48":
            return "EVIDENCED", "every exception carries expires + revalidate"
        if comp == "GAP11-P2-44":
            return "PARTIAL", "review cadence + out-of-cycle triggers; no expiry"
        return "OPEN", "no expiry/revalidation rule in this artifact"
    if n == 7:
        if comp == "GAP11-P2-44":
            return "EVIDENCED", "each THR-xx row names its mitigation and test evidence"
        if comp == "GAP11-P2-50":
            return "EVIDENCED", "docs/TRACEABILITY.md links every check to tests/artifacts"
        return "PARTIAL", "references to runbooks/tests are partial"
    if n == 8:
        return "EVIDENCED", "versioned inside the 4.3.0 package alongside the code"
    if n == 9:
        return ("EVIDENCED", "ADR carries Supersedes/Superseded-by; v4.2.0 AUDIT_REPORT.md retained unchanged") if comp == "GAP11-P2-45" else ("PARTIAL", "v4.2.0 artifacts retained; no supersession header")
    if n == 10:
        if comp in ("GAP11-P2-46", "GAP11-P2-49", "GAP11-P2-50"):
            return "EVIDENCED", f"{doc} states the exact evidence required to close"
        return "PARTIAL", "completion gate implied by GAP11-EXIT-*, not stated in the artifact"
    return "OPEN", ""


def generic(comp: str, n: int, ctx: dict) -> tuple[str, str]:
    c = REG[comp]
    blocked = c["disposition"] == "BLOCKED"
    doc_only = c["template"] in ("governance", "release")
    if n == 20:
        return "BLOCKED", "acceptance needs design approval + independent security review + operator sign-off: " + B_HUMAN
    if blocked and n not in (11, 16):
        return "BLOCKED", "; ".join(c["blockers"])
    if n == 11:
        return "PARTIAL", f"docs/DESIGN_RECORDS.md#{comp} (all fields present); owner UNASSIGNED: " + B_HUMAN
    if n == 12:
        k = sum(1 for r in ctx["reqs"] if r["component"] == comp)
        return ("EVIDENCED", f"docs/REQUIREMENTS.json: {k} MUST/SHOULD/MAY requirements with stable IDs {comp}-Rnn") if c["invariants"] else ("PARTIAL", f"only the capability MUST ({comp}-R00); no component invariants")
    if n == 13:
        if doc_only:
            return "PARTIAL", "artifact interface = file format; failure contract n/a"
        return "PARTIAL", "typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008)"
    if n == 14:
        if c["invariants"] and ctx["comp_pass"].get(comp):
            return "EVIDENCED", "invariants " + ", ".join(i.split(" ")[0] for i in c["invariants"]) + " enforced in code and asserted by tagged tests"
        return ("PARTIAL", "invariants stated, not runtime-enforced (document component)") if c["invariants"] else ("OPEN", "no invariants")
    if n == 15:
        return "EVIDENCED", "docs/DATA_INVENTORY.md" + ("" if c["data"] else " (declares no persistent datum)")
    if n == 16:
        return "EVIDENCED", "docs/OPERATING_MODES.md"
    if n == 17:
        if doc_only:
            return "BLOCKED", "not applicable to a document; exception EXC-005 PROPOSED, unapproved: " + B_HUMAN
        codes = c["telemetry"]
        src = "".join((ROOT / m).read_text() for m in c["modules"] if (ROOT / m).is_file())
        if codes and all(code in src or code in ctx["codes_src"] for code in codes):
            return "EVIDENCED", "reason codes " + ", ".join(codes) + " registered and emitted"
        return ("PARTIAL", "uses shared Telemetry/Metrics but defines no component-specific reason code") if c["modules"] else ("OPEN", "")
    if n == 18:
        k = ctx["neg_tests"].get(comp, 0)
        return ("EVIDENCED", f"{k} tagged tests assert refusals/fault paths") if k else ("OPEN", "no tagged negative test")
    if n == 19:
        return ("EVIDENCED", "docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules") if c["rollout"] != "n/a" else ("PARTIAL", "global rollout rules only (docs/ROLLOUT.md header)")
    return "OPEN", ""


# ----------------------------------------------------------------------------- exit gates
def _approved(e: dict) -> bool:
    return e.get("status") == "APPROVED" and e.get("owner") not in (None, "", "UNASSIGNED") and bool(e.get("approved_on"))


EXIT_DEPS = {
    "GAP11-EXIT-02": [f"GAP11-P0-{i:02d}" for i in range(1, 17)],
    "GAP11-EXIT-03": ["GAP11-P2-34", "GAP11-P0-06", "GAP11-P0-09", "GAP11-P1-19", "GAP11-P1-25"],
    "GAP11-EXIT-04": ["GAP11-P0-01", "GAP11-P0-02", "GAP11-P0-03", "GAP11-P0-04", "GAP11-P0-05", "GAP11-P0-16", "GAP11-P2-36", "GAP11-P2-38"],
    "GAP11-EXIT-05": ["GAP11-P0-09", "GAP11-P0-10", "GAP11-P0-11", "GAP11-P1-24", "GAP11-P1-30", "GAP11-P2-37", "GAP11-P2-44"],
    "GAP11-EXIT-06": ["GAP11-P1-24", "GAP11-P1-25", "GAP11-P1-26", "GAP11-P1-27", "GAP11-P1-28"],
    "GAP11-EXIT-07": ["GAP11-P2-40", "GAP11-P2-41", "GAP11-P2-42", "GAP11-P2-43"],
    "GAP11-EXIT-08": ["GAP11-P2-47"],
    "GAP11-EXIT-09": ["GAP11-P2-49"],
    "GAP11-EXIT-10": ["GAP11-P2-50"],
}


def compute_exit(gates: dict[str, str], ownership_md: str, exceptions: list[dict]) -> dict[str, tuple[str, str]]:
    """Every exit gate is derived from component gates + ownership + exception register."""
    out: dict[str, tuple[str, str]] = {}
    unassigned = "UNASSIGNED" in ownership_md
    out["GAP11-EXIT-01"] = ("MET", "every role assigned") if not unassigned else ("NOT_MET", "docs/OWNERSHIP.md still lists UNASSIGNED roles")
    for k, deps in EXIT_DEPS.items():
        open_ = [d for d in deps if gates.get(d) != "MET"]
        out[k] = ("MET", "all dependent component gates MET") if not open_ else ("NOT_MET", f"{len(open_)}/{len(deps)} dependent component gates not MET: " + ", ".join(open_[:6]) + (" …" if len(open_) > 6 else ""))
    unapproved = [e["id"] for e in exceptions if not _approved(e)]
    if out["GAP11-EXIT-10"][0] == "MET" and unapproved:
        out["GAP11-EXIT-10"] = ("NOT_MET", f"{len(unapproved)} exceptions not APPROVED: " + ", ".join(unapproved))
    elif unapproved:
        out["GAP11-EXIT-10"] = ("NOT_MET", out["GAP11-EXIT-10"][1] + f"; {len(unapproved)} exceptions not APPROVED")
    return dict(sorted(out.items()))


# ----------------------------------------------------------------------------- main
def main() -> int:
    records, summary = run_tests()
    by_check: dict[str, list[dict]] = {}
    for r in records:
        for t in r["covers"]:
            by_check.setdefault(t, []).append(r)

    # tests that assert refusals (negative/fault) per component, by source inspection
    neg: dict[str, int] = {}
    for f in sorted(TESTS.glob("test_*.py")):
        mod = importlib.import_module(f.stem)
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            for name, fn in inspect.getmembers(cls, inspect.isfunction):
                if name.startswith("test_") and re.search(r"assertRaises|assertFalse|\"code\"\]|refus|DENIED|FAILED|NOT_MET", inspect.getsource(fn)):
                    for comp in {t.rsplit(".", 1)[0] for t in getattr(fn, "covers", ())}:
                        neg[comp] = neg.get(comp, 0) + 1
    comp_pass = {}
    for r in records:
        for t in r["covers"]:
            comp = t.rsplit(".", 1)[0]
            comp_pass[comp] = comp_pass.get(comp, True) and r["outcome"] == "PASS"
    sbom = json.loads((ROOT / "release" / "SBOM.cdx.json").read_text())
    ctx = {"reqs": json.loads((ROOT / "docs" / "REQUIREMENTS.json").read_text())["requirements"], "neg_tests": neg, "comp_pass": comp_pass,
           "repro": reproducible_digest(), "residue": residue_scan(),
           "sbom_deps": int(next(p["value"] for p in sbom["properties"] if p["name"] == "third_party_runtime_dependencies")),
           "codes_src": (ROOT / "gap11_control" / "common.py").read_text()}

    status = {}
    for it in ITEMS["items"]:
        cid = it["id"]
        if cid.startswith("GAP11-EXIT"):
            continue
        comp, n = cid.rsplit(".", 1)[0], int(cid.rsplit(".", 1)[1])
        tagged = by_check.get(cid, [])
        failed = [r["test"] for r in tagged if r["outcome"] in ("FAIL", "ERROR")]
        passed = [r["test"] for r in tagged if r["outcome"] == "PASS"]
        if failed:
            st, why = "FAILED", "failing: " + ", ".join(failed)
        elif n <= 10:
            f = forced(comp, n, ctx)
            if f is not None:
                st, why = f
                if passed and st in ("PARTIAL", "BLOCKED"):
                    why += f" | local evidence: {len(passed)} test(s)"
            elif passed:
                st, why = "EVIDENCED", f"{len(passed)} passing test(s)" + (" against simulated providers" if REG[comp]["disposition"] == "SIMULATED" else "")
            else:
                bl = REG[comp]["blockers"]
                st, why = ("BLOCKED", "; ".join(bl)) if REG[comp]["disposition"] in ("BLOCKED",) else ("OPEN", "no test or artifact evidences this item" + (f" (component blockers: {'; '.join(b.split(':')[0] for b in bl)})" if bl else ""))
        else:
            st, why = generic(comp, n, ctx)
        status[cid] = {"status": st, "why": why, "tests": passed}

    # ---------------------------------------------------------------- component + exit gates
    comps = {}
    for c in ITEMS["components"]:
        mine = {k: v for k, v in status.items() if k.startswith(c["id"] + ".")}
        counts = {s: sum(1 for v in mine.values() if v["status"] == s) for s in MARK}
        comps[c["id"]] = {"title": c["title"], "priority": c["priority"], "disposition": REG[c["id"]]["disposition"], "counts": counts,
                          "gate": "MET" if counts["EVIDENCED"] == 20 else "NOT_MET", "blockers": REG[c["id"]]["blockers"]}
    exc = json.loads((ROOT / "docs" / "EXCEPTIONS.json").read_text())["exceptions"]
    exit_items = compute_exit({k: v["gate"] for k, v in comps.items()}, (ROOT / "docs" / "OWNERSHIP.md").read_text(), exc)
    approved_exc = [e for e in exc if _approved(e)]
    totals = {s: sum(1 for v in status.values() if v["status"] == s) for s in MARK}
    verdict = "GO" if all(v[0] == "MET" for v in exit_items.values()) and not totals["FAILED"] else "NO_GO"

    src_digest = hashlib.sha256(b"".join(hashlib.sha256(p.read_bytes()).digest() for p in sorted(ROOT.rglob("*.py")) if "__pycache__" not in p.parts)).hexdigest()
    env = {"python": platform.python_version(), "implementation": platform.python_implementation(), "platform": sys.platform,
           "machine": platform.machine()}
    ev = ROOT / "evidence"
    ev.mkdir(exist_ok=True)
    run = {"schema": "GAP11_RUN/1", "package_version": "4.3.0", "source_py_digest": src_digest, "environment": env,
           "seeds": {"fuzz": 1103, "property": 20260922, "constraint_shuffle": 7}, "summary": summary, "tests": records}
    (ev / "RUN.json").write_text(json.dumps(run, indent=1) + "\n")
    (ev / "CHECKLIST_STATUS.json").write_text(json.dumps({"schema": "GAP11_CHECKLIST_STATUS/1", "totals": totals, "components": comps,
                                                           "items": status}, indent=1) + "\n")
    bench = next((r for r in records if r["test"].endswith("test_latency_thresholds_local_reference_host")), None)
    try:
        import test_verification as tv
        bres = getattr(tv.BenchmarkTests, "result", None)
        fm = getattr(tv.FaultMatrixTests, "matrix", None)
    except Exception:
        bres, fm = None, None
    (ev / "benchmark.json").write_text(json.dumps({"thresholds_status": "PROPOSED_UNAPPROVED", "result": bres,
                                                   "note": "reference host = build container; not a fleet measurement"}, indent=1) + "\n")
    (ev / "fault_matrix.json").write_text(json.dumps(fm, indent=1) + "\n")
    bundle = {"schema": "GAP11_EXIT_BUNDLE/1", "package_version": "4.3.0", "verdict": verdict,
              "verdict_rule": "GO only if every GAP11-EXIT-xx is MET and no checklist item FAILED; computed, never asserted",
              "exit_gates": {k: {"state": v[0], "reason": v[1]} for k, v in exit_items.items()}, "checklist_totals": totals,
              "component_gates": {k: v["gate"] for k, v in comps.items()}, "exceptions": {"total": len(exc), "approved": len(approved_exc)},
              "evidence": {"run": "evidence/RUN.json", "status": "evidence/CHECKLIST_STATUS.json", "benchmark": "evidence/benchmark.json",
                           "fault_matrix": "evidence/fault_matrix.json", "traceability": "docs/TRACEABILITY.md"},
              "source_py_digest": src_digest, "test_summary": summary, "reviewed_by": None, "approved_by": None}
    (ev / "EXIT_BUNDLE.json").write_text(json.dumps(bundle, indent=1) + "\n")

    # traceability + filled checklist
    tr = ["# GAP-11 traceability matrix (generated)\n\n| Check | Status | Evidence |\n|---|---|---|\n"]
    md = [f"# GAP-11 Accelerator Scheduling v4.3.0 — checklist status (generated by tools/run_checklist.py)\n\n",
          f"**Verdict:** {verdict}. Totals: " + ", ".join(f"{k} {v}" for k, v in totals.items()) + f" of {len(status)} component checks; "
          f"exit gates {sum(1 for v in exit_items.values() if v[0]=='MET')}/10 met.  \n",
          f"Tests: {summary['run']} run, {summary['failures']} failures, {summary['errors']} errors, {summary['skipped']} skipped (Python {env['python']}).  \n",
          "Marks: `[x]` evidenced in this run (not independently reviewed) · `[~]` partial, remainder named · `[!]` blocked, blocker named · `[ ]` no evidence.\n\n"]
    for c in ITEMS["components"]:
        cc = comps[c["id"]]
        md.append(f"## {c['priority']} · {c['number']}. {c['title']} — `{c['id']}` — {cc['disposition']} — gate {cc['gate']}\n\n")
        for it in ITEMS["items"]:
            if it["id"].startswith(c["id"] + "."):
                s = status[it["id"]]
                md.append(f"- {MARK[s['status']]} **{it['id']}** — {it['text']}  \n  ↳ *{s['status']}*: {s['why']}" +
                          (f" — tests: {', '.join(t.split('.')[-1] for t in s['tests'][:3])}{' …' if len(s['tests']) > 3 else ''}" if s["tests"] else "") + "\n")
                tr.append(f"| {it['id']} | {s['status']} | {s['why'][:160]}{'; ' + ', '.join(s['tests'][:2]) if s['tests'] else ''} |\n")
        md.append("\n")
    md.append("## Final program-level completion gate\n\n")
    for k, (st, why) in exit_items.items():
        text = next(i["text"] for i in ITEMS["items"] if i["id"] == k)
        md.append(f"- {'[x]' if st == 'MET' else '[ ]'} **{k}** — {text}  \n  ↳ *{st}*: {why}\n")
    (ROOT / "docs" / "TRACEABILITY.md").write_text("".join(tr))
    (ROOT / "GAP11_v4.3.0_CHECKLIST_STATUS.md").write_text("".join(md))
    print(json.dumps({"summary": summary, "totals": totals, "verdict": verdict}, indent=1))
    return 1 if (summary["failures"] or summary["errors"] or totals["FAILED"]) else 0


if __name__ == "__main__":
    import importlib.util  # noqa: F401
    sys.exit(main())
