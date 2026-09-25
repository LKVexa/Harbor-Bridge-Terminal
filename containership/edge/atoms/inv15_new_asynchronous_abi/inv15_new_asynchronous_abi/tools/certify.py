"""Execute the INV-15 v4.2.0 component checklist against this package.

1. Runs every test file under normal and -O Python, the interop harness, the
   binding/vector reproducibility checks and the release metadata check.
2. Classifies all 1,599 checklist boxes with a hand-written, per-item status:
     E  EVIDENCED   implemented here and checked by an executed, passing test/tool
     P  PARTIAL     something real exists, the stated remainder is missing
     B  BLOCKED     needs a person, a production runtime, other hardware/OSes,
                    another team's component, signing keys, or elapsed time
     N  NOT_DONE    reachable in principle, not done in this pass
   A component whose evidence tests FAIL has every E downgraded to N.
3. Writes certification/CHECKLIST_STATUS.json, certification/COMPONENT_STATUS.md
   and certification/CHECKLIST_ANNOTATED.md.
No box is ever ticked [x]: the checklist reserves [x] for verified-with-evidence
under an owner and reviewer, and no owner or reviewer exists.
"""
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKLIST = pathlib.Path(os.environ.get("INV15_CHECKLIST", ROOT / "certification" / "SOURCE_CHECKLIST.md"))
NAME = {"E": "EVIDENCED", "P": "PARTIAL", "B": "BLOCKED", "N": "NOT_DONE"}

