"""Source of truth for per-finding remediation status (MC-001..MC-056).  Writes REMEDIATION_STATUS.json.

Statuses:
  IMPLEMENTED       code/artifact + automated tests in this archive; human sign-off still needed per checklist V1
  PENDING_APPROVAL  artifact written; closes only when the named human approval is recorded
  PARTIAL           in-archive part done; named remainder depends on something outside the archive
  BLOCKED           cannot be done from this archive; needs an owner decision or an external input
No item is reported COMPLETE: the checklist's completion semantics require reviewer records and a
release-evidence link that only the owner can supply.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

S = {
 "MC-001": ("PENDING_APPROVAL", ["OWNERS.yaml", ".github/CODEOWNERS", "docs/RACI.md", "docs/ESCALATION.md", "telemetry.py"],
            "Role slots, RACI, escalation, emergency authority and owner-in-health defined; no named principals exist - owner must fill OWNERS.yaml from the identity/on-call system (audit fails release while unresolved)."),
 "MC-002": ("PENDING_APPROVAL", ["docs/adr/ADR-0001-runtime-technology.md"], "ADR written as Proposed; needs Architecture Board approval record."),
 "MC-003": ("IMPLEMENTED", ["docs/REQUIREMENTS.md"], "19 SHALL requirements with site classes, implementation and tests."),
 "MC-004": ("PARTIAL", ["docs/NFR.md", "PERF_BUDGET.json"], "NFRs specified; power (NFR-PWR-01) and fleet availability need target hardware/fleet telemetry."),
 "MC-005": ("IMPLEMENTED", ["envelope.py", "docs/SEMANTICS.md"], ""),
 "MC-006": ("IMPLEMENTED", ["lifecycle.py", "docs/SEMANTICS.md"], ""),
 "MC-007": ("PENDING_APPROVAL", ["docs/COMPATIBILITY.md", "negotiation.py"], "Policy written and enforced in negotiation; needs owner/board approval."),
 "MC-008": ("IMPLEMENTED", ["resilience.py", "docs/LIMITS.md"], "Per-tenant state byte quota declared but not enforced (needs adapter accounting)."),
 "MC-009": ("IMPLEMENTED", ["durability.py", "plane.py", "docs/SEMANTICS.md"], ""),
 "MC-010": ("IMPLEMENTED", ["config.py", "durability.py", "docs/SEMANTICS.md"], ""),
 "MC-011": ("IMPLEMENTED", ["TRACEABILITY.json", "tools/traceability.py"], "Generated 100-item matrix; release revision field is filled by release_evidence."),
 "MC-012": ("IMPLEMENTED", ["schemas/", "wit/pk-runtime.wit", "wire.py"], "WIT not compiled with wit-bindgen here (toolchain unpinned)."),
 "MC-013": ("IMPLEMENTED", ["tokens.py", "plane.py"], ""),
 "MC-014": ("IMPLEMENTED", ["resilience.py", "docs/SEMANTICS.md"], ""),
 "MC-015": ("IMPLEMENTED", ["envelope.py", "schemas/error-envelope.v1.json"], ""),
 "MC-016": ("IMPLEMENTED", ["negotiation.py", "schemas/hello.v1.json"], ""),
 "MC-017": ("IMPLEMENTED", ["resilience.py", "docs/LIMITS.md"], ""),
 "MC-018": ("IMPLEMENTED", ["fixtures/conformance/core.v1.json", "wire.py"], ""),
 "MC-019": ("BLOCKED", ["docs/INTEGRATION.md"], "Contracts documented; PLN-02/INV-49/PLN-04/PLN-06/PLN-07 are not packaged or pinned, so no end-to-end suite can run."),
 "MC-020": ("PARTIAL", ["DEPENDENCIES.lock.json"], "Manifest exists; wasmCloud/wRPC/Wadm/adjacent planes have no versions to pin until ADR-0001 is approved."),
 "MC-021": ("IMPLEMENTED", ["config.py", "schemas/config.v1.json"], ""),
 "MC-022": ("IMPLEMENTED", ["config.py"], ""),
 "MC-023": ("IMPLEMENTED", ["config.py"], ""),
 "MC-024": ("IMPLEMENTED", ["config.py", "docs/operations/RUNBOOKS.md"], ""),
 "MC-025": ("IMPLEMENTED", ["config.py", "telemetry.py", "audit_log.py"], ""),
 "MC-026": ("IMPLEMENTED", ["pyproject.toml", "tools/bootstrap.sh", "DEPENDENCIES.lock.json"], ""),
 "MC-027": ("PENDING_APPROVAL", ["docs/THREAT_MODEL.md"], "Needs security_contact review record."),
 "MC-028": ("BLOCKED", ["docs/INTEGRATION.md", "plane.py"], "Adapter quarantine added; process/Wasm/microVM isolation belongs to PLN-04 which is not in the archive."),
 "MC-029": ("BLOCKED", ["tokens.py", "docs/THREAT_MODEL.md"], "Workload tokens verified; node/peer/control-plane identity (mTLS/SPIFFE) needs PLN-07."),
 "MC-030": ("PARTIAL", ["artifacts.py"], "Digest allowlist + provenance + seal done; public-key signature (Sigstore) and SBOM attestation verification not integrated."),
 "MC-031": ("PARTIAL", ["runtime.py", "tokens.py"], "Data-plane tenant isolation tested on every capability; execution/memory/network/device/side-channel isolation is PLN-04."),
 "MC-032": ("PARTIAL", ["tokens.py"], "Token-key rotation/retirement implemented; transport and at-rest encryption and KMS contract need PLN-07."),
 "MC-033": ("IMPLEMENTED", ["tokens.py", "docs/THREAT_MODEL.md"], ""),
 "MC-034": ("IMPLEMENTED", ["audit_log.py", "plane.py"], "Chain head should be shipped to PLN-07 for truncation detection."),
 "MC-035": ("PARTIAL", ["tests/test_contract.py", "tests/test_remediation.py"], "Fuzz/injection/spoofing/replay/exhaustion covered; escape and side-channel campaigns need PLN-04 isolation."),
 "MC-036": ("IMPLEMENTED", ["telemetry.py", "docs/FAILURE_CATALOG.md"], ""),
 "MC-037": ("IMPLEMENTED", ["resilience.py"], ""),
 "MC-038": ("IMPLEMENTED", ["resilience.py", "plane.py"], ""),
 "MC-039": ("IMPLEMENTED", ["durability.py"], "Selection + fencing implemented; wiring to a real site inventory is PLN-04."),
 "MC-040": ("IMPLEMENTED", ["durability.py", "plane.py"], ""),
 "MC-041": ("IMPLEMENTED", ["durability.py"], ""),
 "MC-042": ("IMPLEMENTED", ["lifecycle.py", "plane.py", "docs/operations/RUNBOOKS.md"], ""),
 "MC-043": ("IMPLEMENTED", ["tests/test_faults.py"], "In-process fault injection; network-level injection needs a deployed topology."),
 "MC-044": ("PARTIAL", ["tools/bench.py", "PERF_BUDGET.json"], "Reproducible latency gate done; power, fleet capacity model and target-hardware budgets open."),
 "MC-045": ("IMPLEMENTED", ["telemetry.py", "plane.py"], "No HTTP server shipped; health()/exposition() are the endpoints' bodies."),
 "MC-046": ("PARTIAL", ["tests/test_contract.py"], "Schema/fixture/fuzz done; cross-architecture/provider compatibility needs other hosts."),
 "MC-047": ("PARTIAL", ["tests/test_faults.py"], "Security, soak, partition/reconnect, restore suites done in-process; fleet-scale certification open."),
 "MC-048": ("IMPLEMENTED", ["tools/release_evidence.py", "evidence/"], "Evidence built and hashed; sealing uses PK_EVIDENCE_KEY if provided, else marked UNSEALED. pk_core gate still unavailable."),
 "MC-049": ("PARTIAL", ["docs/operations/ROLLOUT.md", "plane.py"], "Criteria + emergency disable done; promotion controller belongs to deployment system."),
 "MC-050": ("IMPLEMENTED", ["docs/COMPATIBILITY.md", "docs/operations/BACKUP_RESTORE.md"], "SLAs need owner approval."),
 "MC-051": ("PENDING_APPROVAL", ["docs/operations/"], "Runbooks, governance, exception register written; need owner approval."),
 "MC-052": ("PENDING_APPROVAL", ["docs/adr/ADR-0002-actor-workflow-scope.md"], "Proposed as approved-NA; needs board approval and CHECKLIST wording change."),
 "MC-053": ("BLOCKED", ["wit/pk-runtime.wit", "docs/adr/ADR-0001-runtime-technology.md"], "WIT package written; no wasmCloud host/provider, wRPC transport or Wadm manifest can be built or interop-tested until versions are chosen."),
 "MC-054": ("BLOCKED", [], "Original MASTER.md must be supplied by the owner; it was not reconstructed to avoid fabricating a source document."),
 "MC-055": ("BLOCKED", ["DEPENDENCIES.lock.json", "pyproject.toml"], "Declared as UNPINNED; pk_core source/version/digest must be supplied."),
 "MC-056": ("PARTIAL", ["SBOM.cdx.json", "tools/sbom.py", ".github/workflows/ci.yml", "NOTICE"], "SBOM, CI, provenance hashing done; LICENSE choice is the owner's (BLOCKED)."),
}


def main() -> None:
    mc = {m["id"]: m for m in json.loads((ROOT / "MISSING_COMPONENTS.json").read_text())["components"]}
    tests_dir = ROOT / "tests"
    names = []
    import re
    for p in tests_dir.glob("test_*.py"):
        names += [(p.name, n) for n in re.findall(r"def (test_\w+)", p.read_text())]
    out = []
    for mid, (status, artifacts, note) in S.items():
        key = "mc" + mid.split("-")[1]
        tests = [f"{f}::{n}" for f, n in names if key in n]
        out.append({"id": mid, "component": mc[mid]["component"], "checklist": mc[mid]["checklist"],
                    "status": status, "artifacts": artifacts, "tests": sorted(tests), "open": note})
    counts = {}
    for o in out:
        counts[o["status"]] = counts.get(o["status"], 0) + 1
    (ROOT / "REMEDIATION_STATUS.json").write_text(json.dumps(
        {"schema": "pk.remediation-status/1", "version": (ROOT / "VERSION").read_text().strip(),
         "counts": counts, "items": out}, indent=2) + "\n")
    print(counts)


if __name__ == "__main__":
    main()
