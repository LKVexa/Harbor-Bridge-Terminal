"""Execute the MC-001..MC-074 closure checklist against the candidate and record honest per-item status.

Inputs: the issued checklist (path argument; kept unmodified), governance/CI_RESULT.json.
Per item, a deterministic rule assigns exactly one status:
  VERIFIED_LOCAL  - implemented here AND the component's evidence tests passed in this CI run
  PARTIAL         - implemented for a narrower scope than the item asks (scope named)
  BLOCKED:<id>    - needs something that does not exist in this delivery (governance/BLOCKERS.json)
  OPEN            - not attempted
The rule that fired is stored with the item.  No item is ever Production Accepted: the
highest lifecycle any component reaches is 'Verified' (local), per the checklist's own convention.
"""
from __future__ import annotations

import json
import re
import sys

from _common import PKG, write_json

# component -> (lifecycle, evidence test ids/tools, scope note, extra blockers)
T = "test_production."
C: dict[str, tuple[str, list[str], str, list[str]]] = {
    "GLOBAL": ("Verified", [T + "ReconcilerTest", T + "SecurityTest", T + "ApiTest"], "invariants enforced in code and tests", []),
    "MC-001": ("Implemented", ["tools/pk_core_gate.py", "tools/build.py"], "pin/lock + fail-closed gate; pk_core itself absent", ["B-PKCORE"]),
    "MC-002": ("Designed", ["governance/OWNERS.json"], "owner registry shape only", ["B-OWNER"]),
    "MC-003": ("Verified", ["tools/rtm.py"], "30 SHALL requirements", []),
    "MC-004": ("Verified", ["tools/rtm.py"], "generated RTM, dangling-link check", []),
    "MC-005": ("Verified", [T + "CloudHypervisorAdapterTest"], "Cloud Hypervisor REST adapter vs scripted peer", ["B-LIVE-HV"]),
    "MC-006": ("Verified", [T + "ObservationTest"], "signed guest cpulist observation", ["B-LIVE-HV"]),
    "MC-007": ("Implemented", ["governance/SPEC_PIN.json"], "API pinned; ACPI revision unpinned", ["B-OWNER"]),
    "MC-008": ("Implemented", ["governance/COMPATIBILITY_MATRIX.json"], "matrix drafted; no live row certified", ["B-LIVE-HV"]),
    "MC-009": ("Verified", [T + "ApiTest"], "stdlib HTTP boundary; TLS in front not bundled", []),
    "MC-010": ("Verified", [T + "SecurityTest.test_authn_accept_replay_forge_skew"], "reference HMAC authn", ["B-KEYS"]),
    "MC-011": ("Verified", [T + "SecurityTest.test_authz_least_privilege_and_cross_tenant"], "capability policy", []),
    "MC-012": ("Verified", [T + "SecurityTest.test_quota_tenant_site_fleet_fairness"], "in-process quota; not fleet-shared", ["B-REPLICATED-STORE"]),
    "MC-013": ("Verified", [T + "ApiTest.test_error_mapping", T + "ApiTest.test_overload_sheds"], "deadline/backpressure; cancel = no side effect only before call", []),
    "MC-014": ("Implemented", [T + "ApiTest.test_error_mapping"], "protocol negotiation; only v1 exists, no mixed-version run", []),
    "MC-015": ("Verified", [T + "ConfigTest"], "declarative JSON config", []),
    "MC-016": ("Verified", [T + "ConfigTest.test_activate_provenance_rollback"], "provenance JSONL", []),
    "MC-017": ("Verified", [T + "ConfigTest.test_activate_provenance_rollback"], "atomic pointer swap", []),
    "MC-018": ("Verified", [T + "ConfigTest.test_activate_provenance_rollback", T + "StoreTest.test_backup_restore_marks_needs_reconcile"], "config rollback; state never rolled back", []),
    "MC-019": ("Verified", [T + "StoreTest"], "single-host durable CAS store", ["B-REPLICATED-STORE"]),
    "MC-020": ("Verified", [T + "ReconcilerTest.test_durable_idempotency_across_restart"], "durable idempotency", []),
    "MC-021": ("Verified", [T + "StoreTest.test_lease_exclusive_and_fence_monotonic", T + "ReconcilerTest.test_two_replicas_one_lease"], "lease + fence on shared single-host store", ["B-REPLICATED-STORE"]),
    "MC-022": ("Verified", [T + "ReconcilerTest.test_retry_exhaustion_fails_closed", T + "ResilienceTelemetryAuditTest.test_backoff_bounded_jitter"], "", []),
    "MC-023": ("Verified", [T + "ResilienceTelemetryAuditTest.test_budget_and_breaker", T + "ApiTest.test_overload_sheds"], "", []),
    "MC-024": ("Verified", [T + "ReconcilerTest.test_crash_between_accept_and_reconcile_recovers", T + "ReconcilerTest.test_two_replicas_one_lease"], "failover via lease expiry on one host", ["B-REPLICATED-STORE"]),
    "MC-025": ("Verified", [T + "ReconcilerTest.test_policy_quota_degraded_and_limits"], "", []),
    "MC-026": ("Verified", [T + "ReconcilerTest.test_crash_between_accept_and_reconcile_recovers"], "", []),
    "MC-027": ("Verified", [T + "ApiTest.test_quarantine_explain_health_metrics"], "per-VM freeze endpoint; fleet-wide policy not bundled", []),
    "MC-028": ("Verified", [T + "ObservationTest.test_stall_thresholds"], "thresholds PROPOSED", ["B-APPROVAL"]),
    "MC-029": ("Implemented", [T + "ReconcilerTest.test_timeout_after_action_no_double_hotadd"], "partition modelled as adapter/transport loss only", ["B-FLEET"]),
    "MC-030": ("Verified", [T + "ResilienceTelemetryAuditTest.test_precedence"], "", []),
    "MC-031": ("Implemented", [T + "SecurityTest.test_secret_rotation_and_redacted_repr"], "env secret source + rotation; no KMS", ["B-KEYS"]),
    "MC-032": ("Implemented", ["tools/build.py"], "digests + manifest; unsigned", ["B-KEYS"]),
    "MC-033": ("Implemented", ["tools/build.py"], "CycloneDX SBOM generated; no attestation signature", ["B-KEYS"]),
    "MC-034": ("Verified", [T + "ResilienceTelemetryAuditTest.test_audit_chain_tamper"], "local chain; no external anchor", []),
    "MC-035": ("Verified", [T + "SecurityTest", T + "ApiTest.test_hostile_payloads_fuzz"], "", []),
    "MC-036": ("Verified", [T + "ApiTest.test_hostile_payloads_fuzz", T + "ReconcilerTest.test_property_random_sequences_invariants"], "", []),
    "MC-037": ("Implemented", [T + "StoreTest.test_multiprocess_cas_no_lost_update", T + "ReconcilerTest.test_concurrent_submits_single_commit"], "multi-process single host; no cross-host", ["B-FLEET"]),
    "MC-038": ("Verified", [T + "ReconcilerTest"], "emulator faults", ["B-LIVE-HV"]),
    "MC-039": ("Implemented", [T + "ApiTest.test_full_path_and_trace_propagation"], "adjacent layers in-process", ["B-LIVE-HV"]),
    "MC-040": ("Implemented", [T + "CloudHypervisorAdapterTest"], "contract vs donor OpenAPI shape, not live API", ["B-LIVE-HV"]),
    "MC-041": ("Verified", ["tools/perf.py"], "local harness", []),
    "MC-042": ("Designed", ["governance/THRESHOLDS.json"], "PROPOSED values", ["B-APPROVAL"]),
    "MC-043": ("Implemented", ["tools/perf.py"], "steady/burst/fault local", ["B-FLEET"]),
    "MC-044": ("Implemented", ["tools/perf.py"], "per-VM state bytes + latency; no tenant workload", ["B-FLEET"]),
    "MC-045": ("Designed", ["docs/PERFORMANCE.md"], "analysis of local path", ["B-LIVE-HV"]),
    "MC-046": ("Verified", [T + "ResilienceTelemetryAuditTest.test_admission"], "bounded queue/in-flight/journal/idempotency", []),
    "MC-047": ("Not Started", [], "", ["B-HW"]),
    "MC-048": ("Verified", [T + "ResilienceTelemetryAuditTest.test_forecast"], "", []),
    "MC-049": ("Implemented", ["tools/perf.py"], "gate vs PROPOSED limits", ["B-APPROVAL"]),
    "MC-050": ("Verified", [T + "ApiTest.test_quarantine_explain_health_metrics"], "", []),
    "MC-051": ("Verified", [T + "ApiTest.test_quarantine_explain_health_metrics"], "Prometheus text", []),
    "MC-052": ("Verified", [T + "ResilienceTelemetryAuditTest.test_redaction_and_bounded_labels"], "", []),
    "MC-053": ("Verified", [T + "ApiTest.test_full_path_and_trace_propagation"], "", []),
    "MC-054": ("Verified", [T + "ResilienceTelemetryAuditTest.test_redaction_and_bounded_labels"], "", []),
    "MC-055": ("Verified", [T + "ApiTest.test_quarantine_explain_health_metrics"], "", []),
    "MC-056": ("Implemented", [T + "ApiTest.test_full_path_and_trace_propagation"], "release+config digest on journal/explain; no infra graph", ["B-DEPLOY"]),
    "MC-057": ("Designed", ["production/telemetry.py"], "TELEMETRY_POLICY PROPOSED", ["B-APPROVAL"]),
    "MC-058": ("Implemented", ["docs/ALERT_RULES.yml"], "alert rules; no dashboard backend", ["B-DEPLOY"]),
    "MC-059": ("Not Started", [], "", ["B-FLEET"]),
    "MC-060": ("Not Started", [], "", ["B-FLEET"]),
    "MC-061": ("Implemented", ["tools/pk_core_gate.py"], "gate fails closed", ["B-PKCORE"]),
    "MC-062": ("Designed", ["docs/OPERATIONS_PROGRAM.md"], "DRAFT", ["B-OWNER"]),
    "MC-063": ("Implemented", ["tools/runbook.py"], "canary evaluator; no deploy system", ["B-DEPLOY"]),
    "MC-064": ("Designed", ["docs/SUPPLY_CHAIN.md"], "DRAFT", ["B-OWNER"]),
    "MC-065": ("Verified", [T + "StoreTest.test_backup_restore_marks_needs_reconcile"], "", []),
    "MC-066": ("Implemented", ["tools/runbook.py"], "day0/1/2 local with evidence capture", ["B-DEPLOY"]),
    "MC-067": ("Designed", ["docs/OPERATIONS_PROGRAM.md"], "DRAFT", ["B-OWNER"]),
    "MC-068": ("Designed", ["docs/OPERATIONS_PROGRAM.md"], "DRAFT", ["B-OWNER"]),
    "MC-069": ("Implemented", ["governance/WAIVERS.json"], "registry schema, empty", ["B-OWNER"]),
    "MC-070": ("Implemented", ["tools/exit_gate.py"], "gate evaluates to NO_GO", ["B-OWNER"]),
    "MC-071": ("Verified", ["pyproject.toml", "tools/build.py"], "", []),
    "MC-072": ("Verified", ["tools/ci.py", ".github/workflows/ci.yml"], "", []),
    "MC-073": ("Verified", ["tools/ci.py"], "stdlib AST lint policy (no mypy installed)", []),
    "MC-074": ("Designed", ["governance/LICENSE_REQUIRED.md"], "no licence invented", ["B-LICENSE"]),
}