# --- per-component: specific items (4), evidence test ids, note ---------------
S = {
 1: ("EEEB", ["test_wire.TestIdl", "test_host.TestCore", "test_adapters.TestAsyncFunction"], "B: only one language (Python) and one runtime exist"),
 2: ("EEEE", ["test_host.TestCore", "test_wire.TestNegotiation"], ""),
 3: ("EEEE", ["test_host.TestCancellation", "test_certification.TestRaces"], ""),
 4: ("PPEP", ["test_wire.TestIdl", "test_security_telemetry.TestRedaction"], "P: registry has code+retryable but no owner/severity class; categories are distinct codes not a published class taxonomy; envelope carries no causal chain"),
 5: ("EEEB", ["test_wire.TestHandleEncoding", "test_wire.TestVectors"], "B: layout is explicit big-endian but was only executed on one little-endian x86_64 host"),
 6: ("EEEP", ["test_wire.TestHandleEncoding", "test_wire.TestVectors"], "P: vectors cover version 0/1/2, bit1 and bit4, not every flag combination"),
 7: ("EEEE", ["test_host.TestLifecycle", "test_certification.TestProperty"], ""),
 8: ("EEBP", ["test_wire.TestVectors"], "B: only one language consumes the corpus; P: corpus hashed in MANIFEST, not signed"),
 9: ("EPPP", ["test_host.TestDeadlines"], "P: detachment does not opt out of deadline inheritance; no cross-binding rounding exists; scheduler suspension not tested"),
 10: ("EEEE", ["test_host.TestDeadlines"], ""),
 11: ("EEEE", ["test_host.TestCancellation"], ""),
 12: ("PPNE", ["test_host.TestCancellation", "test_wire.TestIdl"], "N: v1 decoders REJECT unknown reason codes (MALFORMED) instead of mapping them to OTHER - not forward-compatible; P: no vendor range; only Future.cancel is mapped"),
 13: ("EEPE", ["test_host.TestCancellation"], "P: deep tree tested (64 levels); wide trees under quota pressure not tested"),
 14: ("PPNE", ["test_host.TestIdempotency"], "N: same-key/different-payload conflict is not detected (payload is not compared); P: no entropy guidance; callee retry safety not declared per operation"),
 15: ("EPNN", ["test_host.TestIdempotency"], "N: attempt number is not carried; no retry-storm test; P: ambiguous-commit outcome not distinguished"),
 16: ("PEPE", ["test_host.TestBudgetsFairness", "test_certification.TestSoakOverload"], "P: node/global scopes collapse into process; explain() shows tenant names to operators (not reviewed)"),
 17: ("EEPE", ["test_host.TestBudgetsFairness", "test_certification.TestSoakOverload"], "P: fairness measured as held-count parity, no starvation metric"),
 18: ("EPEE", ["test_host.TestDrainDisable"], "P: no bounded grace-period timer; policies are allow/cancel/invalidate"),
 19: ("BBPB", [], "B: the production backend is by definition not this Python reference; nothing here replaces it"),
 20: ("EEEE", ["test_host.TestGenerations"], ""),
 21: ("PEPE", ["test_host.TestRng", "test_certification.TestFaultInjection"], "P: secrets.token_bytes documented, FIPS not considered; guessing math for deployment scale not written"),
 22: ("EPBP", ["test_host.TestSubscribe", "test_certification.TestLostWakeup"], "B: no futex/scheduler-native primitive; P: thousands of randomized iterations, not millions; removal-vs-publication race not threaded"),
 23: ("BEEB", ["test_host.TestReadyQueue", "test_certification.TestSoakOverload"], "B: no MPSC/scheduler-native queue; no multi-core contention measurement possible under the GIL"),
 24: ("EEPN", ["test_host.TestReadyQueue"], "P: singleton-starvation not tested; N: no batch-size benchmark"),
 25: ("EEEE", ["test_host.TestCore", "test_certification.TestFaultInjection"], ""),
 26: ("PPEB", ["test_host.TestCore", "test_adapters.TestAsyncFunction"], "P: one TRAPPED class, host abort/resource kill not distinguished; no privileged diagnostic path; B: no language bindings"),
 27: ("EEEE", ["test_host.TestTeardownRestart"], ""),
 28: ("EPEP", ["test_host.TestTeardownRestart"], "P: epoch is in memory, not persisted; crash at every transition not tested"),
 29: ("EEEP", ["test_host.TestMemoryOwnership", "test_certification.TestSoakOverload"], "P: reconciliation ran and FOUND a gap - declared 256 B/row vs ~1.1 KB/row measured by tracemalloc (see BENCHMARK_BASELINE.json)"),
 30: ("PEEB", ["test_host.TestMemoryOwnership"], "P: result ownership defined, input buffers not; B: sanitizers do not apply to CPython"),
 31: ("EEPE", ["test_adapters.TestScheduler", "test_certification.TestFaultInjection"], "P: adapter run queue is FIFO, tenant fairness not preserved at this layer"),
 32: ("PEPP", ["test_adapters.TestAsyncFunction"], "P: no generated guest stubs; deadline not mapped from the future; timeout/teardown/version-mismatch paths untested at this layer"),
 33: ("EEPP", ["test_adapters.TestStream"], "P: gap/duplicate rules unwritten; only some close/error races tested"),
 34: ("EPEP", ["test_adapters.TestCompletion"], "P: type check is isinstance only; resolution races untested"),
 35: ("BENE", ["test_wire.TestIdl"], "B: INV-11 grammar belongs to INV-11; N: no diagnostics for unsupported async features"),
 36: ("BBPB", [], "B: INV-12 and other languages absent; P: widths/BE/UTF-8 explicit in codec"),
 37: ("BPPP", ["test_adapters.TestShim"], "B: INV-14 behaviour inventory needs INV-14's source; P: deprecation counter has no workload label; no cutover deadline"),
 38: ("BBPP", ["test_wire.TestVectors"], "B: 'two independent runtimes, not two wrappers' - there is one author and one language; the harness compares codec vs codec_alt and v4.2 model vs v4.3 host"),
 39: ("EEEB", ["test_security_telemetry.TestSideChannel", "test_host.TestReplayTenant"], "B: residual-risk owner unnamed"),
 40: ("EEPE", ["test_security_telemetry.TestRedaction"], "P: correlation-id collision/rotation not documented beyond per-process key"),
 41: ("EPEP", ["test_host.TestReplayTenant", "test_wire.TestHandleEncoding", "test_host.TestTeardownRestart"], "P: no per-transport anti-replay window; version-upgrade replay not tested"),
 42: ("EEPE", ["test_host.TestCore", "test_host.TestReplayTenant", "test_security_telemetry.TestAudit"], "P: adapters carry views but the scheduler adapter keys by instance name; not reviewed"),
 43: ("EPPP", ["test_security_telemetry.TestAudit"], "P: timestamp is host monotonic (not trusted), no host id; chain integrity but no access control; forensic reconstruction not exercised"),
 44: ("EPEP", ["test_certification.TestSoakOverload", "test_host.TestBudgetsFairness", "test_host.TestSubscribe"], "P: CPU/lock contention not measured; recovery phases short"),
 45: ("EEPP", ["test_security_telemetry.TestSideChannel"], "P: timing compared by median over 400 samples with a coarse 5x bound, noise not modelled; explain/metrics surface not reviewed"),
 46: ("PBPN", ["test_ops.TestRelease"], "B: no signing key/signer; N: no vulnerability scan; P: SBOM is empty because there are zero dependencies"),
 47: ("EEPN", ["test_security_telemetry.TestTelemetry"], "P: table invariants reconciled, counters not; N: exporter overhead not load-tested"),
 48: ("ENEP", ["test_host.TestCancellation", "test_security_telemetry.TestTelemetry"], "N: buckets are generic log2, not derived from an SLO; P: alert rule written, not verified with injected delay"),
 49: ("PNPP", ["test_adapters.TestScheduler"], "P: publication, runnable and resume stamped; guest resume is outside this model; N: batching/coalescing treatment unwritten"),
 50: ("PEEE", ["test_security_telemetry.TestTelemetry"], "P: schema fixed but not version-tagged"),
 51: ("PNEP", ["test_security_telemetry.TestTelemetry"], "N: no span/link model for fan-out/retries; P: scheduler wake not traced"),
 52: ("EBEN", ["test_security_telemetry.TestTelemetry"], "B: there is no endpoint server to authenticate; N: explain() under overload not tested"),
 53: ("EPPB", ["test_ops.TestRelease"], "B: never imported into Grafana/Prometheus or exercised in staging; P: thresholds PROPOSED, no owner"),
 54: ("PENB", ["test_security_telemetry.TestTelemetry"], "N: no collector-outage behaviour; B: privacy review"),
 55: ("EPNE", ["test_certification.TestProperty"], "P: teardown not in the generator; N: no shrinking"),
 56: ("EPBP", ["test_certification.TestFuzz"], "B: sanitizers; P: seeds are generator outputs not the full vector corpus; mutations are byte-level"),
 57: ("EPBP", ["test_certification.TestRaces"], "B: thread sanitizer; P: slot reuse covered in TestGenerations not under threads; iteration gate small"),
 58: ("PPEP", ["test_certification.TestLostWakeup"], "P: 3,000 x SCALE iterations on one host, not millions across cores; removal-vs-publication not included"),
 59: ("PEEP", ["test_certification.TestSoakOverload"], "P: 20,000 x SCALE cycles in seconds, not long-duration; patterns mixed randomly, not rotated in phases"),
 60: ("EPPE", ["test_certification.TestSoakOverload", "test_host.TestBudgetsFairness"], "P: p99 recorded, CPU not; fail-fast cost not profiled"),
 61: ("PPPN", ["test_ops.TestBench"], "P: core ops benchmarked at 1 and 8 threads, no wait-registration benchmark; environment recorded, no warmup rule; N: no CI regression gate"),
 62: ("EPBN", ["test_ops.TestRelease"], "B: other OS/arch/runtimes not available; N: install-time blocking of unsupported rows"),
 63: ("PEEE", ["test_certification.TestFaultInjection"], "P: trap, clock, RNG, scheduler stall, producer death, callback faults injected; host crash only as restart(); allocator pressure only via memory ceilings"),
 64: ("BPBB", ["test_wire.TestVectors"], "B: no independent production implementation exists; results unsigned"),
 65: ("EEPP", ["test_ops.TestRelease"], "P: no build revision embedded; clean isolated install not run"),
 66: ("PNBP", ["test_ops.TestRelease"], "P: ci.sh has no lint/type-check stage; N: no cache exists; B: protected-branch approvals"),
 67: ("BPEP", ["test_adapters.TestScheduler", "test_wire.TestNegotiation"], "B: adjacent component versions are unknown here; E: fail-fast on unsupported major"),
 68: ("EBPP", ["test_ops.TestRollbackHook"], "B: representative workloads/architectures; P: hook compares a subset of signals, pause is not automated"),
 69: ("PEBB", ["test_ops.TestRollbackHook", "test_host.TestTeardownRestart"], "B: no deployment system to automate restore or exercise"),
 70: ("PPEB", ["test_host.TestDrainDisable"], "P: instance + global scope only, unauthenticated, no grace deadline; B: control-plane loss"),
 71: ("EPBB", ["test_ops.TestRelease"], "B: escalation contacts and exercises need people"),
 72: ("BPPN", ["test_ops.TestRelease"], "B: owners; N: exception tracking"),
}

