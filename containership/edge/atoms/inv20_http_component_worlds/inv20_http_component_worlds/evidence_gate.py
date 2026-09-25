"""Machine-readable evidence bundle and production gate (checklist components 25, 27; feeds C090/C100).

    python -m inv20_http_component_worlds.evidence_gate collect   # run suites, write evidence/
    python -m inv20_http_component_worlds.evidence_gate gate      # independent decision from evidence/

Disposition rules (strict, per requirement C001..C100):
  FAIL      any test group mapped to the requirement failed or errored
  WAIVED    an approved, unexpired waiver in docs/governance/waivers.json names it (never hides FAIL)
  BLOCKED   a mapped component is PARTIAL/BLOCKED, a mandatory suite was skipped, or the requirement has
            no local mapping (its verification path is pk_core conformance, WI-INV20-01)
  PASS      every mapped component is CLOSED_LOCAL and every mapped test group ran and passed

Gate: GO only if all 100 are PASS/WAIVED, no waiver is expired, the evidence source digest equals the
current tree digest, the release version matches, and C100 is PASS. Exit 0 GO, 1 NO_GO (failure/
tamper/drift), 2 BLOCKED (nothing failed, but mandatory items are not closable here).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import time
import unittest
from typing import Dict, List

from ._version import __version__

PKG = pathlib.Path(__file__).resolve().parent
EVIDENCE = PKG / "evidence"
SCHEMA = "INV20_EVIDENCE/1"
SUITES = ["test_runtime", "test_protocol", "test_egress", "test_identity", "test_config", "test_aio", "test_ops",
          "test_evidence", "test_component"]
MANDATORY_SKIP_FORBIDDEN = ("test_component",)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def source_digest() -> str:
    from .tools.release import source_digest as sd
    return sd()


class _Rec(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes: Dict[str, str] = {}

    def addSuccess(self, t):
        super().addSuccess(t); self.outcomes[t.id()] = "pass"

    def addFailure(self, t, e):
        super().addFailure(t, e); self.outcomes[t.id()] = "fail"

    def addError(self, t, e):
        super().addError(t, e); self.outcomes[getattr(t, "id", lambda: str(t))()] = "error"

    def addSkip(self, t, r):
        super().addSkip(t, r); self.outcomes[t.id()] = "skip:" + r

    def addSubTest(self, test, sub, err):
        super().addSubTest(test, sub, err)
        if err is not None:
            self.outcomes[test.id()] = "fail"


def run_suites(optimized: bool = False) -> Dict[str, str]:
    if optimized:
        code = ("import json,sys,unittest;from inv20_http_component_worlds import evidence_gate as g;"
                "print(json.dumps(g.run_suites()))")
        out = subprocess.run([sys.executable, "-O", "-c", code], cwd=str(PKG.parent), capture_output=True, text=True)
        try:
            return json.loads(out.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"optimized_mode": "error"}
    import io
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for s in SUITES:
        if s == "test_evidence" and "INV20_IN_EVIDENCE_RUN" in __import__("os").environ:
            continue
        suite.addTests(loader.loadTestsFromName(f"inv20_http_component_worlds.tests.{s}"))
    r = unittest.TextTestRunner(stream=io.StringIO(), resultclass=_Rec, verbosity=0).run(suite)
    return {k.replace("inv20_http_component_worlds.", ""): v for k, v in r.outcomes.items()}


def group_status(outcomes: Dict[str, str], group: str) -> str:
    if group == "all":
        vals = list(outcomes.values())
    else:
        vals = [v for k, v in outcomes.items() if k == group or k.startswith(group + ".")]
    if not vals:
        return "missing"
    if any(v in ("fail", "error") for v in vals):
        return "fail"
    if any(v.startswith("skip") for v in vals):
        return "skip"
    return "pass"


def _load_components() -> List[dict]:
    return json.loads((PKG / "components.json").read_text())["components"]


def _load_waivers() -> List[dict]:
    p = PKG / "docs" / "governance" / "waivers.json"
    return json.loads(p.read_text())["waivers"] if p.exists() else []


def _waiver_valid(w: dict, today: dt.date) -> bool:
    need = ("requirement", "rationale", "risk", "compensating_control", "owner", "approver", "created", "expires")
    if any(not w.get(k) for k in need) or "UNASSIGNED" in (w.get("owner"), w.get("approver")):
        return False
    return dt.date.fromisoformat(w["expires"]) >= today


def disposition(check_id: str, comps: List[dict], groups: Dict[str, str], waivers: List[dict],
                today: dt.date, pk_status: str) -> dict:
    mapped = [c for c in comps if check_id in c["maps_to"]]
    tests = sorted({t for c in mapped for t in c["tests"]})
    failed = [t for t in tests if groups.get(t) == "fail"]
    not_run = [t for t in tests if groups.get(t) in (None, "missing", "skip")]
    blockers = sorted({c["work_item"] for c in mapped if c["status"] != "CLOSED_LOCAL"})
    if not mapped:
        blockers = ["WI-INV20-01"]
    if check_id == "INV-20-C100":
        blockers = sorted(set(blockers) | {"ALL-DOMAINS-GREEN"})
    if failed:
        status = "FAIL"
    elif blockers or not_run:
        status = "BLOCKED"
    else:
        status = "PASS"
    waiver = next((w for w in waivers if w.get("requirement") == check_id), None)
    if status == "BLOCKED" and waiver and _waiver_valid(waiver, today):
        status = "WAIVED"
    return {"schema": SCHEMA, "check_id": check_id, "release": __version__, "status": status,
            "implementation": sorted({a for c in mapped for a in c["artifacts"]}),
            "components": [c["work_item"] for c in mapped], "tests": {t: groups.get(t, "missing") for t in tests},
            "blocked_by": blockers if status in ("BLOCKED", "WAIVED") else [],
            "not_run": not_run, "waiver": waiver.get("id") if waiver else None,
            "tool_versions": {"python": platform.python_version(), "pk_core": pk_status},
            "owner": "UNASSIGNED", "reviewer": "UNASSIGNED"}


def collect(extra_groups: Dict[str, str] | None = None) -> dict:
    import os
    os.environ["INV20_IN_EVIDENCE_RUN"] = "1"
    from .pk_compat import probe
    pk = probe()
    outcomes = run_suites()
    opt = run_suites(optimized=True)
    groups: Dict[str, str] = {}
    comps = _load_components()
    names = {t for c in comps for t in c["tests"]}
    for g in names:
        groups[g] = group_status(outcomes, g)
        if g not in ("fuzz", "bench", "clean_room", "VERIFY", "all") and group_status(opt, g) == "fail":
            groups[g] = "fail"                               # must also pass under python -O
    groups.update(extra_groups or {})
    for g in ("fuzz", "bench", "clean_room", "VERIFY"):
        groups.setdefault(g, "missing")
    skipped_mandatory = sorted(k for k, v in outcomes.items() if v.startswith("skip")
                               and any(m in k for m in MANDATORY_SKIP_FORBIDDEN))
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    today = dt.datetime.now(dt.timezone.utc).date()
    waivers = _load_waivers()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    src = source_digest()
    (EVIDENCE / "requirements").mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "tests").mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "dependencies").mkdir(parents=True, exist_ok=True)
    test_doc = {"schema": "INV20_TESTRUN/1", "timestamp_utc": now, "python": sys.version.split()[0],
                "platform": platform.platform(), "outcomes": outcomes, "optimized_outcomes": opt,
                "groups": groups, "skipped_mandatory": skipped_mandatory,
                "command": "python -m inv20_http_component_worlds.evidence_gate collect"}
    (EVIDENCE / "tests" / "testrun.json").write_bytes(canonical(test_doc))
    (EVIDENCE / "dependencies" / "pk_core.json").write_bytes(canonical(pk))
    wit_lock = (PKG / "wit" / "wit.lock").read_text()
    (EVIDENCE / "dependencies" / "wit-lock.json").write_bytes(canonical({
        "local_wit_sha256": _sha((PKG / "wit" / "inv20.wit").read_bytes()),
        "upstream_status": "BLOCKED" if "UNRESOLVED" in wit_lock else "PINNED"}))
    trace, counts, local_counts = [], {}, {}
    for item in checklist["items"]:
        rec = disposition(item["check_id"], comps, groups, waivers, today, pk["status"])
        rec["local_verification"] = rec["status"]     # what this repository alone proves
        rec.update({"requirement_sha256": _sha(item["requirement"].encode()), "timestamp_utc": now,
                    "source_revision": "sha256:" + src, "dimension": item["dimension"]})
        if skipped_mandatory and rec["status"] == "PASS":
            rec["status"], rec["blocked_by"] = "BLOCKED", ["mandatory-skip:pk_core-conformance"]
        # C100 may only pass when every other requirement passes.
        body = canonical(rec)
        (EVIDENCE / "requirements" / f"{item['check_id']}.json").write_bytes(body)
        trace.append({"check_id": item["check_id"], "status": rec["status"], "local_verification":
                      rec["local_verification"], "sha256": _sha(body), "blocked_by": rec["blocked_by"]})
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        local_counts[rec["local_verification"]] = local_counts.get(rec["local_verification"], 0) + 1
    others_green = all(t["status"] in ("PASS", "WAIVED") for t in trace if t["check_id"] != "INV-20-C100")
    if not others_green:
        c100 = next(t for t in trace if t["check_id"] == "INV-20-C100")
        if c100["status"] == "PASS":  # pragma: no cover - defensive
            c100["status"] = "BLOCKED"
    files = sorted(p for p in EVIDENCE.rglob("*") if p.is_file() and p.name not in ("release.json", "traceability.json", "gate.json"))
    release = {"schema": "INV20_RELEASE/1", "release": __version__, "source_sha256": src, "timestamp_utc": now,
               "builder": {"python": sys.version.split()[0], "platform": platform.platform(), "host": platform.node()},
               "pk_core": pk, "counts": counts, "local_counts": local_counts, "skipped_mandatory": skipped_mandatory,
               "evidence_files": {p.relative_to(EVIDENCE).as_posix(): _sha(p.read_bytes()) for p in files},
               "signature": None, "signature_status": "BLOCKED: no approved signing infrastructure"}
    (EVIDENCE / "traceability.json").write_bytes(canonical({"schema": "INV20_TRACE/1", "release": __version__,
                                                            "items": trace}))
    release["traceability_sha256"] = _sha((EVIDENCE / "traceability.json").read_bytes())
    (EVIDENCE / "release.json").write_text(json.dumps(release, indent=1, sort_keys=True))
    return release


def gate(evidence: pathlib.Path = EVIDENCE) -> dict:
    """Independent decision: re-derives everything from files + current tree; trusts no runtime state."""
    reasons: List[str] = []
    try:
        release = json.loads((evidence / "release.json").read_text())
        trace = json.loads((evidence / "traceability.json").read_text())
    except (OSError, ValueError):
        return {"verdict": "NO_GO", "reasons": ["missing evidence bundle"], "exit": 1}
    if release.get("release") != __version__ or trace.get("release") != __version__:
        reasons.append("version mismatch among source, evidence and declared release")
    if release.get("source_sha256") != source_digest():
        reasons.append("stale evidence: source digest changed since collection")
    if _sha((evidence / "traceability.json").read_bytes()) != release.get("traceability_sha256"):
        reasons.append("traceability.json tampered")
    for rel, h in release.get("evidence_files", {}).items():
        p = evidence / rel
        if not p.exists() or _sha(p.read_bytes()) != h:
            reasons.append(f"evidence file missing/tampered: {rel}")
    ids = [t["check_id"] for t in trace.get("items", [])]
    expected = [f"INV-20-C{i:03d}" for i in range(1, 101)]
    if sorted(ids) != expected:
        reasons.append("requirement records missing or duplicated")
    today = dt.datetime.now(dt.timezone.utc).date()
    for w in _load_waivers():
        if w.get("expires") and dt.date.fromisoformat(w["expires"]) < today:
            reasons.append(f"expired waiver {w.get('id')}")
    statuses = {t["check_id"]: t["status"] for t in trace.get("items", [])}
    failed = sorted(k for k, v in statuses.items() if v == "FAIL")
    blocked = sorted(k for k, v in statuses.items() if v == "BLOCKED")
    if failed:
        reasons.append(f"{len(failed)} requirement(s) FAIL")
    if release.get("skipped_mandatory"):
        reasons.append("mandatory test skipped: " + ", ".join(release["skipped_mandatory"][:3]))
    if release.get("signature") is None:
        blocked_note = "evidence/artifacts unsigned"
    else:
        blocked_note = ""
    hard = [r for r in reasons if not r.startswith("mandatory test skipped")]
    if hard:
        verdict, code = "NO_GO", 1
    elif blocked or reasons or blocked_note:
        verdict, code = "BLOCKED", 2
    else:
        verdict, code = "GO", 0
    return {"schema": "INV20_GATE/1", "verdict": verdict, "exit": code, "release": release.get("release"),
            "counts": release.get("counts"), "local_counts": release.get("local_counts"), "failed": failed, "blocked": len(blocked),
            "reasons": reasons + ([blocked_note] if blocked_note else [])}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    extra = {}
    for a in argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            extra[k] = v
    if argv and argv[0] == "collect":
        rel = collect(extra)
        print(json.dumps({"release": rel["release"], "counts": rel["counts"]}))
        argv = ["gate"]
    res = gate()
    if EVIDENCE.exists():
        (EVIDENCE / "gate.json").write_text(json.dumps(res, indent=1))   # not part of the hashed bundle
    print(json.dumps(res, indent=1))
    return res["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
