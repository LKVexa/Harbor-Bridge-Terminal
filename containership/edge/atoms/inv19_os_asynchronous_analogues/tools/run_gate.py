"""MC-27 / MC-01 - INV-19 production gate and machine-readable evidence bundle.

    python tools/run_gate.py              # run everything, write evidence/, print verdict
    python tools/run_gate.py --verify     # independently re-verify an existing bundle
    python tools/run_gate.py --self-test  # negative verification: the gate must fail on bad input

Result per requirement: PASS / FAIL / BLOCKED / NOT_APPLICABLE.
* behaviour/security/platform/performance requirements PASS only on executable
  evidence (tests passing under BOTH ``python`` and ``python -O``, or measured
  evidence files); a skip whose reason starts with ``BLOCKED:`` is a blocker,
  any other skip is an *unexplained skip* and also blocks.
* documentation requirements PASS on a present, digest-bound document section.
* explicit blockers (owner decisions, human approvals, platforms not
  available) are carried verbatim.
Verdict: GO only with zero FAIL and zero BLOCKED; FAIL > 0 -> NO_GO; else BLOCKED.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile

PKG = pathlib.Path(__file__).resolve().parents[1]
EVID = PKG / "evidence"
sys.path.insert(0, str(PKG.parent))

from inv19_os_asynchronous_analogues.tools import supply_chain as sc  # noqa: E402
from inv19_os_asynchronous_analogues.tools.pk_core_preflight import preflight  # noqa: E402

SCHEMA = "PK_EVIDENCE/1"
TOOL_VERSION = "run_gate/1.0"

# kind, tests (id prefixes), docs ("path::marker"), evidence ("file::jsonpath==value"), blockers
T, D, E, B = "tests", "docs", "evidence", "blockers"
N = "test_native_backends."
C = "test_contracts."
S = "test_security_observability."
I = "test_integration."
F = "test_fuzz_adversarial."
TRACE: dict[int, dict] = {
    1: {"kind": "doc", D: ["contract.py::responsibility=", "README.md::## Responsibility"]},
    2: {"kind": "doc", D: ["contract.py::not_owns=", "README.md::## Explicitly does not own"]},
    3: {"kind": "doc", D: ["contract.py::dependencies="], T: [I + "WaitableSetTest.test_authoritative_binding_reported"]},
    4: {"kind": "doc", D: ["contract.py::source_of_truth="]},
    5: {"kind": "doc", D: ["contract.py::assumptions=", "governance/REQUIREMENTS.md::## C018"]},
    6: {"kind": "behaviour", D: ["contract.py::boundaries="], T: [C + "ResourceTest", S + "CrossTenantDriverTest"]},
    7: {"kind": "doc", D: ["contract.py::optional=", "governance/adr/ADR-005-native-ffi.md::Decision"]},
    8: {"kind": "doc", D: ["contract.py::non_goals=", "governance/adr/ADR-003-portable-fallback.md::Limitations"]},
    9: {"kind": "governance", D: ["governance/OWNERSHIP.md::Ownership transfer"], "owner_check": True},
    10: {"kind": "governance", D: ["governance/adr/ADR-001-readiness-vs-completion.md::Decision",
                                   "governance/adr/ADR-002-backend-selection-priority.md::Decision",
                                   "governance/adr/ADR-004-runtime-failover.md::Decision"], "adr_check": True},
    11: {"kind": "behaviour", T: [N + "IoUringTest.test_real_pipe_io_success_and_eof", N + "EpollTest", N + "PortableTest",
                                  I + "ParityTest", N + "CapabilityTest"], E: ["bench.json::decision.decision==PASS"],
         D: ["governance/REQUIREMENTS.md::## C011"]},
    12: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C012"], T: [I + "ParityTest"]},
    13: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C013"], T: [I + "FutureTest", I + "ParityTest"],
         E: ["bench.json::decision.decision==PASS"]},
    14: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C014"], T: [C + "ErrorTaxonomyTest", I + "ParityTest"]},
    15: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C015"], T: [F + "StateMachineFuzz", I + "FutureTest"]},
    16: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C016"], T: [C + "SchemaTest"]},
    17: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C017"], T: [C + "ResourceTest", I + "OverloadTest",
                                                                           F + "SecurityAbuse.test_resource_exhaustion_attack_is_contained"]},
    18: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C018"], T: [C + "PolicyTest", S + "CapabilityTest.test_key_rotation_revocation_outage"]},
    19: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C019"], T: [S + "CrossTenantDriverTest.test_audit_outage_fails_closed"]},
    20: {"kind": "generated", E: ["traceability.json::count==100"]},
    21: {"kind": "behaviour", D: ["schemas/PK_ASYNC_BACKEND_1.schema.json::$id", "schemas/PK_ASYNC_ARM_1.schema.json::$id",
                                  "schemas/PK_ASYNC_REAP_1.schema.json::$id", "README.md::## Interfaces"], T: [C + "SchemaTest"]},
    22: {"kind": "behaviour", T: [C + "SchemaTest"]},
    23: {"kind": "security", T: [S + "CapabilityTest"]},
    24: {"kind": "security", T: [S + "CapabilityTest", S + "CrossTenantDriverTest"]},
    25: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C025"], T: [C + "PolicyTest", I + "FutureTest.test_cancel_before_completion", I + "StreamCreditTest"]},
    26: {"kind": "behaviour", T: [C + "ErrorTaxonomyTest", C + "SchemaTest.test_live_error_objects_conform"]},
    27: {"kind": "behaviour", T: [C + "SchemaTest.test_negotiation", C + "SchemaTest.test_forward_compat_unknown_field_accepted_unknown_enum_rejected"]},
    28: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C017 / C028"], T: [C + "ResourceTest", F + "InputFuzz.test_oversized_event_batches_rejected", C + "SchemaTest.test_oversized_payload_rejected"]},
    29: {"kind": "behaviour", T: [C + "SchemaTest.test_every_fixture_validates", C + "SchemaTest.test_every_malformed_fixture_rejected"]},
    30: {"kind": "integration", T: [I + "ParityTest", I + "StreamCreditTest", I + "WaitableSetTest"], "adjacent_check": True},
    31: {"kind": "behaviour", T: [N + "IoUringTest.test_probe_reports_ops_and_reason"], "pk_core_check": True},
    32: {"kind": "behaviour", T: [C + "ConfigTest"], E: ["sbom.cdx.json::bomFormat==CycloneDX"]},
    33: {"kind": "behaviour", T: [C + "ConfigTest.test_defaults_valid_and_digest_stable"]},
    34: {"kind": "behaviour", T: [C + "ConfigTest.test_invalid_cannot_partially_activate", F + "InputFuzz.test_config_fuzz_never_partially_activates"]},
    35: {"kind": "behaviour", T: [C + "ConfigTest.test_precedence"]},
    36: {"kind": "behaviour", T: [C + "ConfigTest.test_provenance_has_no_secrets", C + "ConfigTest.test_failed_activation_hook_rolls_back_and_operator_rollback"]},
    37: {"kind": "behaviour", T: [C + "ConfigTest.test_concurrent_activation_is_atomic", C + "ConfigTest.test_invalid_cannot_partially_activate"]},
    38: {"kind": "behaviour", T: [C + "ConfigTest.test_failed_activation_hook_rolls_back_and_operator_rollback", I + "RecoveryTest"]},
    39: {"kind": "security", T: [S + "RedactionTest", C + "ConfigTest.test_invalid_cannot_partially_activate"]},
    40: {"kind": "behaviour", T: [N + "CapabilityTest.test_detect_is_operational_and_selects_highest", I + "ParityTest"],
         D: ["governance/RELEASE_PROCEDURE.md::## Day-0 / Day-1 / Day-2"]},
    41: {"kind": "security", D: ["governance/THREAT_MODEL.md::STRIDE"], T: [F + "SecurityAbuse"]},
    42: {"kind": "security", T: [S + "CapabilityTest.test_forged_expired_revoked_scope"]},
    43: {"kind": "security", T: [S + "CapabilityTest", S + "CrossTenantDriverTest"], D: ["governance/adr/ADR-005-native-ffi.md::Decision"]},
    44: {"kind": "security", T: [S + "CapabilityTest"], E: ["release_manifest.json::signature.alg==ed25519"],
         B: ["node/peer/provider attestation needs a platform identity/attestation service that is not present"]},
    45: {"kind": "security", E: ["release_manifest.json::signature.alg==ed25519", "self_test.json::all_caught==True"], "pk_core_check": True,
         B: ["release signing key is ephemeral, not KMS-bound (EX-004)"]},
    46: {"kind": "security", T: [S + "CrossTenantDriverTest", F + "SecurityAbuse.test_resource_exhaustion_attack_is_contained"],
         E: ["soak.json::fleet.isolation_ok==True"]},
    47: {"kind": "security", B: ["at-rest encryption of the audit log and managed key rotation require a KMS binding (security.key_ref is a reference only)"]},
    48: {"kind": "security", T: [S + "CapabilityTest.test_key_rotation_revocation_outage", S + "CrossTenantDriverTest.test_audit_outage_fails_closed",
                                 S + "RedactionTest.test_outage_policy_covers_every_dependency"]},
    49: {"kind": "security", T: [S + "AuditTest"]},
    50: {"kind": "security", T: [F + "SecurityAbuse", F + "ConcurrencyAdversary"]},
    51: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C051"], T: [I + "RecoveryTest"], E: ["soak.json::disaster.safe_states==True"]},
    52: {"kind": "behaviour", T: [I + "RecoveryTest.test_stall_detection"]},
    53: {"kind": "behaviour", T: [C + "PolicyTest.test_retry_bounded_and_idempotency_required", C + "PolicyTest.test_backoff_capped_no_overflow_with_jitter", C + "PolicyTest.test_retry_budget"]},
    54: {"kind": "behaviour", T: [C + "PolicyTest.test_admission_and_tenant_limit", C + "PolicyTest.test_circuit_breaker_recovers_via_half_open", I + "OverloadTest"]},
    55: {"kind": "behaviour", T: [I + "RecoveryTest.test_recovery_fails_inflight_exactly_once_then_failover"], D: ["governance/adr/ADR-004-runtime-failover.md::Decision"]},
    56: {"kind": "behaviour", T: [I + "RecoveryTest.test_open_failure_falls_back_with_reason", S + "AuditTest.test_sink_outage_buffers_then_refuses"]},
    57: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::## C057"], E: ["soak.json::disaster.forced_restart.restart_clean==True"]},
    58: {"kind": "behaviour", T: [I + "FutureTest.test_race_many_resolvers", F + "StateMachineFuzz.test_operation_table_invariants_and_id_reuse", F + "SecurityAbuse.test_spoofed_and_replayed_op_ids"]},
    59: {"kind": "behaviour", T: [I + "RecoveryTest.test_admin_quarantine_and_portable_protected"]},
    60: {"kind": "behaviour", T: [I + "RecoveryTest", N + "IoUringTest.test_fault_injected_setup_failure_rolls_back", N + "IoUringTest.test_seccomp_style_denial_probe_reason"],
         E: ["soak.json::disaster.safe_states==True"]},
    61: {"kind": "performance", E: ["bench.json::schema==PK_BENCH/1", "perf_baseline.json::results"]},
    62: {"kind": "performance", E: ["bench.json::decision.decision==PASS"]},
    63: {"kind": "performance", E: ["bench.json::decision.decision==PASS", "soak.json::burst.bounded_and_recovered==True"],
         B: ["scale-out / scale-in measurement requires a multi-node deployment"]},
    64: {"kind": "performance", E: ["bench.json::decision.decision==PASS", "soak.json::fleet.isolation_ok==True"]},
    65: {"kind": "doc", D: ["governance/REQUIREMENTS.md::## C065 / C066"], E: ["bench.json::decision.decision==PASS"]},
    66: {"kind": "doc", D: ["governance/REQUIREMENTS.md::## C065 / C066", "governance/adr/ADR-005-native-ffi.md::Decision"]},
    67: {"kind": "behaviour", T: [C + "ResourceTest", N + "EpollTest.test_event_burst_bounded_and_fair"], E: ["soak.json::soak.leak_detected==False"]},
    68: {"kind": "performance", B: ["power/thermal: no RAPL or thermal sensors exposed on the build host; constrained-edge hardware not available"]},
    69: {"kind": "doc", D: ["governance/REQUIREMENTS.md::## C069"], E: ["bench.json::overload"]},
    70: {"kind": "performance", E: ["bench.json::decision.decision==PASS", "bench.json::baseline_compared==True"]},
    71: {"kind": "behaviour", T: [S + "RedactionTest.test_snapshot_has_no_secrets", S + "ObservabilityTest.test_driver_explains_selection_and_propagates_trace"]},
    72: {"kind": "behaviour", T: [S + "ObservabilityTest.test_exposition_and_histogram", S + "ObservabilityTest.test_label_safety"]},
    73: {"kind": "behaviour", T: [S + "ObservabilityTest.test_driver_explains_selection_and_propagates_trace"]},
    74: {"kind": "behaviour", T: [S + "ObservabilityTest.test_trace_context", S + "ObservabilityTest.test_driver_explains_selection_and_propagates_trace"]},
    75: {"kind": "security", T: [S + "ObservabilityTest.test_label_safety", S + "RedactionTest"]},
    76: {"kind": "behaviour", T: [S + "ObservabilityTest.test_driver_explains_selection_and_propagates_trace", I + "RecoveryTest.test_open_failure_falls_back_with_reason"]},
    77: {"kind": "behaviour", T: [S + "ObservabilityTest.test_driver_explains_selection_and_propagates_trace"]},
    78: {"kind": "behaviour", T: [S + "ObservabilityTest.test_driver_explains_selection_and_propagates_trace"],
         B: ["correlation with the live infrastructure graph needs the platform topology service (release/config lineage is recorded)"]},
    79: {"kind": "doc", D: ["hostio/observability.py::TELEMETRY_POLICY", "hostio/audit.py::RETENTION"]},
    80: {"kind": "behaviour", T: [S + "ObservabilityTest.test_alert_rules_cover_required_signals"], D: ["governance/dashboard.json::panels"]},
    81: {"kind": "behaviour", T: ["test_backend.", F + "StateMachineFuzz"]},
    82: {"kind": "behaviour", T: [C + "SchemaTest", N + "EpollTest", N + "PortableTest"]},
    83: {"kind": "integration", T: [I + "ParityTest", I + "FutureTest", I + "StreamCreditTest", I + "WaitableSetTest"], "adjacent_check": True},
    84: {"kind": "platform", E: ["compat_matrix.json::schema==PK_COMPAT_MATRIX/1"], "matrix_check": True},
    85: {"kind": "security", T: [F + "InputFuzz", F + "RegressionCorpus"]},
    86: {"kind": "behaviour", T: [F + "ConcurrencyAdversary", N + "IoUringTest.test_concurrent_submit_and_reap", N + "EpollTest.test_concurrent_add_mod_del"]},
    87: {"kind": "security", D: ["governance/THREAT_MODEL.md::STRIDE"], T: [F + "SecurityAbuse", S + "CapabilityTest"]},
    88: {"kind": "performance", E: ["bench.json::decision.decision==PASS", "soak.json::verdict==PASS"], "soak_check": True},
    89: {"kind": "behaviour", E: ["soak.json::disaster.safe_states==True"], T: [I + "RecoveryTest"]},
    90: {"kind": "generated", E: ["self_test.json::all_caught==True"]},
    91: {"kind": "governance", D: ["contract.py::slos="], "owner_check": True},
    92: {"kind": "doc", D: ["governance/RELEASE_PROCEDURE.md::## Canary", "governance/RELEASE_PROCEDURE.md::## Rollback"]},
    93: {"kind": "generated", E: ["compat_matrix.json::schema==PK_COMPAT_MATRIX/1"], D: ["governance/LIFECYCLE.md::Support matrix"]},
    94: {"kind": "doc", D: ["governance/LIFECYCLE.md::Security patch SLA"]},
    95: {"kind": "behaviour", D: ["governance/REQUIREMENTS.md::C095"], T: [S + "AuditTest.test_offline_file_verifier"]},
    96: {"kind": "doc", D: ["governance/RELEASE_PROCEDURE.md::## Day-0 / Day-1 / Day-2"]},
    97: {"kind": "governance", D: ["governance/INCIDENT_RUNBOOK.md::Severity"], "owner_check": True},
    98: {"kind": "governance", D: ["governance/REVIEWS.md::Cadence"], B: ["no recurring review has been performed yet (needs named reviewers)"]},
    99: {"kind": "governance", D: ["governance/EXCEPTIONS.md::EX-001"], "exceptions_check": True},
    100: {"kind": "governance", D: ["governance/RELEASE_PROCEDURE.md::## Release checklist"], "exit_check": True},
}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_suite(optimize: bool, mutant: str = "") -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if mutant:
        env["INV19_MUTANT"] = mutant
    cmd = [sys.executable] + (["-O"] if optimize else []) + [str(PKG / "tools" / "_collect.py")]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=3600, cwd=str(PKG / "tests"))
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"optimized": int(optimize), "rows": [], "ran": 0, "crash": r.stderr[-2000:]}


def _get(doc, path):
    cur = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def check_evidence(spec: str, base: pathlib.Path) -> tuple[bool, str, dict]:
    fname, expr = spec.split("::", 1)
    p = base / fname
    art = {"path": f"evidence/{fname}", "sha256": sha(p) if p.exists() else None}
    if not p.exists():
        return False, f"missing evidence {fname}", art
    doc = json.loads(p.read_text())
    if isinstance(doc, dict) and doc.get("source_revision") not in (None, sc.source_revision()):
        return False, f"{fname}: stale evidence from another source revision", art
    if "==" in expr:
        path, want = expr.split("==", 1)
        got = _get(doc, path)
        ok = str(got) == want
        return ok, f"{fname}:{path}={got!r} (want {want})", art
    return _get(doc, expr) is not None, f"{fname}:{expr} present", art


def check_doc(spec: str) -> tuple[bool, str, dict]:
    path, marker = spec.split("::", 1)
    p = PKG / path
    art = {"path": path, "sha256": sha(p) if p.exists() else None}
    if not p.exists():
        return False, f"missing document {path}", art
    return marker in p.read_text(), f"{path} contains {marker!r}", art


def classify_tests(prefixes: list[str], runs: list[dict]) -> tuple[str, list[str], list[str]]:
    notes, blockers = [], []
    status = "PASS"
    for pre in prefixes:
        for run in runs:
            rows = [r for r in run["rows"] if r[0].startswith(pre)]
            mode = "python -O" if run["optimized"] else "python"
            if not rows:
                return "FAIL", [f"no tests matched {pre} under {mode}"], []
            for tid, outcome, msg in rows:
                if outcome in ("fail", "error"):
                    if "DEPENDENCY_UNAVAILABLE" in msg:
                        blockers.append(f"{tid}: dependency unavailable")
                    else:
                        status = "FAIL"
                        notes.append(f"{tid} {outcome} under {mode}")
                elif outcome == "skip":
                    blockers.append(f"{tid} [{mode}]: {msg if msg.startswith('BLOCKED') else 'UNEXPLAINED SKIP: ' + msg}")
            notes.append(f"{pre}: {sum(1 for r in rows if r[1] == 'pass')}/{len(rows)} pass under {mode}")
    return status, notes, sorted(set(blockers))


def special_blockers(n: int, spec: dict, ctx: dict) -> list[str]:
    out = []
    if spec.get("owner_check") and "UNASSIGNED" in (PKG / "governance/OWNERSHIP.md").read_text():
        out.append("accountable/operational owner and escalation contacts are UNASSIGNED (governance/OWNERSHIP.md)")
    if spec.get("adr_check"):
        prop = [p.name for p in (PKG / "governance/adr").glob("*.md") if "PROPOSED" in p.read_text()]
        if prop:
            out.append(f"ADRs awaiting approval by a named approver: {prop}")
    if spec.get("pk_core_check") and ctx["preflight"]["result"] != "GO":
        out.append("pk_core not pinned/installed: " + "; ".join(ctx["preflight"]["reasons"]))
    if spec.get("adjacent_check"):
        bad = {k: v for k, v in ctx["adjacent"].items() if v != "BOUND"}
        if bad:
            out.append(f"authoritative adjacent layers not installed: {sorted(bad)} (reference implementations tested)")
    if spec.get("matrix_check"):
        m = json.loads((EVID / "compat_matrix.json").read_text())
        un = [c["cell"] for c in m["cells"] if c["claim"] == "claimed" and c["status"] != "FULLY_SUPPORTED"]
        if un:
            out.append(f"claimed platform cells without current evidence: {un}")
    if spec.get("soak_check"):
        s = json.loads((EVID / "soak.json").read_text())
        if s["soak"]["release_criterion"] != "PASS":
            out.append(s["soak"]["release_criterion"])
    if spec.get("exceptions_check"):
        txt = (PKG / "governance/EXCEPTIONS.md").read_text()
        rows = [l for l in txt.splitlines() if l.startswith("| EX-")]
        today = dt.date.today().isoformat()
        for r in rows:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if "UNASSIGNED" in (cells[4], cells[5]):
                out.append(f"{cells[0]} has no owner/approver")
            if cells[6] < today:
                out.append(f"{cells[0]} expired {cells[6]}")
    if spec.get("exit_check"):
        out.append("production-exit record requires the release approver's countersignature and all other requirements PASS")
    return out


def assess(runs: list[dict], ctx: dict, base: pathlib.Path = EVID) -> list[dict]:
    rev = sc.source_revision()
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    recs = []
    for it in items:
        n = it["ordinal"]
        spec = TRACE[n]
        status, notes, blockers, arts = "PASS", [], [], []
        if spec.get(T):
            s, nn, bb = classify_tests(spec[T], runs)
            notes += nn; blockers += bb
            if s == "FAIL":
                status = "FAIL"
        for d in spec.get(D, []):
            ok, note, art = check_doc(d)
            notes.append(note); arts.append(art)
            if not ok:
                status = "FAIL"
        for e in spec.get(E, []):
            ok, note, art = check_evidence(e, base)
            notes.append(note); arts.append(art)
            if not ok:
                status = "FAIL"
        blockers += spec.get(B, []) + special_blockers(n, spec, ctx)
        if status == "PASS" and blockers:
            status = "BLOCKED"
        recs.append({"schema": SCHEMA, "check_id": it["check_id"], "ordinal": n, "dimension": it["dimension"],
                     "requirement": it["requirement"], "result": status, "evidence_type": spec["kind"],
                     "source_revision": rev, "artifacts": arts, "tests": spec.get(T, []),
                     "test_run_digest": ctx["test_digest"], "timestamp": now,
                     "platform": f"{platform.system()}-{platform.machine()}-{platform.release()}",
                     "config_digest": ctx["config_digest"],
                     "dependency_versions": {"python": platform.python_version(),
                                             "pk_core": ctx["preflight"].get("installed_version") or "UNAVAILABLE",
                                             "cryptography": sc._crypto_version() or "NOT_INSTALLED"},
                     "producer": TOOL_VERSION, "notes": notes[:12], "blockers": blockers})
    return recs


def chain(recs: list[dict]) -> list[dict]:
    prev = "0" * 64
    for r in recs:
        r["prev"] = prev
        prev = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
    return recs


def bundle_digest(recs: list[dict]) -> str:
    return hashlib.sha256("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs).encode()).hexdigest()


def gate_result(recs: list[dict], rev: str) -> dict:
    cnt = {k: sum(1 for r in recs if r["result"] == k) for k in ("PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE")}
    verdict = "GO" if cnt["FAIL"] == 0 and cnt["BLOCKED"] == 0 and len(recs) == 100 else \
        ("NO_GO" if cnt["FAIL"] else "BLOCKED")
    return {"schema": "PK_GATE_RESULT/1", "element": "INV-19", "release": sc.VERSION, "source_revision": rev,
            "verdict": verdict, "counts": cnt, "total": len(recs),
            "blockers": {r["check_id"]: r["blockers"] for r in recs if r["result"] == "BLOCKED"},
            "failures": {r["check_id"]: [x for x in r["notes"] if "fail" in x or "missing" in x or "want" in x]
                         for r in recs if r["result"] == "FAIL"},
            "evidence_bundle_digest": bundle_digest(recs)}


def sign(data: bytes, key_path: pathlib.Path) -> dict:
    k = sc._key(key_path)
    from cryptography.hazmat.primitives import serialization
    return {"alg": "ed25519", "sig": k.sign(data).hex(),
            "public_key": k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()}


def verify_bundle(base: pathlib.Path = EVID, pkg: pathlib.Path = PKG) -> tuple[bool, list[str]]:
    """Independent verification: chain, signature, revision, artifact digests,
    and cross-validation of every result against the raw test outcomes."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    probs = []
    try:
        lines = (base / "evidence_bundle.jsonl").read_text().splitlines()
        recs = [json.loads(l) for l in lines if l.strip()]
        sig = json.loads((base / "evidence_bundle.sig.json").read_text())
        gate = json.loads((base / "gate_result.json").read_text())
        raw = json.loads((base / "test_results.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"missing/corrupt evidence: {exc}"]
    if len(recs) != 100:
        probs.append(f"bundle has {len(recs)} records, expected 100")
    prev = "0" * 64
    for r in recs:
        if r.get("prev") != prev:
            probs.append(f"chain broken at {r.get('check_id')}")
            break
        prev = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig["public_key"])).verify(
            bytes.fromhex(sig["sig"]), bundle_digest(recs).encode())
    except (InvalidSignature, ValueError, KeyError):
        probs.append("bundle signature invalid")
    if gate.get("evidence_bundle_digest") != bundle_digest(recs):
        probs.append("gate result does not reference this bundle")
    old = sc.PKG
    sc.PKG = pkg
    try:
        rev = sc.source_revision()
    finally:
        sc.PKG = old
    for r in recs:
        if r["source_revision"] != rev:
            probs.append(f"{r['check_id']}: evidence from another revision")
            break
    raw_digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    for r in recs:
        if r["test_run_digest"] != raw_digest:
            probs.append(f"{r['check_id']}: test results file does not match the run the record cites")
            break
        for a in r["artifacts"]:
            p = (pkg / a["path"])
            if a["sha256"] is None or not p.exists():
                if r["result"] != "FAIL":
                    probs.append(f"{r['check_id']}: missing artifact {a['path']}")
            elif sha(p) != a["sha256"]:
                probs.append(f"{r['check_id']}: artifact digest mismatch {a['path']}")
        if r["tests"]:
            s, _, bb = classify_tests(r["tests"], raw["runs"])
            derived = "FAIL" if s == "FAIL" else r["result"]
            if r["result"] == "PASS" and (s == "FAIL" or bb):
                probs.append(f"{r['check_id']}: marked PASS but raw test outcomes say {s}{' + blockers' if bb else ''}")
            elif derived != r["result"]:
                probs.append(f"{r['check_id']}: result {r['result']} inconsistent with raw tests")
    if gate.get("verdict") == "GO" and any(r["result"] != "PASS" for r in recs):
        probs.append("GO verdict with non-PASS records")
    return (not probs), probs