GROUP = [  # (first, last, 6 statuses, reason for non-E)
 (1, 8, "EEEPEP", "P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings"),
 (9, 18, "EEPEPP", "P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged"),
 (19, 30, "BEBPEE", "B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only"),
 (31, 38, "PEEEBP", "B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only"),
 (39, 46, "EEEPPB", "P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review"),
 (47, 54, "PEEEPN", "P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested"),
 (55, 64, "EEPEEB", "P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows"),
 (65, 72, "PBPPBP", "P: archive timestamps not normalised; no recurring exercises; B: signing and owners"),
]
UNIVERSAL = "PEEEEEPPPPBB"
UNIVERSAL_REASON = ("P: generated component dossier + SPEC, not a reviewed ADR", "", "", "", "",
                    "", "P: adversarial coverage uneven across components", "P: baselines for core ops only; no approved budget",
                    "P: COMPATIBILITY.md is package-level", "P: docs are package-level; no generated per-component reference",
                    "B: code/security review requires reviewers", "B: closure requires owner, reviewer and release artifacts")
UNIVERSAL_OVERRIDE = {19: "BBBBBBBBBBBB", 36: "BBBBBBBBBBBB", 38: "PNENNPNNPPBB", 64: "PNENNPNNPPBB",
                      39: "PNNNNNNNPEBB", 71: "PNNNNNNNPEBB", 72: "PNNNNNNNPEBB", 62: "PNNNNNNNEEBB",
                      61: "PEEEEEPEPPBB"}
