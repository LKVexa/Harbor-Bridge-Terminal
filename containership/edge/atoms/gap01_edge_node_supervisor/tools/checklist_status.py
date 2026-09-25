"""Item-level status for the Professional Missing-Components Checklist v1.0.0.

The checklist uses five template families (the check at position N means
something different in each family):

  CORE  components 1-15   engineering/runtime checks
  SEC   components 16-30  security checks
  OBS   components 31-40  observability/operations checks
  VER   components 41-60  verification/packaging/governance checks
  DOC   components 61-70  documentation/package artifact checks

Each family has a default judgment per check (evidence, open, or n/a);
components override where their situation differs.  Marks:
  [x] evidenced (evidence cited)   [ ] open (gap / exception cited)   [-] n/a (reason cited)
"""
from __future__ import annotations

import json
import pathlib
import re

PKG = pathlib.Path(__file__).resolve().parents[1]
SRC = PKG / "docs" / "GAP01_Professional_Missing_Components_Checklist_v1.0.0.md"
TC, TP, TI, TB = ("tests/test_controller.py", "tests/test_production.py", "tests/test_integration.py",
                  "tests/test_bootstrap_inventory.py")
X, O, NA = "x", " ", "-"  # noqa: E741

# ---- family defaults: check -> (mark, text); "{impl}" / "{tests}" are substituted per component
CORE = {
    1: (X, "{impl}; ADR-0001 authority table"), 2: (X, "docs/REQUIREMENTS.md"),
    3: (X, "supervisor.TRANSITIONS; controller degraded-mode sets"), 4: (X, "schemas/*.schema.json (/1)"),
    5: (X, "errors.ERROR_CATALOG"), 6: (X, "request_id completion records; nonce window"),
    7: (X, "controller.lock serialization"), 8: (X, "ADR-0006 MonotonicClock"),
    9: (X, "config.SCHEMA"), 10: (X, "store.StateStore checkpoint+WAL"), 11: (X, "controller.start reconciliation"),
    12: (X, "PARTITION_ALLOWED / EMERGENCY_ALLOWED"), 13: (X, "security.Authenticator"),
    14: (X, "security.AuthorizationPolicy"), 15: (X, "schema_validator + size cap"),
    16: (X, "systemd sandbox (static; runtime check EXC-005)"), 17: (X, "docs/CAPACITY.md ceilings"),
    18: (X, "fail closed; persistence failure -> emergency"), 19: (X, "observability.Metrics"),
    20: (X, "JSON logs with event_id/request_id/trace_id"), 21: (X, "Tracer handle/apply/persist spans"),
    22: (X, "controller.diagnostics"), 23: (X, "{tests}"), 24: (X, f"{TC}::PropertyTest (300 seeds)"),
    25: (X, f"{TC}::ConcurrencyTest"), 26: (X, f"{TI}::ProcessChaosTest; {TP}::StoreTest"),
    27: (X, "{tests}"), 28: (X, "evidence/bench.json"), 29: (X, "docs/RUNBOOKS.md; docs/PLATFORMS_AND_COMPATIBILITY.md"),
    30: (O, "owner and production-exit approval not assigned (EXC-001)"),
}
SEC = {
    1: (X, "docs/THREAT_MODEL.md"), 2: (X, "THREAT_MODEL crypto/key table"), 3: (X, "ADR-0005 fail-closed model"),
    4: (X, "security.Authenticator (per-caller HMAC)"), 5: (X, "AuthorizationPolicy deny-by-default"),
    6: (X, "nonce + ts skew + request_id + cordon generation"), 7: (X, "HMAC-SHA256 parameters (THREAT_MODEL)"),
    8: (O, "key expiry not enforced; rotation requires restart"), 9: (X, f"redaction; {TP}::test_redaction, test_secret_boundary"),
    10: (X, "schema_validator; stale/future/duplicate rejection"),
    11: (X, "deny-by-default; signed config required unless --allow-unsigned-config"),
    12: (X, "AuditLog records actor/op/args/state/generation/trace_id"),
    13: (O, "tail truncation needs an off-node head anchor (documented, not automated)"),
    14: (X, "docs/CAPACITY.md ceilings; systemd limits"), 15: (X, "RateLimiter per caller and op class"),
    16: (X, "partition/emergency modes"), 17: (X, "WAL recovery; durable request_id dedup"),
    18: (O, "hot-reloaded config not persisted/versioned for rollback"),
    19: (O, "override-use and trust-expiry metrics missing (codes covered by requests_total)"),
    20: (X, "stable event_ids + levels + audit"), 21: (X, f"{TC}::PipelineTest, FuzzTest; {TP}::SecurityTest"),
    22: (X, f"{TC}::test_authz_denied_is_audited, test_operator_override (API level; OS level EXC-005)"),
    23: (X, f"{TC}::FuzzTest, PropertyTest"), 24: (X, f"{TP}::StoreTest; {TC}::SafetyModesTest; {TI}"),
    25: (X, "stdlib-only runtime; sbom.cdx.json"), 26: (X, "docs/RUNBOOKS.md RB-05/08/09"),
    27: (X, "expiring override grants with reason; break-glass role; audited"),
    28: (O, "security overhead under adversarial load not measured"),
    29: (O, "threat-model mapping done; owners unassigned (EXC-001)"),
    30: (O, "security review gate (EXC-012)"),
}
OBS = {
    1: (X, "docs/OBSERVABILITY.md; alert rules"), 2: (X, "docs/OBSERVABILITY.md units/semantics"),
    3: (X, "stable names; TelemetryContractTest"), 4: (X, "LABEL_DOMAINS -> 'other'"),
    5: (X, "counter/gauge/histogram with fixed buckets"), 6: (X, "requests by outcome/code, in_flight, pressure, reconcile counters"),
    7: (X, "JsonFormatter event schema"), 8: (X, f"redact(); {TP}::test_redaction"),
    9: (X, "handle -> apply -> persist spans; traceparent in"), 10: (X, "/livez vs /readyz semantics"),
    11: (X, "OBSERVABILITY SLI/SLO table"), 12: (X, "no-budget SLOs page on any event"),
    13: (X, "deploy/prometheus/alertmanager-inhibit.yml"), 14: (X, "RUNBOOKS per alert"),
    15: (X, "controller.diagnostics"), 16: (X, "OBSERVABILITY retention"),
    17: (X, "exporter errors suppressed; bounded ring (log sink stall is open, see 18/24)"),
    18: (O, "per-request telemetry overhead not isolated"), 19: (X, "monotonic time for durations"),
    20: (X, "gap01_build_info{version}; version in START log"),
    21: (O, "not every emission path has a dedicated assertion"),
    22: (X, f"{TP}::TelemetryContractTest"), 23: (X, "evidence/soak.json"),
    24: (X, f"{TP}::TelemetryContractTest::test_exporter_loss_does_not_affect_control"),
    25: (O, "no corruption/partial-bundle test for diagnostics export"),
    26: (O, "dashboards not shipped (EXC-013)"), 27: (O, "on-call ownership (EXC-001)"),
    28: (O, "alert rules not validated with promtool in CI"),
    29: (O, "no dedicated telemetry evidence artifact"), 30: (O, "depends on 26-29"),
}
VER = {
    1: (X, "{impl}"), 2: (O, "owner/approvers unassigned (EXC-001)"), 3: (X, "{impl}"),
    4: (X, "requirements-dev.txt pinned; hash lock EXC-006"), 5: (X, "clean-room extract+verify (evidence)"),
    6: (X, "RELEASE_MANIFEST version + tree sha256"), 7: (X, "ruff, mypy, schema validation"),
    8: (X, "{tests}"), 9: (X, f"{TI} (live control plane EXC-014)"), 10: (X, "examples/fixtures compat_*"),
    11: (X, f"{TC}::ConcurrencyTest"), 12: (X, f"{TC}::FuzzTest, PropertyTest"),
    13: (X, f"{TI}::ProcessChaosTest; {TP}::StoreTest"), 14: (X, "evidence/soak.json"),
    15: (X, "tools/perf_gate.py"), 16: (X, "coverage >= 85% gate (~90% lines)"),
    17: (X, "examples/fixtures"), 18: (X, "TRACEABILITY.json"), 19: (X, "tools/evidence.py"),
    20: (X, "RELEASE_MANIFEST sha256 (+optional HMAC)"),
    21: (O, "branch protection / override capture not configurable from the package"),
    22: (O, "advisory vs blocking CI classes not separated"),
    23: (O, "clean install per platform (EXC-009)"), 24: (X, "migrate() refuses newer schema"),
    25: (X, "docs/PLATFORMS_AND_COMPATIBILITY.md"), 26: (X, "README; RUNBOOKS; tools docstrings"),
    27: (X, "SUPPORT.md evidence retention"), 28: (O, "CI actions pinned by tag, not commit SHA"),
    29: (O, "independent review (EXC-012)"), 30: (X, "tools/exit_gate.py"),
}
DOC = {
    1: (X, "{impl}"), 2: (O, "owner/review cadence (EXC-001)"), 3: (X, "{impl}"),
    4: (X, "tools/check_repo.py link check"), 5: (X, "check_repo + exit_gate in evidence/CI"),
    6: (X, "JSON parse + link checks"), 7: (X, "VERSION 5.0.0 across artifacts"),
    8: (X, "RELEASE_MANIFEST / CHECKSUMS.sha256"), 9: (X, "authoritative source in repo"),
    10: (X, "DEPENDENCIES.md"), 11: (X, "examples/sequences"), 12: (X, "examples/fixtures invalid_*"),
    13: (X, "check_repo secret scan"), 14: (X, "tools/check_repo.py"), 15: (X, "PLATFORMS_AND_COMPATIBILITY.md"),
    16: (X, "PLATFORMS_AND_COMPATIBILITY.md downgrade"), 17: (X, "compat tables"),
    18: (X, "RUNBOOKS Day 0"), 19: (X, "RUNBOOKS RB-03..13"), 20: (X, "README Policies"),
    21: (X, "sbom.cdx.json"), 22: (O, "license not selected (EXC-011)"), 23: (X, "RELEASE_MANIFEST entry"),
    24: (O, "extraction tested on Linux only (EXC-009)"), 25: (X, "tools/check_repo.py"),
    26: (O, "doc-review-on-change needs an owner process (EXC-001)"), 27: (X, "evidence/evidence.json"),
    28: (X, "EXCEPTIONS.md"), 29: (X, "CHANGELOG 5.0.0"), 30: (X, "exit_gate EXIT-07 + check_repo"),
}
FAMILY = {**{c: CORE for c in range(1, 16)}, **{c: SEC for c in range(16, 31)},
          **{c: OBS for c in range(31, 41)}, **{c: VER for c in range(41, 61)},
          **{c: DOC for c in range(61, 71)}}

