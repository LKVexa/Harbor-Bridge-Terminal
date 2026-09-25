"""Release/evidence pipeline for GAP-06 v5.0.0 (MC-38/44/50/51/52 tooling).

Runs the test suite (normal and -O), the fuzzer and the benchmark; generates
schemas, fixtures, the error catalogue, config and observability references,
the SBOM and SPEC; evaluates every item of the missing-components checklist
against governance/item_map.txt -- *re-checking every cited test, file and
evidence artefact* -- and writes CHECKLIST_STATUS.{json,md}, an annotated copy
of the checklist, governance/PRODUCTION_GATE.json and a signed
evidence/EVIDENCE_MANIFEST.json.

Status marks: [~] implemented with passing evidence but NOT independently
reviewed; [!] blocked (named blocker); [ ] not started.  The builder never
emits [x]: every item needs U20 independent review.
Usage (from the directory containing the package):
    python -m gap06_device_identity_and_attestation.tools.release [--fuzz N]
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parent
TESTS = PKG / "tests"
CHECKLIST = PKG / "governance" / "GAP06_Missing_Components_Professional_Checklist_v1.0.0.md"
SELF_OUTPUTS = {"CHECKLIST_STATUS.md", "governance/PRODUCTION_GATE.json", "evidence/EVIDENCE_MANIFEST.json"}
VERSION = (PKG / "VERSION").read_text().strip()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------ tests
class _Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes = {}

    def _id(self, test):
        parts = test.id().split(".")
        return ".".join(parts[-2:])

    def addSuccess(self, t):
        super().addSuccess(t); self.outcomes[self._id(t)] = "pass"

    def addFailure(self, t, e):
        super().addFailure(t, e); self.outcomes[self._id(t)] = "fail"

    def addError(self, t, e):
        super().addError(t, e); self.outcomes[self._id(t)] = "error"

    def addSkip(self, t, r):
        super().addSkip(t, r); self.outcomes[self._id(t)] = "skip"


def run_tests():
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))
    stream = io.StringIO()
    res = unittest.TextTestRunner(stream=stream, resultclass=_Collect, verbosity=0).run(suite)
    opt = subprocess.run([sys.executable, "-O", "-m", "unittest", "discover", "-s", str(TESTS), "-p", "test_*.py"],
                         cwd=ROOT, capture_output=True, text=True)
    tail = opt.stderr.strip().splitlines()[-1] if opt.stderr.strip() else ""
    import cryptography
    return {"schema": "GAP06-TESTS/1", "total": res.testsRun, "failures": len(res.failures), "errors": len(res.errors),
            "skipped": len(res.skipped), "outcomes": res.outcomes,
            "optimized_run": {"returncode": opt.returncode, "summary": tail},
            "environment": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                            "platform": platform.platform(), "cryptography": cryptography.__version__,
                            "openssl": __import__("ssl").OPENSSL_VERSION}}


# ------------------------------------------------------------------ generated references
def gen_references():
    from ..mc import errors, ops, schemas
    out = PKG / "schemas"
    (out / "fixtures").mkdir(parents=True, exist_ok=True)
    for name in schemas.T:
        (out / f"{name.replace('/', '_')}.schema.json").write_text(json.dumps(schemas.json_schema(name), indent=1) + "\n")
    pos = {"schema": "PK_ATTESTATION/1", "node": "node-a", "nonce": "00" * 32, "attest": "ff544347", "signature": "0018",
           "pcrs": {"0": "00" * 32}, "idempotency_key": "golden-1"}
    (out / "fixtures" / "positive_attestation.json").write_text(json.dumps(pos, indent=1, sort_keys=True) + "\n")
    neg = [{"case": "unknown field", "message": dict(pos, extra=1)},
           {"case": "uppercase hex", "message": dict(pos, nonce="AB")},
           {"case": "future schema version", "message": dict(pos, schema="PK_ATTESTATION/2")},
           {"case": "PCR index out of range", "message": dict(pos, pcrs={"24": "00" * 32})},
           {"case": "missing required", "message": {k: v for k, v in pos.items() if k != "node"}}]
    for n in neg:  # the fixtures must actually behave as labelled
        try:
            schemas.validate(n["message"])
            raise SystemExit(f"negative fixture accepted: {n['case']}")
        except errors.Gap06Error as e:
            n["expected_code"] = e.code
    schemas.validate(pos)
    (out / "fixtures" / "negative_cases.json").write_text(json.dumps(neg, indent=1, sort_keys=True) + "\n")

    lines = ["# Error catalogue (GAP06-ERR/1) — generated", "",
             "Codes are append-only. Clients must branch on `code`, not on HTTP status.", "",
             "| Code | Category | Retryable | HTTP | Operator remediation |", "|---|---|---|---|---|"]
    remedy = {"freshness": "request a new challenge; check TrustedClock health", "measurement": "run explain(); compare PCRs with active policy; quarantine runbook",
              "authentication": "check enrolled AK / trust anchors / CRLs", "authorization": "check principal roles and scopes",
              "capacity": "back off with jitter; honour retry_after", "malformed": "fix client encoder; do not retry unchanged",
              "unsupported": "see COMPATIBILITY.md", "tcb": "update firmware/TCB", "state": "check enrollment/policy state",
              "internal": "page on-call; preserve evidence"}
    for c, (cat, retry, st) in errors.CODES.items():
        lines.append(f"| `{c}` | {cat.value} | {'yes' if retry else 'no'} | {st} | {remedy[cat.value]} |")
    (PKG / "docs" / "ERROR_CATALOG.md").write_text("\n".join(lines) + "\n")

    lines = ["# Configuration reference — generated from `mc/ops.py::CONFIG_SCHEMA`", "",
             "Configuration must be signed (`load_config(..., signature_ok=True)` after verification). Unknown keys are rejected.", "",
             "| Key | Type | Default | Bounds | Runtime-mutable | Restart | Owner |", "|---|---|---|---|---|---|---|"]
    for k, (typ, d, lo, hi, m, r) in ops.CONFIG_SCHEMA.items():
        lines.append(f"| `{k}` | {typ.__name__} | {d} | {'' if lo is None else f'[{lo}, {hi}]'} | {m} | {r} | UNASSIGNED |")
    (PKG / "docs" / "CONFIG.md").write_text("\n".join(lines) + "\n")

    (PKG / "docs" / "OBSERVABILITY.md").write_text("""# Observability catalogue (MC-24) — reference