DOD = "BBEPBPEPPPPPPPB"
DOD_REASON = ["B: no owners/reviewers", "B: P0 items remain open", "", "P: deterministic in the reference host; restart only as a model",
              "B: guarantees depend on the Python reference by construction", "P: all dimensions bounded; payload accounting understates heap ~4.5x",
              "", "P: suites pass at CI scale; independent conformance BLOCKED", "P: secret-safety tested; overload/exporter failure not",
              "P: one architecture/runtime", "P: SBOM/digests yes, signatures no", "P: procedures and hooks tested as code, not exercised on a fleet",
              "P: adjacent layers absent", "P: package-level docs", "B: sign-off needs four named functions"]


def run_suite():
    tmp = tempfile.mkdtemp()
    results, counts = {}, {}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", INV15_COUNTS=os.path.join(tmp, "c.json"))
    for mode in ("normal", "optimized"):
        for f in sorted((ROOT / "tests").glob("test_*.py")):
            args = [sys.executable, "-B"] + (["-O"] if mode == "optimized" else []) + [str(f), "-v"]
            r = subprocess.run(args, capture_output=True, text=True, env=env, cwd=ROOT.parent)
            for m in re.finditer(r"^(test_\w+) \(\S*?\.?(\w+)\.(test_\w+)\)\s*\.\.\.\s*(ok|FAIL|ERROR|skipped.*)$", r.stderr, re.M):
                key = f"{f.stem}.{m.group(2)}"
                ok = m.group(4) == "ok" or m.group(4).startswith("skipped")
                results.setdefault(key, {"normal": True, "optimized": True, "tests": 0})
                results[key][mode] &= ok
                results[key]["tests"] += 1 if mode == "normal" else 0
            if f.stem == "test_certification" and mode == "normal" and os.path.exists(env["INV15_COUNTS"]):
                counts = json.load(open(env["INV15_COUNTS"]))
    tools = {}
    for name, args in (("bindgen", ["tools/bindgen.py", "--check"]), ("vectors", ["tools/vectors.py", "--check"]),
                       ("interop", ["tools/interop.py"])):
        r = subprocess.run([sys.executable, "-B"] + args, capture_output=True, text=True, cwd=ROOT, env=env)
        tools[name] = {"exit": r.returncode, "out": r.stdout.strip()[-400:]}
    return results, counts, tools


def parse_checklist():
    t = CHECKLIST.read_text()
    parts = re.split(r"\n## (\d+)\. ", t)
    dod = re.findall(r"^- \[ \] (.*)$", parts[0], re.M)
    comps = {}
    for i in range(1, len(parts), 2):
        n, body = int(parts[i]), parts[i + 1]
        comps[n] = {"title": body.split("\n")[0], "priority": re.search(r"\*\*Priority:\*\* (P\d)", body).group(1),
                    "items": re.findall(r"^- \[ \] (.*)$", body.split("# Recommended")[0], re.M)}
    return dod, comps