VER_NONRUNTIME_NA = {n: (NA, "static artifact; not exercised at runtime") for n in (11, 12, 13, 14, 15)}

# ---- per-component: impl, tests, overrides {check: (mark, text)}
S: dict[int, tuple[str, str, dict]] = {
    1: ("bootstrap.py phases/recovery/attestation", f"{TB}::BootstrapTest, IntegrityPhaseTest",
        {13: (NA, "internal, not caller-invoked"), 14: (NA, "internal"), 19: (O, "no boot metrics"),
         21: (O, "no boot spans"), 24: (O, "run_phases not property-tested"), 25: (NA, "boot is sequential"),
         28: (O, "boot time not benchmarked"), 16: (O, "measured boot/TPM (EXC-002)")}),
    2: ("inventory.py", f"{TB}::InventoryTest",
        {6: (NA, "read-only"), 7: (NA, "read-only"), 11: (NA, "stateless"), 24: (O, "no property tests"),
         25: (O, "no concurrency tests"), 27: (O, "validated only in a container (no GPU/NUMA/firmware)"),
         28: (O, "not benchmarked"), 21: (O, "no spans")}),
    3: ("runtime.py adapter protocol, ProcessAdapter, FakeRuntime", f"{TI}; {TC}::DrainTest",
        {27: (O, "wasm/microVM/unikernel adapters (EXC-004)"), 28: (O, "per-runtime latency (EXC-004)"),
         16: (O, "per-runtime sandboxing (EXC-004/005)")}),
    4: ("store.StateStore", f"{TP}::StoreTest", {13: (NA, "internal"), 14: (NA, "internal; 0700 dir")}),
    5: ("controller.start", f"{TC}::ReconciliationTest; {TI}::ProcessChaosTest",
        {13: (NA, "internal"), 14: (NA, "internal")}),
    6: ("schemas/*.schema.json + schema_validator.py", f"{TB}::SchemaFixtureTest",
        {n: (NA, "static schema") for n in (6, 7, 10, 11, 12, 16, 18, 19, 20, 21, 22, 25)}
        | {28: (X, "validation included in request p99")}),
    7: ("server.ControlServer + Authenticator", f"{TI}::test_socket_permissions; {TC}::PipelineTest",
        {28: (O, "socket round-trip not benchmarked"), 13: (X, "local HMAC (remote mTLS EXC-003)")}),
    8: ("security.AuthorizationPolicy", f"{TP}::SecurityTest; {TC}::test_authz_denied_is_audited", {}),
    9: ("health.HealthRegistry", f"{TP}::HealthTest", {}),
    10: ("controller.Watchdog + sd_notify", f"{TC}::test_readiness_liveness_watchdog",
         {6: (NA, "no requests"), 10: (NA, "volatile by design"), 27: (O, "real systemd WatchdogSec (EXC-005)")}),
    11: ("runtime.ReclaimProof", f"{TC}::test_unproven_reclaim_never_stops_node; {TI}",
         {27: (O, "cgroup/VM reclaim (EXC-004)"), 28: (O, "reclaim latency (EXC-004)")}),
    12: ("cordon generation + cordon_ack", f"{TC}::test_cordon_ack_generation",
         {27: (O, "live scheduler (EXC-014)")}),
    13: ("controller.drain_tick / DrainIntent / drain_override", f"{TC}::DrainTest; {TI}", {}),
    14: ("controller.lock", f"{TC}::ConcurrencyTest", {28: (O, "lock contention not benchmarked")}),
    15: ("store.record_completion", f"{TC}::test_idempotent_request_id; {TP}::test_idempotency_window_bounded", {}),
    16: ("config.py", f"{TP}::ConfigTest", {}),
    17: ("config.SecretBoundary", f"{TP}::test_secret_boundary",
         {7: (O, "encryption at rest delegated to host (EXC-007)")}),
    18: ("security.NodeIdentity; boot_attestation.json", f"{TP}::test_attestation",
         {2: (O, "no hardware trust root (EXC-002)"), 4: (O, "node not authenticated to a remote verifier (EXC-002)"),
          22: (O, "EXC-002")}),
    19: ("verify_artifacts; config signatures; integrity boot phase", f"{TP}::test_artifact_verification; {TB}::IntegrityPhaseTest", {}),
    20: ("PARTITION_ALLOWED", f"{TC}::test_partitioned_refuses_admit", {24: (X, "simulated partition (real network: EXC-014)")}),
    21: ("partition state machine", f"{TC}::test_partition_state_machine", {}),
    22: ("inventory.pressure + PRESSURE_BLOCKED", f"{TC}::test_pressure_blocks_admission", {}),
    23: ("atomic_write; torn-tail handling", f"{TP}::StoreTest; {TI}::ProcessChaosTest",
         {24: (O, "true power cut on real storage not tested")}),
    24: ("security.RateLimiter", f"{TC}::test_rate_limit", {}),
    25: ("errors.py", f"{TP}::ErrorModelTest", {}),
    26: ("store.AuditLog", f"{TP}::test_audit_chain_detects_tamper", {}),
    27: ("docs/THREAT_MODEL.md", "threat table test column", {}),
    28: ("systemd sandbox", "static review",
         {22: (O, "OS-level escalation test on real host (EXC-005)"), 24: (O, "EXC-005")}),
    29: ("FuzzTest + PropertyTest", f"{TC}", {}),
    30: ("enter_emergency + EMERGENCY_ALLOWED", f"{TC}::test_emergency_mode", {}),
    31: ("observability.Metrics", f"{TP}::TelemetryContractTest", {}),
    32: ("JsonFormatter/log_event", f"{TP}::test_redaction", {}),
    33: ("observability.Tracer", f"{TP}::test_trace_propagation", {17: (X, "exporter errors suppressed"),
                                                                   26: (O, "OTLP exporter + dashboards (EXC-013)")}),
    34: ("probes /livez /readyz", f"{TI}", {}),
    35: ("controller.diagnostics", f"{TP}::test_diagnostics_is_bounded_and_redacted", {}),
    36: ("SLOTracker", f"{TC}::PropertyTest", {}),
    37: ("alert rules + inhibit + runbooks", "docs review", {}),
    38: ("backup/restore + timer", f"{TP}::test_backup_restore", {}),
    39: ("store.migrate", f"{TP}::test_migration", {}),
    40: ("DISABLED flag", f"{TC}::test_emergency_disable_persists", {}),
    41: ("requirements*.txt, pyproject", "RELEASE_MANIFEST", {4: (O, "hash lock (EXC-006)"), **VER_NONRUNTIME_NA}),
    42: ("tools/build_release.py", "RELEASE_MANIFEST.json", VER_NONRUNTIME_NA),
    43: (".github/workflows/ci.yml", "workflow", {**VER_NONRUNTIME_NA, 5: (O, "CI never executed (EXC-009)")}),
    44: ("mypy config", "mypy clean", VER_NONRUNTIME_NA),
    45: ("ruff config", "ruff clean", VER_NONRUNTIME_NA),
    46: ("coverage tooling", "evidence/coverage.json", {**VER_NONRUNTIME_NA, 16: (X, "lines ~90%; branch via coverage.py in CI")}),
    47: ("tests/helpers.Harness + real-socket tests", f"{TI}", {9: (O, "live control plane (EXC-014)")}),
    48: ("ConcurrencyTest", f"{TC}::ConcurrencyTest", {}),
    49: ("tools/soak.py", "evidence/soak.json", {9: (O, "many-node live control plane (EXC-014)")}),
    50: ("tools/bench.py + perf_gate", "evidence/bench.json", {15: (X, "budgets in perf_gate (power: EXC-008)")}),
    51: ("chaos tests", f"{TI}; {TP}", {}),
    52: ("examples/fixtures", f"{TB}::SchemaFixtureTest", {}),
    53: ("tools/traceability.py", "TRACEABILITY.json", VER_NONRUNTIME_NA),
    54: ("tools/evidence.py", "evidence/evidence.json", VER_NONRUNTIME_NA),
    55: ("docs/ARCHITECTURE_DECISIONS.md", "docs review", {**VER_NONRUNTIME_NA, 1: (O, "ADRs not approved (EXC-001)")}),
    56: ("deploy/systemd/*", "static review", {**VER_NONRUNTIME_NA, 9: (O, "not installed on a host (EXC-005)")}),
    57: ("docs/PLATFORMS_AND_COMPATIBILITY.md", "docs review", {**VER_NONRUNTIME_NA, 9: (O, "matrix unexecuted (EXC-009)")}),
    58: ("config ceilings + CAPACITY.md", f"{TC}::test_capacity", {}),
    59: ("scoped per ADR-0001; deterministic drain order; per-caller buckets", "docs/CAPACITY.md#Fairness",
         {**VER_NONRUNTIME_NA, 11: (X, f"{TC}::ConcurrencyTest")}),
    60: ("tools/exit_gate.py", "evidence/exit_gate.json", VER_NONRUNTIME_NA),
    61: ("README (MASTER.md reference removed)", "exit_gate EXIT-07", {}),
    62: ("LICENSE placeholder, NOTICE", "files", {1: (O, "license not selected (EXC-011)"), 30: (O, "EXC-011")}),
    63: ("DEPENDENCIES.md", "docs", {27: (O, "pk_core gate not run (EXC-010)")}),
    64: ("schemas/*.schema.json", f"{TB}::SchemaFixtureTest", {}),
    65: ("deploy/config + systemd unit", "static review", {18: (X, "RUNBOOKS Day 0 (host install unverified EXC-005)")}),
    66: ("sbom.cdx.json", "tools/build_release.py", {}),
    67: ("SECURITY.md, SUPPORT.md", "docs", {}),
    68: ("examples/sequences + fixtures", "examples/", {}),
    69: ("docs/RUNBOOKS.md", "docs", {}),
    70: ("PLATFORMS_AND_COMPATIBILITY.md#Version-compatibility", "compat fixtures", {}),
}