RULES = [
    ("B-OWNER", r"\b(owner|on-call|oncall|sign-off|signoff|approv|accountable|rights holder|paging|escalat|support hours)"),
    ("B-PKCORE", r"pk_core"),
    ("B-KEYS", r"\b(sign(ed|ing|ature)?|attest|kms|idp|hsm|mtls|certificate)\b"),
    ("B-LICENSE", r"\b(licen[sc]e|spdx|copyright)"),
    ("B-HW", r"\b(power|thermal|edge node)"),
    ("B-FLEET", r"\b(fleet|soak|game day|canary|staged rollout|disaster|multi-region|scale test|certification environment)"),
    ("B-LIVE-HV", r"\b(real (api|hypervisor|guest|boundary|supported)|live hypervisor|supported hypervisor|every supported|all supported|production path|production environment)"),
    ("B-REPLICATED-STORE", r"\b(replicas?|replicated|multi-node|cross-host|quorum|regions?|distributed)\b"),
    ("B-DEPLOY", r"\b(dashboard|deploy(ment)? system|pager|infrastructure graph)"),
]

# Items reviewed by hand and judged fully met by code + a passing test in this delivery.
# Everything else in an implemented component defaults to PARTIAL (never promoted silently).
VERIFIED_PATTERNS = [re.compile(x) for x in (
    r"^CPU changes through INV-34 are monotonic", r"^`desired_vcpus` and independently observed",
    r"^New desired targets never exceed", r"^Unsupported hypervisor/guest hot-plug capability",
    r"^Tenant/workload identity, authorization, quota",
    r"^Define an adapter interface such as", r"^Query current hypervisor CPU topology",
    r"^Use an operation/fencing token", r"^Map already-at-target into idempotent",
    r"^Enforce backend timeouts and cancellation", r"^Capture backend operation IDs",
    r"^Map every remote/backend failure", r"^Validate every boundary input before side effects",
    r"^Inject dependency errors and unknown outcomes",
    r"^Emit observations with VM identity", r"^Authenticate observation producers",
    r"^Distinguish presented CPUs from guest-online", r"^Handle delayed/partial onlining",
    r"^Detect impossible observations", r"^Define observation freshness TTL",
    r"^Implement endpoints/methods for submit", r"^Return stable machine-readable error code",
    r"^Add transport-level fuzzing", r"^Carry deadline/cancellation and request-id",
    r"^Bind authenticated identity to tenant", r"^Define capabilities separately",
    r"^Evaluate authorization immediately before",
    r"^Atomically create/check idempotency record", r"^Reject key reuse with a different target",
    r"^Bound storage growth", r"^Use CAS on generation", r"^Use atomic compare-and-swap",
    r"^Run reconciliation from durable", r"^Re-observe current backend state before replaying",
    r"^Persist next-attempt time", r"^Use exponential backoff with full",
    r"^Use half-open probes", r"^Keep desired/observed divergence visible",
    r"^Stop accepting new expansions if", r"^Do not hot-unplug already online CPUs",
    r"^Create integrity-verification tooling", r"^Redact credentials",
    r"^Assert no hot-unplug, no false convergence", r"^Separate liveness from readiness",
    r"^Export request counters by outcome", r"^Do not log raw credentials",
    r"^Choose trace context standard", r"^Make explain generation read-only",
    r"^Record previous configuration digest", r"^Validate the entire candidate configuration",
    r"^Add automated checks that referenced files/tests exist", r"^Generate the RTM artifact during CI",
    r"^Add `pyproject.toml`", r"^Support deterministic clean-room rebuild",
    r"^Bound in-memory caches", r"^Account for already accepted-but-not-yet-observed",
    r"^Emit raw results in machine-readable format",
)]