def classify(results):
    dod, comps = parse_checklist()
    assert len(dod) == 15 and len(comps) == 72 and all(len(c["items"]) == 22 for c in comps.values())
    rows = []
    for i, text in enumerate(dod):
        rows.append({"id": f"DOD-{i+1:02d}", "component": 0, "text": text, "status": NAME[DOD[i]],
                     "reason": DOD_REASON[i], "evidence": []})
    comp_summary = {}
    for n, c in comps.items():
        spec, ev, note = S[n]
        g = next(x for x in GROUP if x[0] <= n <= x[1])
        uni = UNIVERSAL_OVERRIDE.get(n, UNIVERSAL)
        letters = list(spec) + list(g[2]) + list(uni)
        tests_ok = all(results.get(t, {}).get("normal") and results.get(t, {}).get("optimized") for t in ev)
        missing = [t for t in ev if t not in results]
        for k, (text, L) in enumerate(zip(c["items"], letters)):
            if L == "E" and (not tests_ok or not ev):
                L = "N"
                reason = "downgraded: evidence tests missing or failing" if ev else "no executed evidence"
            elif k < 4:
                reason = "" if L == "E" else note
            elif k < 10:
                reason = "" if L == "E" else g[3]
            else:
                reason = "" if L == "E" else (UNIVERSAL_REASON[k - 10] or "not applicable to a component with no implementation here")
            rows.append({"id": f"C{n:02d}-{k+1:02d}", "component": n, "text": text, "status": NAME[L],
                         "reason": reason, "evidence": ev if L in "EP" else []})
        cnt = {s: sum(1 for r in rows if r["component"] == n and r["status"] == s) for s in NAME.values()}
        comp_summary[n] = {"title": c["title"], "priority": c["priority"], "counts": cnt, "evidence": ev,
                           "evidence_passed": tests_ok and bool(ev), "missing_evidence": missing, "note": note}
    return rows, comp_summary


def main():
    results, counts, tools = run_suite()
    rows, comps = classify(results)
    tot = {s: sum(1 for r in rows if r["status"] == s) for s in NAME.values()}
    env = {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system(),
           "scale": int(os.environ.get("INV15_SCALE", "1"))}
    failing = {k: v for k, v in results.items() if not (v["normal"] and v["optimized"])}
    report = {"subject": "inv15_new_asynchronous_abi 4.3.0", "environment": env, "totals": tot, "items": len(rows),
              "test_classes": len(results), "tests": sum(v["tests"] for v in results.values()),
              "failing_test_classes": failing, "tools": tools, "certification_counts": counts,
              "components": comps, "rows": rows,
              "verdict": "NOT_RELEASABLE: 0 items VERIFIED under an owner/reviewer; BLOCKED items require people, a production host and other runtimes"}
    out = ROOT / "certification"
    (out / "CHECKLIST_STATUS.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    md = ["# INV-15 v4.3.0 — component checklist execution status", "",
          f"Environment: CPython {env['python']} / {env['system']} {env['machine']}, INV15_SCALE={env['scale']}. "
          f"Tests: {report['tests']} in {len(results)} classes, normal and `-O`; failing classes: {len(failing)}.", "",
          "| Status | Boxes |", "|---|---|"] + [f"| {k} | {v} |" for k, v in tot.items()] + [
          f"| **total** | **{len(rows)}** |", "",
          "Status meanings: EVIDENCED = implemented and checked by an executed passing test/tool in this delivery; "
          "PARTIAL = real but incomplete (reason given); BLOCKED = needs a person, production host, other runtime/hardware, "
          "another component, keys, or elapsed time; NOT_DONE = reachable but not done. No box is ticked `[x]`.", "",
          "| # | Component | Pri | E | P | B | N | Evidence | Open points |", "|---|---|---|---|---|---|---|---|---|"]
    for n, c in comps.items():
        k = c["counts"]
        md.append(f"| {n} | {c['title']} | {c['priority']} | {k['EVIDENCED']} | {k['PARTIAL']} | {k['BLOCKED']} | "
                  f"{k['NOT_DONE']} | {', '.join('`'+e+'`' for e in c['evidence']) or '—'} | {c['note'] or '—'} |")
    md += ["", "## Tool checks", ""] + [f"- `{k}`: exit {v['exit']}" for k, v in tools.items()]
    md += ["", "## Certification scale actually executed", "", "```", json.dumps(counts, indent=1, sort_keys=True), "```"]
    (out / "COMPONENT_STATUS.md").write_text("\n".join(md) + "\n")
    ann = CHECKLIST.read_text()
    it = iter(rows[15:])
    lines, comp = [], 0
    dod_iter = iter(rows[:15])
    for line in ann.splitlines():
        if line.startswith("- [ ] "):
            r = next(dod_iter) if comp == 0 else next(it)
            tag = f" — **{r['status']}**" + (f" ({r['reason']})" if r["reason"] else "") + \
                  (f" · evidence: {', '.join(r['evidence'])}" if r["evidence"] else "")
            line = line + tag
        m = re.match(r"## (\d+)\. ", line)
        if m:
            comp = int(m.group(1))
        lines.append(line)
    (out / "CHECKLIST_ANNOTATED.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"totals": tot, "tests": report["tests"], "failing": list(failing), "tools": {k: v["exit"] for k, v in tools.items()}}))
    return 0 if not failing and all(v["exit"] == 0 for v in tools.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