def produce(ctx_extra: dict | None = None, mutant: str = "") -> dict:
    EVID.mkdir(exist_ok=True)
    runs = [run_suite(False, mutant), run_suite(True, mutant)]
    raw = {"runs": runs}
    (EVID / "test_results.json").write_text(json.dumps(raw, sort_keys=True))
    from inv19_os_asynchronous_analogues.hostio.integration import bind_authoritative
    from inv19_os_asynchronous_analogues.hostio.config import ConfigStore
    ctx = {"preflight": preflight(), "adjacent": bind_authoritative(),
           "config_digest": ConfigStore().active.digest,
           "test_digest": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()}
    (EVID / "pk_core_preflight.json").write_text(json.dumps(ctx["preflight"], indent=1, sort_keys=True))
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    (EVID / "traceability.json").write_text(json.dumps(
        {"count": len(TRACE), "matrix": {it["check_id"]: TRACE[it["ordinal"]] for it in items}}, indent=1, sort_keys=True))
    recs = chain(assess(runs, ctx))
    rev = recs[0]["source_revision"]
    (EVID / "evidence_bundle.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    g = gate_result(recs, rev)
    g["tests"] = {("python -O" if r["optimized"] else "python"): {
        "ran": r["ran"], "pass": sum(1 for x in r["rows"] if x[1] == "pass"),
        "fail": sum(1 for x in r["rows"] if x[1] in ("fail", "error")),
        "skip": sum(1 for x in r["rows"] if x[1] == "skip")} for r in runs}
    g["pk_core_gate"] = ctx["preflight"]["result"]
    (EVID / "gate_result.json").write_text(json.dumps(g, indent=1, sort_keys=True))
    (EVID / "evidence_bundle.sig.json").write_text(json.dumps(
        sign(bundle_digest(recs).encode(), EVID / ".release_signing_key"), indent=1))
    return g


def self_test() -> dict:
    """Negative verification in a scratch copy: every tamper must be caught."""
    res = {}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="inv19_selftest_"))
    try:
        dst = tmp / PKG.name
        shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns("__pycache__"))
        ev = dst / "evidence"
        res["baseline_verifies"] = verify_bundle(ev, dst)[0]
        # 1 remove required evidence
        b = ev / "bench.json"; saved = b.read_bytes(); b.unlink()
        res["removed_evidence_caught"] = not verify_bundle(ev, dst)[0]; b.write_bytes(saved)
        # 2 alter an artifact
        d = dst / "governance/THREAT_MODEL.md"; saved = d.read_bytes(); d.write_bytes(saved + b"\n")
        res["altered_artifact_caught"] = not verify_bundle(ev, dst)[0]; d.write_bytes(saved)
        # 3 evidence from another revision (source changed after the run)
        s = dst / "hostio/errors.py"; saved = s.read_bytes(); s.write_bytes(saved + b"\n# drift\n")
        res["stale_revision_caught"] = not verify_bundle(ev, dst)[0]; s.write_bytes(saved)
        # 4 a failed test marked PASS in the raw results is caught by cross-validation
        raw_p = ev / "test_results.json"; raw_s = raw_p.read_bytes()
        raw = json.loads(raw_s)
        for run in raw["runs"]:
            for row in run["rows"]:
                if row[0].startswith("test_contracts.ErrorTaxonomyTest"):
                    row[1] = "fail"
        raw_p.write_text(json.dumps(raw, sort_keys=True))
        res["failed_test_marked_pass_caught"] = not verify_bundle(ev, dst)[0]; raw_p.write_bytes(raw_s)
        # 5 flip a BLOCKED record to PASS inside the bundle
        bp = ev / "evidence_bundle.jsonl"; bs = bp.read_bytes()
        lines = bs.decode().splitlines()
        j = next(i for i, l in enumerate(lines) if '"result": "BLOCKED"' in l)
        lines[j] = lines[j].replace('"result": "BLOCKED"', '"result": "PASS"')
        bp.write_text("\n".join(lines) + "\n")
        res["forged_result_caught"] = not verify_bundle(ev, dst)[0]; bp.write_bytes(bs)
        # 6 pk_core removed -> preflight BLOCKED, never skipped-success
        res["pk_core_absent_blocks"] = preflight(env_path="/nonexistent")["result"] == "BLOCKED"
        # 7 known-bad implementation: readiness fabricating completions must fail the suite
        bad = run_suite(False, mutant="fabricate_completion")
        res["known_bad_readiness_mutant_fails"] = any(r[1] in ("fail", "error") for r in bad["rows"]
                                                       if r[0].startswith("test_integration.ParityTest"))
        bad2 = run_suite(False, mutant="drop_completion_error")
        res["known_bad_error_swallow_mutant_fails"] = any(r[1] in ("fail", "error") for r in bad2["rows"]
                                                          if r[0].startswith(("test_integration.", "test_backend.")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    res["all_caught"] = all(v for k, v in res.items())
    (EVID / "self_test.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.verify:
        ok, probs = verify_bundle()
        print(json.dumps({"verified": ok, "problems": probs[:30]}, indent=1))
        return 0 if ok else 3
    if a.self_test:
        r = self_test()
        print(json.dumps(r, indent=1))
        return 0 if r["all_caught"] else 4
    g = produce()
    print(json.dumps({k: g[k] for k in ("verdict", "counts", "tests", "pk_core_gate", "evidence_bundle_digest")}, indent=1))
    return {"GO": 0, "BLOCKED": 2, "NO_GO": 1}[g["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