DOD_PARTIAL = ("The RTM links", "Machine-readable test/gate results", "Documentation/runbooks")


def parse(md: str):
    comps, cur, section = [], None, None
    for line in md.splitlines():
        m = re.match(r"^## (MC-\d{3}) — (.*)", line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2), "items": []}
            comps.append(cur)
            continue
        if line.startswith("## Non-negotiable global invariants"):
            cur = {"id": "GLOBAL", "title": "Non-negotiable global invariants", "items": []}
            comps.append(cur)
            continue
        if line.startswith("# Final integrated closure gate"):
            cur = {"id": "FINAL", "title": "Final integrated closure gate", "items": []}
            comps.append(cur)
        if line.startswith("### "):
            section = line[4:].strip()
        m = re.match(r"^- \[ \] (.*)", line)
        if m and cur is not None:
            cur["items"].append({"section": section, "text": m.group(1)})
    return comps


def evidence_ok(evidence: list[str], ci: dict) -> bool:
    passed = set(ci.get("tests_passed", []))
    for e in evidence:
        if e.startswith("test_"):
            if not any(p == e or p.startswith(e + ".") for p in passed):
                return False
        elif e.startswith("tools/"):
            if ci.get("tools", {}).get(e) not in ("PASS", "EXPECTED_FAIL_CLOSED"):
                return False
        elif not (PKG / e).exists():
            return False
    return bool(evidence)