Allowed metric labels (cardinality control, enforced in `ops.Telemetry`): `code, level, result, site, op`. Node ids, nonces and challenge ids are **never** labels.

| Metric | Type | Labels | Emitted by |
|---|---|---|---|
| `gap06_challenges_total` | counter | op | `service.challenge` |
| `gap06_attest_total` | counter | result, code | `service.attest` (every outcome incl. replay) |
| `gap06_admission_rejected` | counter (field `Admission.rejected`) | — | `ratelimit` — not yet exported |
| `gap06_telemetry_dropped_series` | gauge (`Telemetry.dropped_series`) | — | not yet exported |

Structured logs: `Telemetry.log(event, trace_id=…, **fields)`, values redacted and truncated to 256 chars. Trace context: W3C `traceparent` via `ops.trace_context`.

## Proposed alerts (not deployed — no alerting platform)
| Alert | Condition | Severity | Runbook |
|---|---|---|---|
| ReplayAttempts | rate(`gap06_attest_total{code="E_REPLAY"}`) > 0 for 5m | SEV2 | RUNBOOKS.md › Replay-state storage pressure |
| MeasurementDriftSpike | reject ratio `E_MEASUREMENT_REJECTED` > 2× 1h baseline | SEV2 | RUNBOOKS.md › Policy publication / rollback |
| TimeUntrusted | any `E_TIME_UNTRUSTED` | SEV1 | RUNBOOKS.md › Time-integrity failure |
| LedgerTamper | `AuditLedger.verify` raises | SEV1 | RUNBOOKS.md › Audit verification |
""")
    bench = json.loads((PKG / "evidence" / "bench.json").read_text())
    (PKG / "docs" / "CAPACITY.md").write_text(f"""# Capacity baseline (MC-26/39) — measured, not approved

Environment: Python {bench['env']['python']}, {bench['env']['cpus']} vCPU, {bench['env']['platform']}.

