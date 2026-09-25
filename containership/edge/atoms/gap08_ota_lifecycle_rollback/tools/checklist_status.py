"""Execute the GAP-08 professional checklist against this package: every checkbox gets a status + evidence.

    python tools/checklist_status.py            # writes docs/CHECKLIST_STATUS.{json,md}
    python tools/checklist_status.py --check    # also verifies every referenced evidence path exists

Statuses (deliberately conservative — nothing is marked DONE that this package cannot itself prove):
  DONE      implemented in this package and exercised by its tests on the build host
  DONE-SIM  implemented and exercised, but only against in-package simulations/doubles (no real sibling
            service, hardware, fleet or production-representative environment)
  PARTIAL   some of the item exists; the gap is stated
  DOC       written down (design/runbook/policy) but not yet independently reviewed or drilled
  OPEN      not done here; needs people, hardware, real services, long runs or organisational action
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SRC = PKG / "docs" / "GAP08_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md"

# ---- module / test per section ------------------------------------------------------------------------
MOD = {1: "store.py", 2: "lease.py", 3: "conflicts.py", 4: "health.py", 5: "audit_sink.py", 6: "artifact.py",
       7: "installer.py", 8: "executor.py", 9: "topology.py", 10: "freeze.py", 11: "authz.py", 12: "identity.py",
       13: "deferred.py", 14: "transport.py", 15: "dependencies.py", 16: "retry.py", 17: "admission.py",
       18: "windows.py", 19: "distribution.py", 20: "schema.py", 21: "errors.py", 22: "telemetry.py",
       23: "explain.py", 24: "store.py", 25: "compat.py", 26: "config.py", 27: "secrets_boundary.py",
       28: "controller.py", 29: "controller.py", 30: "controller.py", 31: "tests/test_property_fuzz.py",
       32: "tests/test_chaos.py", 33: "harness.py", 34: "tools/benchmark.py", 35: "tools/soak.py",
       36: "tests/test_installer_powerloss.py", 37: "tools/release_evidence.py", 38: "docs/SECURITY_AND_VULN.md",
       39: "docs/ADR-0001-control-plane.md", 40: "docs/OWNERS.md"}
TEST = {1: "tests/test_store_lease.py", 2: "tests/test_store_lease.py", 3: "tests/test_dod_drills.py",
        4: "tests/test_components.py", 5: "tests/test_dod_drills.py", 6: "tests/test_dod_drills.py",
        7: "tests/test_installer_powerloss.py", 8: "tests/test_controller.py", 9: "tests/test_controller.py",
        10: "tests/test_controller.py", 11: "tests/test_dod_drills.py", 12: "tests/test_components.py",
        13: "tests/test_controller.py", 14: "tests/test_controller.py", 15: "tests/test_dod_drills.py",
        16: "tests/test_components.py", 17: "tests/test_components.py", 18: "tests/test_components.py",
        19: "tests/test_components.py", 20: "tests/test_components.py", 21: "tests/test_components.py",
        22: "tests/test_controller.py", 23: "tests/test_controller.py", 24: "tests/test_store_lease.py",
        25: "tests/test_components.py", 26: "tests/test_components.py", 27: "tests/test_components.py",
        28: "tests/test_controller.py", 29: "tests/test_controller.py", 30: "tests/test_controller.py",
        31: "tests/test_property_fuzz.py", 32: "tests/test_chaos.py", 33: "tests/test_chaos.py",
        34: "tools/benchmark.py", 35: "tools/soak.py", 36: "tests/test_installer_powerloss.py",
        37: "tools/release_evidence.py", 38: "docs/SECURITY_AND_VULN.md", 39: "docs/ADR-0001-control-plane.md",
        40: "docs/OWNERS.md"}
CODE_SECTIONS = set(range(1, 31))

# ---- the 28 repeated engineering items + 3 release-gate items ------------------------------------------
def template(n: int) -> list[tuple[str, str, str]]:
    m, t = MOD[n], TEST[n]
    code = n in CODE_SECTIONS
    return [
        ("DONE", f"{m} module docstring; docs/ARCHITECTURE.md §1", ""),
        ("DONE", "docs/ARCHITECTURE.md §2-4 (sequence diagrams)", ""),
        ("DONE" if code else "PARTIAL", "schemas/INDEX.json; dataclasses in " + m,
         "" if code else "data model is a report/doc format, not a runtime schema"),
        ("DONE", "schemas/INDEX.json (ids + compatibility rules)", ""),
        ("DONE", "docs/ARCHITECTURE.md §5", ""),
        ("DONE" if code else "PARTIAL", f"{m}; {t}", "" if code else "guards live in the harness/tooling"),
        ("DONE", "docs/ARCHITECTURE.md §6", ""),
        ("DONE", "docs/ARCHITECTURE.md §7; store.py docstring", ""),
        ("DONE", "docs/ARCHITECTURE.md §8", ""),
        ("DONE", "retry.py; executor.py", ""),
        ("PARTIAL", "authz.py; identity.py; secrets_boundary.py; docs/THREAT_MODEL.md",
         "HMAC stand-in for asymmetric signatures; no mTLS/workload identity or encryption at rest in-package"),
        ("DOC", "docs/THREAT_MODEL.md", "author draft; independent security review not yet performed"),
        ("DONE", "dependencies.py; tests/test_dod_drills.py::Section15DependencyMatrix", ""),
        ("DONE", "errors.py; schemas/PK_ERROR_1.schema.json", ""),
        ("DONE-SIM", "telemetry.py (+ALERT_RULES)", "not yet wired to the real GAP-09 backend"),
        ("DONE", "secrets_boundary.py (store, sink, logs, explain)", ""),
        ("DONE" if n in (13, 16, 17, 19, 22) else "PARTIAL", "admission.py; telemetry.MAX_SERIES_PER_METRIC",
         "" if n in (13, 16, 17, 19, 22) else "limits exist; per-section saturation not independently measured"),
        ("DONE-SIM", "harness.py fault hooks; tests/test_chaos.py", ""),
        ("DONE" if code else "PARTIAL", t, ""),
        ("PARTIAL", "transport.SimNodeSupervisor, harness GAP-07/09 minting",
         "verified against executable doubles only; real staging services not available"),
        ("DONE-SIM" if n in (1, 2, 5, 8, 13, 14, 24, 28, 29, 30) else "PARTIAL",
         "tests/test_controller.py::FencingRecovery; tests/test_chaos.py", ""),
        ("DONE-SIM" if n in (1, 2, 3, 14, 28, 32) else "PARTIAL", "tests/test_chaos.py::Concurrency; tests/test_dod_drills.py",
         "" if n in (1, 2, 3, 14, 28, 32) else "race harness does not target this component specifically"),
        ("PARTIAL", "tools/benchmark.py", "build-host numbers only; production envelope not established"),
        ("DOC", "docs/RUNBOOKS.md", "not yet drilled by operators"),
        ("PARTIAL", "config.py", "signed/approved config exists; controller thresholds are still constructor-bound, not read from ConfigStore"),
        ("PARTIAL", "tools/ci.sh; tools/release_evidence.py",
         "no hosted CI or security scanner configured; gate scripts provided"),
        DOD[n],
        ("OPEN", "docs/OWNERS.md", "no named owner supplied"),
        ("DONE-SIM", "tests/test_chaos.py::ChaosCampaign", "simulated fleet; representative environment not available"),
        ("PARTIAL", "release/EVIDENCE_BUNDLE.json section_trace", "bundle is unsigned until a release key is supplied"),
        ("PARTIAL", "docs/CHECKLIST_STATUS.md residual risks", "owners/expiry dates cannot be set until OWNERS.md is filled"),
    ]


DOD = {
    1: ("DONE", "tests/test_store_lease.py::test_restart_continuity_byte_for_byte, ::test_two_controller_race_only_current_fence_advances", ""),
    2: ("DONE-SIM", "tests/test_controller.py::test_stale_controller_cannot_mutate; ::test_nodes_reject_stale_fence_commands", "partition simulated via lease expiry"),
    3: ("DONE-SIM", "tests/test_dod_drills.py::Section03OverlapSameInstant", ""),
    4: ("DONE", "tests/test_components.py::HealthEvidence", ""),
    5: ("DONE-SIM", "tests/test_dod_drills.py::Section05TamperDrill", "reference WORM file, not a real transparency log"),
    6: ("DONE-SIM", "tests/test_dod_drills.py::Section06OneByteMutation", ""),
    7: ("OPEN", "tests/test_installer_powerloss.py (filesystem simulation)", "hardware-in-the-loop power cuts not performed"),
    8: ("PARTIAL", "tests/test_controller.py::DeferredAndIdempotency", "drop/duplicate covered; arbitrary reordering covered only for install-after-rollback"),
    9: ("PARTIAL", "tests/test_controller.py::test_topology_blast_radius_denies_whole_domain", "no production-shadow; concurrent site failures not simulated"),
    10: ("PARTIAL", "tests/test_controller.py::test_freeze_blocks_forward…", "in-process freeze; distributed propagation bound not measured; no live drill"),
    11: ("DONE", "tests/test_dod_drills.py::Section11ScopedAuthorization", "environment scope enforced; site-level scope not modelled"),
    12: ("DONE", "tests/test_components.py::Identity::test_cross_node_replay_and_attestation", ""),
    13: ("PARTIAL", "tests/test_controller.py::test_offline_node_deferred_then_retried_behind_gate; tools/soak.py", "no dedicated reconnect-storm-with-restart test for 'at most once concurrently'"),
    14: ("DONE-SIM", "tests/test_controller.py::test_lost_ack_and_duplicate_delivery_execute_once; tests/test_chaos.py", ""),
    15: ("DONE", "tests/test_dod_drills.py::Section15DependencyMatrix", ""),
    16: ("PARTIAL", "tests/test_components.py::RetryBreakerAdmission", "amplification factor not measured under fleet-wide failure"),
    17: ("PARTIAL", "tests/test_components.py::test_recovery_lane_not_starved", "responsiveness beyond limits not load-tested"),
    18: ("PARTIAL", "tests/test_components.py::Windows", "fixed UTC offsets by design; DST gap/fold handled by config, not tested"),
    19: ("PARTIAL", "tests/test_components.py::Distribution", "no network emulation of loss/latency"),
    20: ("PARTIAL", "tests/test_components.py::ErrorsAndSchemas", "no generated clients or N-1 fixture corpus yet"),
    21: ("PARTIAL", "tests/test_components.py::test_error_envelope", "codes asserted by exception type across suites, not every branch field-by-field"),
    22: ("OPEN", "telemetry.py; explain.py", "responder reconstruction drill not run"),
    23: ("OPEN", "explain.py", "operator usability drill not run"),
    24: ("PARTIAL", "tests/test_store_lease.py::test_backup_restore_verified; ChaosCampaign step 4", "scheduled isolated DR exercise not run"),
    25: ("PARTIAL", "tests/test_components.py::test_compat_matrix", "only python3.x/x86_64 cells exercised"),
    26: ("PARTIAL", "tests/test_components.py::test_config_provenance_and_rollback", "historical decision replay not implemented"),
    27: ("PARTIAL", "tests/test_components.py::test_secrets_boundary; Identity rotation", "no repository secret scanner; service-credential rotation drill not run"),
    28: ("DONE-SIM", "tests/test_controller.py::Cancellation", ""),
    29: ("DONE-SIM", "tests/test_controller.py::test_rollback_failure_quarantined_then_released_with_two_people", "reimage simulated"),
    30: ("DONE-SIM", "tests/test_controller.py::test_unknown_outcome_is_never_success; tools/soak.py", ""),
    31: ("PARTIAL", "tests/test_property_fuzz.py (GAP08_FUZZ_ITERS)", "no persisted regression corpus or scheduled extended fuzzing"),
    32: ("PARTIAL", "tests/test_chaos.py::Concurrency", "race harness found+fixed a real defect; no model checker"),
    33: ("DONE-SIM", "tests/test_chaos.py::ChaosCampaign", ""),
    34: ("PARTIAL", "tools/benchmark.py → release/benchmark.json", "no regression-detection lab"),
    35: ("PARTIAL", "tools/soak.py → release/soak.json", "short simulated-time soak only; days/weeks wall-clock soak not run"),
    36: ("OPEN", "tests/test_installer_powerloss.py", "no hardware certification matrix"),
    37: ("PARTIAL", "tools/release_evidence.py build/verify", "unsigned; independent clean-environment verification not performed"),
    38: ("PARTIAL", "release/SBOM.cdx.json; docs/SECURITY_AND_VULN.md", "tabletop exercise not run"),
    39: ("DOC", "docs/ADR-0001-control-plane.md", "status Proposed — not approved"),
    40: ("OPEN", "docs/OWNERS.md", "no owners named"),
}
SECTION_KIND_OVERRIDES = {  # sections whose template items don't apply as code
    40: {i: ("OPEN", "docs/OWNERS.md", "requires named people") for i in range(28)},
}

GLOBAL = [
    ("PARTIAL", "all P0 modules + tests", "implemented and evidenced in simulation; not peer-reviewed or run in production-representative env"),
    ("DONE", "health.py, artifact.py, store.py, audit_sink.py", "no caller booleans, local-only trust anchors or best-effort persistence on the production path"),
    ("DONE-SIM", "tests/test_chaos.py::ChaosCampaign", ""),
    ("DONE", "docs/ARCHITECTURE.md §5; audit events policy_admitted→dispatch_intent→dispatch_result→wave_gate", ""),
    ("DONE", "dependencies.py; tests/test_dod_drills.py::Section15DependencyMatrix", ""),
    ("DONE", "admission.py reserved recovery lane; audit buffering for rollback", ""),
    ("PARTIAL", "schemas/INDEX.json; errors.REGISTRY", "compatibility fixtures across versions not yet built"),
    ("DONE", "tools/release_evidence.py verify (file-digest binding)", ""),
]
SIBLING = {
    "GAP-07": ["DONE", "DONE", "DONE", "DONE", "DONE"],
    "GAP-09": ["DONE", "DONE", "DONE", "DONE", "PARTIAL"],
    "GAP-01": ["DONE-SIM", "DONE-SIM", "DONE-SIM", "OPEN", "DONE-SIM"],
    "GAP-15": ["PARTIAL", "PARTIAL", "OPEN", "DONE", "DONE"],
    "GAP-06": ["DONE-SIM", "DONE-SIM", "DONE-SIM", "DONE", "DONE"],
    "Topology": ["PARTIAL", "DONE", "DONE", "OPEN", "PARTIAL"],
}
SIBLING_NOTE = "contract defined in docs/INTEGRATION_CONTRACTS.md; verified against in-package doubles, not the real service"
FINAL = ["OPEN", "OPEN", "OPEN", "DONE-SIM", "PARTIAL", "OPEN", "OPEN", "OPEN"]


def parse():
    items, section, n = [], "global", None
    for line in SRC.read_text().splitlines():
        m = re.match(r"^##\s+(\d+)\.\s+(.*)", line)
        if m:
            n, section = int(m.group(1)), m.group(2).strip()
            idx = 0
            continue
        m2 = re.match(r"^##\s+(GAP-\d+|Topology)", line)
        if m2:
            n, section, idx = None, m2.group(1), 0
            continue
        if line.startswith("# Final GAP-08"):
            n, section, idx = None, "final", 0
            continue
        if line.startswith("- [ ]"):
            items.append({"section_no": n, "section": section, "text": line[6:].strip()})
    return items


def assign(items):
    counters: Counter = Counter()
    for it in items:
        key = it["section_no"] or it["section"]
        i = counters[key]
        counters[key] += 1
        it["index"] = i + 1
        if it["section_no"]:
            n = it["section_no"]
            st, ev, note = SECTION_KIND_OVERRIDES.get(n, {}).get(i) or template(n)[i]
        elif it["section"] == "global":
            st, ev, note = GLOBAL[i]
        elif it["section"] == "final":
            st, ev, note = FINAL[i], "docs/CHECKLIST_STATUS.md", "requires review/sign-off by named owners"
            if i == 3:
                ev, note = "tests/test_chaos.py::ChaosCampaign", "simulated single campaign"
        else:
            st, ev, note = SIBLING[it["section"]][i], "docs/INTEGRATION_CONTRACTS.md", SIBLING_NOTE
        it.update(status=st, evidence=ev, note=note)
    return items


def evidence_paths(ev: str):
    for part in re.split(r"[;,]", ev):
        tok = part.strip().split("::")[0].split(" ")[0]
        if tok.endswith((".py", ".md", ".json", ".sh")) and "/" in tok or tok.endswith(".py") and "/" not in tok:
            yield tok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    items = assign(parse())
    total = Counter(i["status"] for i in items)
    per = {}
    for it in items:
        k = it["section_no"] or it["section"]
        per.setdefault(k, Counter())[it["status"]] += 1
    out = {"schema": "PK_CHECKLIST_STATUS/1", "source": SRC.name, "items": len(items), "totals": dict(total),
           "entries": items}
    (PKG / "docs" / "CHECKLIST_STATUS.json").write_text(json.dumps(out, indent=1) + "\n")
    order = ["DONE", "DONE-SIM", "PARTIAL", "DOC", "OPEN"]
    md = ["# GAP-08 checklist execution status (v4.3.0)", "",
          f"Every one of the **{len(items)}** checkboxes in `{SRC.name}` has a status, evidence pointer and gap note in "
          "`CHECKLIST_STATUS.json` (generated by `tools/checklist_status.py`). Statuses are conservative: "
          "**DONE** = implemented and tested here; **DONE-SIM** = tested only against in-package simulations; "
          "**PARTIAL**/**DOC** = gap stated; **OPEN** = needs people, hardware, real services or long runs.", "",
          "| Status | Items |", "|---|---|"] + [f"| {s} | {total.get(s, 0)} |" for s in order] + [
          "", "**Production readiness: NOT READY.** The final sign-off items are open: no named owners, no "
          "independent security/operations review, no production-representative environment, no hardware "
          "power-loss certification, unsigned evidence bundle.", "", "## Per section", "",
          "| Section | " + " | ".join(order) + " |", "|---|" + "---|" * len(order)]
    for k, c in per.items():
        label = f"§{k}" if isinstance(k, int) else k
        name = next(i["section"] for i in items if (i["section_no"] or i["section"]) == k)
        md.append(f"| {label} {name if isinstance(k, int) else ''} | " + " | ".join(str(c.get(s, 0)) for s in order) + " |")
    md += ["", "## Definition-of-Done status per component", "", "| § | Status | Evidence | Gap |", "|---|---|---|---|"]
    for n in range(1, 41):
        st, ev, note = DOD[n]
        md.append(f"| {n} | {st} | {ev} | {note} |")
    md += ["", "## Open items that block production (owner action required)", "",
           "1. Name every owner in `docs/OWNERS.md`; approve ADR-0001; set waiver expiries.",
           "2. Replace the HMAC stand-in with asymmetric keys held per trust domain (HSM/KMS); add mTLS/workload identity.",
           "3. Implement `StateStore` on the chosen GAP-05 backend (linearizable CAS + fence floor) and a distributed lease service; rerun the whole suite against them.",
           "4. Verify every sibling contract against real GAP-01/06/07/09/15 and topology services in staging.",
           "5. Hardware-in-the-loop power-loss certification per supported board/storage/bootloader.",
           "6. Days/weeks wall-clock soak and fleet-scale benchmarks on production-class control-plane hardware.",
           "7. Independent security review of `THREAT_MODEL.md`; operator drills of `RUNBOOKS.md` (freeze, DR, quarantine, explain).",
           "8. Wire controller thresholds to `ConfigStore` so gate/blast-radius/lease settings come from signed configuration.",
           "9. Hosted CI running `tools/ci.sh` with a secret scanner and dependency/runtime-image scanner; sign the evidence bundle.",
           "", "## Residual risks", "",
           "| Risk | Compensating control | Owner | Expiry |", "|---|---|---|---|",
           "| Symmetric HMAC keys in reference build | trust-domain separation documented; swap point `sign_envelope/verify_envelope` | unassigned | before production |",
           "| In-memory replay caches reset on restart | freshness windows ≤ 600 s | unassigned | before production |",
           "| Single-host reference store/lease | executable contract + tests for GAP-05 | unassigned | before production |",
           "| No encryption at rest in reference store | file mode 0600; no secrets persisted (enforced) | unassigned | before production |"]
    (PKG / "docs" / "CHECKLIST_STATUS.md").write_text("\n".join(md) + "\n")
    print(f"{len(items)} checklist items: " + ", ".join(f"{s}={total.get(s, 0)}" for s in order))
    if a.check:
        missing = sorted({p for it in items for p in evidence_paths(it["evidence"]) if not (PKG / p).exists()
                          and not p.startswith("release/")})
        if missing:
            print("missing evidence paths:", missing)
            return 1
        if len(items) != 1286:
            print("unexpected checklist item count", len(items))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