def judge(comp: int, n: int) -> tuple[str, str]:
    impl, tests, over = S[comp]
    mark, text = over.get(n) or FAMILY[comp][n]
    return mark, text.replace("{impl}", impl).replace("{tests}", tests)


def main() -> None:
    text = SRC.read_text()
    eg_path = PKG / "evidence" / "exit_gate.json"
    exit_gate = json.loads(eg_path.read_text()) if eg_path.exists() else {}
    out: list[str] = []
    stats = {X: 0, O: 0, NA: 0}
    per: dict[int, dict] = {}
    rows = []
    cur = None
    for line in text.splitlines():
        m = re.match(r"^## (\d+)\. ", line)
        if m:
            cur = int(m.group(1))
            per[cur] = {X: 0, O: 0, NA: 0}
        m = re.match(r"^- \[ \] \*\*(\d+)\.(\d+)\*\* (.*)$", line)
        if m and cur:
            n = int(m.group(2))
            mark, note = judge(cur, n)
            label = {X: "Evidence", O: "OPEN", NA: "N/A"}[mark]
            stats[mark] += 1
            per[cur][mark] += 1
            rows.append({"id": f"{m.group(1)}.{m.group(2)}", "mark": mark, "note": note})
            out.append(f"- [{mark}] **{m.group(1)}.{m.group(2)}** {m.group(3)}  \n  _{label}: {note}_")
            continue
        m = re.match(r"^- \[ \] \*\*(EXIT-\d+)\*\* (.*)$", line)
        if m:
            key = next((k for k in exit_gate.get("items", {}) if k.startswith(m.group(1) + " ")), None)
            ok = bool(key and exit_gate["items"][key])
            out.append(f"- [{'x' if ok else ' '}] **{m.group(1)}** {m.group(2)}  \n  _exit_gate: {'PASS' if ok else 'FAIL'}_")
            continue
        if cur and line.startswith("- Owner:"):
            impl, tests, over = S[cur]
            ids = sorted({e for n in range(1, 31) for e in re.findall(r"EXC-\d+", judge(cur, n)[1])})
            out += ["- Owner: unassigned (EXC-001)", f"- Source/implementation path: {impl}",
                    f"- Test/evidence path: {tests}",
                    "- Schema/API version: PK_NODE_LIFECYCLE/1, PK_DRAIN/1, PK_NODE_HEALTH/1; state schema 2; package 5.0.0",
                    "- Security review: self-review via docs/THREAT_MODEL.md; independent review open (EXC-012)",
                    "- Performance/scale result: evidence/bench.json, evidence/soak.json",
                    "- Runbook/operations reference: docs/RUNBOOKS.md",
                    f"- Exception(s), if any: {', '.join(ids) or 'none'}",
                    f"- Production-exit approval: not granted (exit gate verdict {exit_gate.get('verdict', 'not run')})"]
            continue
        if cur and re.match(r"^- (Source/implementation path|Test/evidence path|Schema/API version|Security review|"
                            r"Performance/scale result|Runbook/operations reference|Exception\(s\), if any|"
                            r"Production-exit approval):", line):
            continue
        out.append(line)
    names = dict(re.findall(r"^## (\d+)\. (.+)$", text, re.M))
    fam_name = {**{c: "core" for c in range(1, 16)}, **{c: "security" for c in range(16, 31)},
                **{c: "observability" for c in range(31, 41)}, **{c: "verification" for c in range(41, 61)},
                **{c: "docs/package" for c in range(61, 71)}}
    head = ["# GAP-01 — Missing-Components Checklist: v5.0.0 Status", "",
            "Generated by `tools/checklist_status.py` from the checklist in `docs/`. The checklist uses five "
            "template families (core 1–15, security 16–30, observability 31–40, verification 41–60, "
            "docs/package 61–70) and each is judged against its own template.", "",
            "Legend: `[x]` evidenced (evidence cited) · `[ ]` open (gap or named exception cited) · "
            "`[-]` not applicable (reason cited).", "",
            f"**Totals (2,100 items):** {stats[X]} evidenced · {stats[O]} open · {stats[NA]} not applicable.  ",
            f"**Exit gate:** {exit_gate.get('verdict', 'not run')} — open blockers: "
            f"{', '.join(exit_gate.get('open_blockers', [])) or 'none'}.", "",
            "| # | Component | Family | evidenced | open | n/a |", "|---|---|---|---|---|---|"]
    for k in sorted(per):
        head.append(f"| {k} | {names[str(k)]} | {fam_name[k]} | {per[k][X]} | {per[k][O]} | {per[k][NA]} |")
    head += ["", "---", ""]
    body = "\n".join(out).replace("# GAP-01 Edge Node Supervisor — Professional Missing-Components Checklist",
                                  "# Annotated checklist", 1)
    (PKG / "CHECKLIST_STATUS.md").write_text("\n".join(head) + body + "\n")
    (PKG / "CHECKLIST_STATUS.json").write_text(json.dumps(
        {"totals": {"evidenced": stats[X], "open": stats[O], "not_applicable": stats[NA]},
         "components": {k: {"evidenced": v[X], "open": v[O], "not_applicable": v[NA]} for k, v in per.items()},
         "items": rows, "exit_gate": exit_gate.get("verdict")}, indent=1) + "\n")
    print({"evidenced": stats[X], "open": stats[O], "not_applicable": stats[NA]})


if __name__ == "__main__":
    main()