| Measure | Value |
|---|---|
| attest path p50 / p99 / max | {bench['attest_path']['p50_ms']} / {bench['attest_path']['p99_ms']} / {bench['attest_path']['max_ms']} ms |
| throughput (single process, fsync off) | {bench['attest_path']['throughput_per_s']} /s |
| traced memory per attestation | {bench['memory']['per_attestation_bytes']} bytes |
| challenge table across soak rounds | {bench['soak']['challenge_table_sizes']} (bounded: {bench['soak']['bounded']}) |
| idempotency rows after soak | {bench['soak']['idempotency_rows']} — **unbounded, no retention implemented** |

Known scale limits: `DurableStore` holds every table in memory and `items()` deep-copies a table (O(n)), which `ChallengeBook.issue` calls on every issuance — acceptable for the reference, not for a fleet. Sharding: `ops.ShardRing` (consistent hashing, tested for balance and ≤35% movement on 4→5 shards). Thresholds for release are **not approved** (no owner).
""")


def gen_sbom():
    import importlib.metadata as md
    comps = []
    for name in ("cryptography", "cffi", "pycparser"):
        try:
            d = md.distribution(name)
            lic = d.metadata.get("License-Expression") or d.metadata.get("License") or ""
            comps.append({"type": "library", "name": name, "version": d.version, "purl": f"pkg:pypi/{name}@{d.version}",
                          "licenses": [{"expression": lic}] if lic else []})
        except md.PackageNotFoundError:
            pass
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                         "component": {"type": "library", "name": "gap06-device-identity-and-attestation", "version": VERSION}},
            "components": comps + [{"type": "platform", "name": "python", "version": sys.version.split()[0]}]}
    (PKG / "evidence" / "sbom.cdx.json").write_text(json.dumps(sbom, indent=1) + "\n")
    (PKG / "requirements.lock").write_text("".join(f"{c['name']}=={c['version']}\n" for c in comps))


# ------------------------------------------------------------------ checklist
ITEM_RE = re.compile(r"^- \[ \] \*\*((?:\d{2}\.(?:\d{2}|D\d))|U\d{2}|G\d{2})\.\*\* (.*)$")


def parse_checklist():
    items, section = [], "Universal gate"
    for line in CHECKLIST.read_text("utf-8").splitlines():
        if line.startswith("# ") and re.match(r"# \d{2}\. ", line):
            section = line[2:].strip()
        elif line.startswith("# Program-level"):
            section = "Program-level production exit gate"
        m = ITEM_RE.match(line)
        if m:
            items.append({"id": m.group(1), "text": m.group(2), "section": section})
    return items


def load_map():
    mp = {}
    for line in (PKG / "governance" / "item_map.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        iid, st, ev, note = (line.split("|") + ["", "", ""])[:4]
        if iid in mp:
            raise SystemExit(f"duplicate item id in item_map: {iid}")
        mp[iid] = (st, [e for e in ev.split(";") if e], note)
    return mp


def check_evidence(tokens, outcomes):
    bad = []
    for t in tokens:
        kind, _, ref = t.partition(":")
        if kind == "T":
            if outcomes.get(ref) != "pass":
                bad.append(f"{t} ({outcomes.get(ref, 'not found')})")
        elif kind in ("F", "E"):
            if ref not in SELF_OUTPUTS and not (PKG / ref).exists():
                bad.append(f"{t} (missing)")
            if kind == "E" and ref == "evidence/fuzz.json" and (PKG / ref).exists():
                if not json.loads((PKG / ref).read_text())["property_holds"]:
                    bad.append(f"{t} (property violated)")
        else:
            bad.append(f"{t} (unknown token)")
    return bad


def evaluate(items, mp, outcomes):
    comps_with_p = {i["id"][:2] for i in items if mp.get(i["id"], ("N",))[0] == "P"}
    rows = []
    for it in items:
        iid = it["id"]
        if iid in mp:
            st, ev, note = mp[iid]
        elif re.match(r"\d{2}\.D[12]$", iid):
            st, ev, note = "B", [], "HUMAN: requires U01/U20 (owner, independent review) and every component item complete or waived"
        elif re.match(r"\d{2}\.D3$", iid):
            st, ev, note = ("P", ["F:CHECKLIST_STATUS.md"], "traceability links generated; no signed release evidence") \
                if iid[:2] in comps_with_p else ("N", [], "")
        elif iid.startswith("G"):
            st, ev, note = "B", ["F:governance/PRODUCTION_GATE.json"], "program gate cannot pass: component DoDs blocked"
        else:
            st, ev, note = "N", [], "not started"
        problems = check_evidence(ev, outcomes)
        if st == "P" and problems:
            st, note = "B", f"DOWNGRADED: cited evidence failed: {'; '.join(problems)}. {note}"
        rows.append({**it, "status": {"P": "[~]", "B": "[!]", "N": "[ ]"}[st], "evidence": ev, "note": note})
    return rows


def write_status(rows, tests):
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    by_comp = {}
    for r in rows:
        c = r["section"]
        by_comp.setdefault(c, {"[~]": 0, "[!]": 0, "[ ]": 0})[r["status"]] += 1
    doc = {"schema": "GAP06-CHECKLIST-STATUS/1", "checklist": "GAP06-MISSING-COMPONENTS-CHECKLIST/1 v1.0.0",
           "package_version": VERSION, "items": len(rows), "counts": counts, "completed_[x]": 0,
           "by_component": by_comp, "rows": rows}
    (PKG / "CHECKLIST_STATUS.json").write_text(json.dumps(doc, indent=1) + "\n")
    md = [f"# GAP-06 missing-components checklist — status for v{VERSION}", "",
          "Generated by `tools/release.py`; every `[~]` below re-ran its cited tests / re-checked its files in this build. "
          "`[~]` = implemented with passing evidence, **not independently reviewed** (U20), so never `[x]`. "
          "`[!]` = blocked, blocker named. `[ ]` = not started.", "",
          f"**{len(rows)} items: {counts.get('[~]', 0)} [~] · {counts.get('[!]', 0)} [!] · {counts.get('[ ]', 0)} [ ] · 0 [x].** "
          f"Tests: {tests['total']} run, {tests['failures']} failed, {tests['errors']} errors, {tests['skipped']} skipped.", "",
          "| Component | [~] | [!] | [ ] |", "|---|---|---|---|"]
    for c, v in by_comp.items():
        md.append(f"| {c} | {v['[~]']} | {v['[!]']} | {v['[ ]']} |")
    md += ["", "## Item detail", "", "| ID | Status | Evidence | Note |", "|---|---|---|---|"]
    for r in rows:
        ev = "<br>".join(f"`{e}`" for e in r["evidence"])
        md.append(f"| {r['id']} | {r['status']} | {ev} | {r['note'].replace('|', '/')} |")
    (PKG / "CHECKLIST_STATUS.md").write_text("\n".join(md) + "\n")
    # annotated copy of the checklist itself
    st = {r["id"]: r for r in rows}
    out = []
    for line in CHECKLIST.read_text("utf-8").splitlines():
        m = ITEM_RE.match(line)
        if m and m.group(1) in st:
            r = st[m.group(1)]
            line = line.replace("- [ ]", f"- {r['status']}", 1)
            if r["note"]:
                line += f"  _({r['note']})_"
        out.append(line)
    (PKG / "docs" / "CHECKLIST_ANNOTATED.md").write_text("\n".join(out) + "\n")
    spec = [f"# GAP-06 SHALL specification (mechanical conversion, v{VERSION})", "",
            "Each checklist item restated as a normative requirement with a stable id. Not yet atomic or reviewed (38.02/38.03 open).", ""]
    for r in rows:
        spec.append(f"- **GAP06-REQ-{r['id']}** — The subsystem SHALL satisfy: {r['text']}  \n  status {r['status']}")
    (PKG / "docs" / "SPEC.md").write_text("\n".join(spec) + "\n")
    return counts


def doc_check():
    problems, longest = [], 0
    for p in PKG.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = f"{PKG.name}/{p.relative_to(PKG).as_posix()}"
            longest = max(longest, len(rel))
    readme = (PKG / "README.md").read_text()
    for ref in re.findall(r"`([A-Za-z0-9_/.-]+\.(?:md|json|py))`", readme):
        if not any((PKG / ref).exists() or list(PKG.rglob(Path(ref).name)) for _ in [0]):
            problems.append(f"README references missing file {ref}")
    required = ["README.md", "CHANGELOG.md", "SECURITY.md", "MISSING_COMPONENTS.md", "docs/MASTER.md", "pyproject.toml"]
    for r in required:
        if not (PKG / r).exists():
            problems.append(f"required file missing: {r}")
    lic = (PKG / "LICENSE").exists()
    res = {"schema": "GAP06-DOCCHECK/1", "problems": problems, "max_relative_path_length": longest,
           "windows_safe": longest < 200, "license_present": lic,
           "note": "LICENSE absent by design: licence choice is the owner's decision (53.01)" if not lic else ""}
    (PKG / "evidence" / "doc_check.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def gate(counts, tests, docres):
    owners = json.loads((PKG / "governance" / "OWNERS.json").read_text())
    waivers = json.loads((PKG / "governance" / "WAIVERS.json").read_text())
    now = dt.datetime.now(dt.timezone.utc)
    wprob = []
    for w in waivers["waivers"]:
        miss = [f for f in waivers["required_fields"] if not w.get(f)]
        if miss:
            wprob.append(f"{w.get('id')}: missing {miss}")
        elif dt.datetime.fromisoformat(w["expires_utc"]) <= now:
            wprob.append(f"{w['id']}: expired")
    reasons = []
    if counts.get("[x]", 0) != sum(counts.values()):
        reasons.append(f"{sum(counts.values()) - counts.get('[x]', 0)} checklist items are not [x] and not waived")
    if tests["failures"] or tests["errors"] or tests["optimized_run"]["returncode"]:
        reasons.append("test failures")
    unassigned = [k for k, v in owners["roles"].items() if not v]
    if unassigned:
        reasons.append(f"unassigned roles: {unassigned}")
    if wprob:
        reasons.append(f"waiver problems: {wprob}")
    if docres["problems"]:
        reasons.append(f"doc problems: {docres['problems']}")
    reasons.append("no signed approver decision record")
    g = {"schema": "GAP06-GATE/1", "package_version": VERSION, "decision": "NO_GO" if reasons else "GO",
         "production_trust_decisions_authorised": False, "reasons": reasons,
         "decided_by": "tools/release.py (mechanical; not an approver)", "decided_at": now.isoformat(timespec="seconds")}
    (PKG / "governance" / "PRODUCTION_GATE.json").write_text(json.dumps(g, indent=1) + "\n")
    return g


def manifest():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    files = {}
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name not in ("EVIDENCE_MANIFEST.json", "RELEASE_MANIFEST.sha256") and p.suffix != ".pyc":
            files[p.relative_to(PKG).as_posix()] = sha(p)
    body = {"schema": "GAP06-EVIDENCE-MANIFEST/1", "package_version": VERSION, "source_commit": None,
            "source_commit_note": "archive supplied without VCS metadata",
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "builder": "Claude (Cowork) chop-shop session; not a managed build service", "files": files}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    key = ed25519.Ed25519PrivateKey.generate()  # EPHEMERAL: discarded after signing
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    out = {"manifest": body, "sha256": hashlib.sha256(blob).hexdigest(), "signature": key.sign(blob).hex(),
           "signing_key": {"ed25519_public_hex": pub, "custody": "ephemeral per-run key; NOT a managed release key (44.04 blocked)"}}
    (PKG / "evidence" / "EVIDENCE_MANIFEST.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def main(argv):
    fuzz_n = int(argv[argv.index("--fuzz") + 1]) if "--fuzz" in argv else 5000
    (PKG / "evidence").mkdir(exist_ok=True)
    from . import bench, fuzz
    import os
    cwd = os.getcwd()
    os.chdir(PKG)
    try:
        (PKG / "evidence" / "fuzz.json").write_text(json.dumps(fuzz.run(fuzz_n), indent=1) + "\n")
        bench.main()
    finally:
        os.chdir(cwd)
    gen_references()
    gen_sbom()
    tests = run_tests()
    (PKG / "evidence" / "test_results.json").write_text(json.dumps(tests, indent=1) + "\n")
    docres = doc_check()
    items = parse_checklist()
    counts = write_status(evaluate(items, load_map(), tests["outcomes"]), tests)
    g = gate(counts, tests, docres)
    m = manifest()
    missing_self = [s for s in SELF_OUTPUTS if not (PKG / s).exists()]
    print(json.dumps({"items": len(items), "counts": counts, "tests": {k: tests[k] for k in ("total", "failures", "errors", "skipped")},
                      "optimized": tests["optimized_run"], "gate": g["decision"], "manifest_sha256": m["sha256"],
                      "self_outputs_missing": missing_self}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