def classify(comp_id: str, item: dict, ci: dict) -> tuple[str, str]:
    life, ev, scope, blockers = C.get(comp_id, ("Not Started", [], "", []))
    text = item["text"]
    if comp_id == "FINAL":
        return "BLOCKED:B-FLEET", "integrated certification requires every component accepted plus a certification environment"
    if item["section"] and item["section"].startswith("Definition of Done"):
        if text.startswith(DOD_PARTIAL) and evidence_ok(ev, ci):
            return "PARTIAL", "local evidence exists; release artifact unsigned and no deployment"
        return "BLOCKED:B-OWNER", "DoD needs identified owner / exit-gate acceptance"
    for bid, rx in RULES:
        if re.search(rx, text, re.I):
            return f"BLOCKED:{bid}", f"rule {bid} matched /{rx}/"
    if life == "Not Started" or not ev:
        return f"BLOCKED:{blockers[0]}" if blockers else "OPEN", "component not started"
    if not evidence_ok(ev, ci):
        return "OPEN", "evidence missing or failed in this CI run"
    if life in ("Verified", "Implemented") and any(p.search(text) for p in VERIFIED_PATTERNS):
        return "VERIFIED_LOCAL", "hand-mapped as fully met; evidence passed: " + ", ".join(ev)
    return "PARTIAL", f"implemented for narrower scope: {scope}" + (f"; open: {', '.join(blockers)}" if blockers else "")


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else str(PKG / "docs/MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md")
    comps = parse(open(src, encoding="utf-8").read())
    ci = json.loads((PKG / "governance/CI_RESULT.json").read_text())
    totals, out = {}, []
    for c in comps:
        life, ev, scope, bl = C.get(c["id"], ("n/a", [], "", []))
        items = []
        for it in c["items"]:
            st, why = classify(c["id"], it, ci)
            totals[st.split(":")[0]] = totals.get(st.split(":")[0], 0) + 1
            items.append({**it, "status": st, "rule": why})
        out.append({"id": c["id"], "title": c["title"], "lifecycle": life if c["id"] != "FINAL" else "Not Started",
                    "evidence": ev, "scope": scope, "blockers": bl, "items": items})
    result = {"schema": "INV34_CHECKLIST_STATUS/1", "source": "MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md",
              "ci_run": ci.get("run_id"), "components": len([c for c in out if c["id"].startswith("MC-")]),
              "items": sum(len(c["items"]) for c in out), "totals": totals,
              "lifecycle_counts": {k: sum(1 for c in out if c["id"].startswith("MC-") and c["lifecycle"] == k) for k in
                                   ("Not Started", "Designed", "Implemented", "Verified", "Evidence Ready", "Production Accepted")},
              "production_decision": "NO_GO", "detail": out}
    write_json("governance/CHECKLIST_STATUS.json", result)
    md = ["# INV-34 v5.1.0 — checklist execution status (generated)", "",
          f"CI run `{ci.get('run_id')}` · {result['items']} items over {result['components']} components + final gate",
          "", "| Status | Items |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(totals.items())]
    md += ["", "| Component lifecycle | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in result["lifecycle_counts"].items()]
    md += ["", "**Production decision: NO_GO.** No component is Evidence Ready or Production Accepted.", "",
           "| MC | Lifecycle | Scope | Blockers | Verified / Partial / Blocked / Open |", "|---|---|---|---|---|"]
    for c in out:
        n = lambda s: sum(1 for i in c["items"] if i["status"].startswith(s))
        md.append(f"| {c['id']} | {c['lifecycle']} | {c['scope']} | {', '.join(c['blockers'])} | "
                  f"{n('VERIFIED')} / {n('PARTIAL')} / {n('BLOCKED')} / {n('OPEN')} |")
    (PKG / "governance/CHECKLIST_STATUS.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"items": result["items"], "totals": totals, "lifecycle": result["lifecycle_counts"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
