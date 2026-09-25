#!/usr/bin/env python3
"""Requirements traceability matrix (checklist #12).

Maps each of the 100 checklist components to artifacts, executable tests, status and residual gap.
Writes evidence/traceability.json and checks that every referenced artifact exists.

Status vocabulary (honest by construction):
  IMPLEMENTED  artifact(s) + executable test(s) exist in-repo and pass
  PARTIAL      in-repo portion implemented and tested; a named residual needs external action
  OPEN         cannot be closed inside the repository (owner decision, infrastructure, approval)
No component is IMPLEMENTED while it depends on an owner approval, real infrastructure run, or
measurement that has not been performed -- those residuals are listed and tracked as waivers.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "requirements" / "missing-component-checklist-v4.2.0.md"

T = "tests/"
A = "docs/architecture/"
S = "docs/security/"
O = "docs/operations/"
G = "docs/governance/"
P = "docs/performance/"
R = "docs/requirements/"
PKG = "inv55_secrets_integration/"
APPROVAL = "owner/security/ops approvals not recorded (PENDING-OWNER-APPROVAL)"

# id: (status, artifacts, tests, residual)
M = {
 1: ("OPEN", [G + "OWNERSHIP.md", "CODEOWNERS", "catalog-info.yaml"], [], "real owners, on-call route and branch protection must be assigned by the owner"),
 2: ("PARTIAL", [A + "ADR-0001-vault-provider.md"], [], APPROVAL),
 3: ("PARTIAL", [A + "deployment-patterns.md"], [], APPROVAL),
 4: ("PARTIAL", [R + "SRS.md"], [T + "test_service_contract.py"], APPROVAL),
 5: ("PARTIAL", [R + "NFR.md"], [], "targets defined; fleet measurements not yet taken; " + APPROVAL),
 6: ("IMPLEMENTED", [PKG + "errors.py", A + "outcome-semantics.md"], [T + "test_schemas_fixtures.py", T + "test_service_contract.py"], ""),
 7: ("IMPLEMENTED", [PKG + "service.py", A + "lifecycle.md"], [T + "test_service_contract.py"], ""),
 8: ("PARTIAL", [A + "compatibility-policy.md"], [T + "test_service_contract.py"], "deprecation window " + APPROVAL),
 9: ("IMPLEMENTED", [PKG + "resilience.py", A + "quota-fairness.md"], [T + "test_resilience.py", T + "test_security_adversarial.py"], ""),
 10: ("IMPLEMENTED", [A + "disconnected-policy.md", PKG + "service.py"], [T + "test_resilience.py"], ""),
 11: ("PARTIAL", [A + "constraint-precedence.md"], [], APPROVAL),
 12: ("IMPLEMENTED", ["tools/traceability.py", "evidence/traceability.json"], [T + "test_release_tooling.py"], ""),
 13: ("PARTIAL", [R + "master-workflow.md"], [], "MASTER.md from the series is not in this snapshot"),
 14: ("IMPLEMENTED", [PKG + "providers/base.py"], [T + "test_resilience.py", T + "test_vault_adapter.py"], ""),
 15: ("PARTIAL", [PKG + "providers/vault.py"], [T + "test_vault_adapter.py", T + "test_vault_real.py"], "real-Vault suite must run green in CI (vault-real job); service does not auto-renew dynamic leases"),
 16: ("PARTIAL", [A + "compatibility-matrix.md", "pyproject.toml"], [T + "test_vault_adapter.py"], "matrix only exercised against real Vault once vault-real job runs per version"),
 17: ("IMPLEMENTED", [PKG + "schemas/"], [T + "test_schemas_fixtures.py"], ""),
 18: ("PARTIAL", [PKG + "identity.py", S + "peer-authentication.md"], [T + "test_security_adversarial.py"], "HS256 JWT implemented; SPIFFE/OIDC authenticators and key distribution need the identity issuer (INV-59/IdP)"),
 19: ("PARTIAL", [PKG + "identity.py"], [T + "test_security_adversarial.py"], "local deny-by-default engine; integration with INV-59 policy service not available in this repo"),
 20: ("IMPLEMENTED", [PKG + "resilience.py", PKG + "service.py"], [T + "test_resilience.py", T + "test_service_contract.py"], ""),
 21: ("IMPLEMENTED", [PKG + "errors.py", PKG + "schemas/error.schema.json"], [T + "test_schemas_fixtures.py"], ""),
 22: ("IMPLEMENTED", [PKG + "service.py", A + "compatibility-policy.md"], [T + "test_service_contract.py"], ""),
 23: ("IMPLEMENTED", [A + "interface-limits.md", PKG + "service.py"], [T + "test_service_contract.py", T + "test_resilience.py"], ""),
 24: ("IMPLEMENTED", ["fixtures/conformance/fixtures.json"], [T + "test_schemas_fixtures.py"], ""),
 25: ("PARTIAL", [T + "vault_fake.py"], [T + "test_vault_adapter.py"], "runtime/identity/audit-pipeline neighbours (INV-46, INV-59) not available here"),
 26: ("IMPLEMENTED", [PKG + "schemas/config.schema.json", PKG + "config.py"], [T + "test_config_audit_telemetry.py"], ""),
 27: ("IMPLEMENTED", ["config/overlays/"], [T + "test_config_audit_telemetry.py"], ""),
 28: ("IMPLEMENTED", [PKG + "config.py"], [T + "test_config_audit_telemetry.py"], ""),
 29: ("IMPLEMENTED", [PKG + "config.py"], [T + "test_config_audit_telemetry.py"], ""),
 30: ("IMPLEMENTED", [PKG + "config.py"], [T + "test_config_audit_telemetry.py"], ""),
 31: ("IMPLEMENTED", ["tools/secret_scan.py", ".github/workflows/ci.yml"], [T + "test_secret_scan.py"], ""),
 32: ("IMPLEMENTED", [PKG + "bootstrap.py"], [T + "test_release_tooling.py"], ""),
 33: ("IMPLEMENTED", ["pyproject.toml"], [T + "test_release_tooling.py"], ""),
 34: ("PARTIAL", ["requirements-test.txt", "evidence/sbom.cdx.json"], [T + "test_release_tooling.py"], "hash-pinned lock requires a resolver run with network in CI (pip-compile --generate-hashes)"),
 35: ("OPEN", [], [T + "test_component.py"], "pk_core is not in this snapshot; conformance tests skip (skip != pass)"),
 36: ("OPEN", ["THIRD-PARTY-NOTICES.md"], [], "project LICENSE must be chosen by the owner"),
 37: ("PARTIAL", [".github/workflows/ci.yml"], [], "pipeline defined; not yet executed on the hosting CI"),
 38: ("PARTIAL", [S + "threat-model.md"], [T + "test_security_adversarial.py"], "security review " + APPROVAL),
 39: ("IMPLEMENTED", [PKG + "identity.py", S + "identity-roles.md"], [T + "test_security_adversarial.py"], ""),
 40: ("IMPLEMENTED", [S + "ambient-authority.md", PKG + "bootstrap.py"], [T + "test_security_adversarial.py"], ""),
 41: ("PARTIAL", [PKG + "providers/vault.py", S + "peer-authentication.md"], [T + "test_vault_adapter.py"], "peer/node SPIFFE identity not implemented"),
 42: ("OPEN", [S + "artifact-provenance.md", "tools/release_evidence.py"], [], "signing requires a key-custody decision (GAP-07); digests are produced, signatures are not"),
 43: ("IMPLEMENTED", [S + "tenant-isolation.md", PKG + "service.py"], [T + "test_security_adversarial.py"], ""),
 44: ("IMPLEMENTED", [PKG + "providers/vault.py", S + "encryption.md"], [T + "test_vault_adapter.py"], ""),
 45: ("OPEN", [S + "encryption.md"], [], "at-rest is Vault seal/KMS configuration owned by the platform; needs evidence from the Vault deployment"),
 46: ("IMPLEMENTED", [S + "dependency-outage-matrix.md"], [T + "test_resilience.py", T + "test_security_adversarial.py"], ""),
 47: ("IMPLEMENTED", [PKG + "audit.py"], [T + "test_config_audit_telemetry.py", T + "test_security_adversarial.py"], ""),
 48: ("IMPLEMENTED", [T + "test_security_adversarial.py"], [T + "test_security_adversarial.py", T + "test_property_fuzz.py"], ""),
 49: ("PARTIAL", [PKG + "secretvalue.py", S + "memory-handling.md"], [T + "test_security_adversarial.py"], "CPython cannot guarantee no transient copies; hard isolation is process-level"),
 50: ("PARTIAL", [S + "secret-name-privacy.md", PKG + "audit.py"], [T + "test_config_audit_telemetry.py"], "pseudonymise() exists; export pipeline that applies it is not in this repo"),
 51: ("IMPLEMENTED", [A + "failure-mode-catalog.md"], [T + "test_resilience.py"], ""),
 52: ("IMPLEMENTED", [PKG + "service.py"], [T + "test_service_contract.py"], ""),
 53: ("IMPLEMENTED", [PKG + "resilience.py"], [T + "test_resilience.py"], ""),
 54: ("IMPLEMENTED", [PKG + "resilience.py"], [T + "test_resilience.py"], ""),
 55: ("PARTIAL", [A + "failover.md"], [T + "test_vault_adapter.py"], "multi-endpoint client failover not implemented (relies on Vault HA/LB)"),
 56: ("IMPLEMENTED", [A + "degraded-mode.md", PKG + "service.py"], [T + "test_resilience.py"], ""),
 57: ("IMPLEMENTED", [A + "crash-restart-semantics.md", PKG + "service.py"], [T + "test_service_contract.py", T + "test_config_audit_telemetry.py"], ""),
 58: ("PARTIAL", [A + "split-brain.md"], [T + "test_concurrency.py"], "single-instance idempotency reservation + provider CAS implemented; cross-instance fencing/shared idempotency store not implemented"),
 59: ("IMPLEMENTED", [PKG + "service.py"], [T + "test_service_contract.py"], ""),
 60: ("IMPLEMENTED", [T + "test_resilience.py"], [T + "test_resilience.py"], ""),
 61: ("IMPLEMENTED", ["tools/benchmark.py", "evidence/benchmark_baseline.json"], [T + "test_release_tooling.py"], ""),
 62: ("PARTIAL", [P + "performance-policy.md"], [], "thresholds set from one host; " + APPROVAL),
 63: ("PARTIAL", ["tools/benchmark.py"], [], "in-process steady/burst/overload only; no fleet-scale or soak run"),
 64: ("IMPLEMENTED", ["tools/benchmark.py"], [T + "test_release_tooling.py"], ""),
 65: ("OPEN", [], [], "profiler/copy/context-switch/network-hop analysis not performed"),
 66: ("PARTIAL", [P + "performance-policy.md", PKG + "service.py"], [T + "test_resilience.py"], "TTL cache implemented; batching not implemented"),
 67: ("IMPLEMENTED", [PKG + "service.py", PKG + "resilience.py", PKG + "telemetry.py"], [T + "test_service_contract.py", T + "test_config_audit_telemetry.py"], ""),
 68: ("OPEN", [P + "power-thermal.md"], [], "not measured; needs instrumented hardware"),
 69: ("PARTIAL", [P + "capacity-model.md"], [], "model from single-host benchmark; not validated in production"),
 70: ("IMPLEMENTED", ["tools/benchmark.py", ".github/workflows/ci.yml"], [T + "test_release_tooling.py"], ""),
 71: ("IMPLEMENTED", [PKG + "service.py"], [T + "test_service_contract.py"], ""),
 72: ("IMPLEMENTED", [PKG + "telemetry.py"], [T + "test_config_audit_telemetry.py"], ""),
 73: ("PARTIAL", [PKG + "telemetry.py"], [T + "test_security_adversarial.py", T + "test_config_audit_telemetry.py"], "log shipping/collector pipeline is platform-owned"),
 74: ("PARTIAL", [PKG + "telemetry.py"], [T + "test_config_audit_telemetry.py"], "W3C propagation implemented; OTLP exporter not included"),
 75: ("PARTIAL", [S + "telemetry-privacy.md", PKG + "telemetry.py"], [T + "test_config_audit_telemetry.py"], "bounded channel via DecisionLedger; no separate high-cardinality store"),
 76: ("IMPLEMENTED", [PKG + "telemetry.py", PKG + "service.py"], [T + "test_config_audit_telemetry.py"], ""),
 77: ("IMPLEMENTED", [PKG + "telemetry.py", O + "observability.md"], [T + "test_config_audit_telemetry.py"], ""),
 78: ("PARTIAL", [PKG + "service.py"], [T + "test_config_audit_telemetry.py"], "release+config+policy digests on every decision; infra-graph correlation needs estate CMDB"),
 79: ("PARTIAL", [S + "telemetry-privacy.md"], [], APPROVAL),
 80: ("PARTIAL", [O + "dashboards-alerts.md"], [], "alert rules specified; not deployed to a monitoring stack"),
 81: ("IMPLEMENTED", [T + "test_service_contract.py"], [T + "test_service_contract.py"], ""),
 82: ("PARTIAL", [T + "test_vault_real.py"], [T + "test_vault_real.py"], "MANDATORY suite currently SKIPS without a Vault; must run green in CI"),
 83: ("PARTIAL", [A + "compatibility-matrix.md"], [T + "test_vault_real.py"], "matrix jobs per Vault/Python version defined; not yet executed"),
 84: ("IMPLEMENTED", [T + "test_property_fuzz.py"], [T + "test_property_fuzz.py"], ""),
 85: ("IMPLEMENTED", [T + "test_concurrency.py"], [T + "test_concurrency.py"], ""),
 86: ("IMPLEMENTED", [T + "test_security_adversarial.py", S + "threat-model.md"], [T + "test_security_adversarial.py"], ""),
 87: ("OPEN", ["tools/benchmark.py"], [], "soak and fleet-scale certification not performed"),
 88: ("PARTIAL", [T + "test_resilience.py"], [T + "test_resilience.py"], "in-process partition/reconnect covered; real network partition against Vault HA not run"),
 89: ("IMPLEMENTED", ["tools/release_evidence.py"], [T + "test_release_tooling.py"], ""),
 90: ("PARTIAL", [G + "slo-support-policy.md"], [], APPROVAL),
 91: ("OPEN", [O + "rollout-rollback.md"], [], "canary/staged rollout automation needs the deployment platform; config rollback is implemented"),
 92: ("PARTIAL", [A + "compatibility-matrix.md"], [], APPROVAL),
 93: ("PARTIAL", [G + "patching-vuln-eol.md"], [], APPROVAL),
 94: ("PARTIAL", [O + "backup-restore.md", PKG + "service.py"], [T + "test_service_contract.py"], "restore drill against real Vault snapshot not performed"),
 95: ("PARTIAL", [O + "runbooks.md"], [], "runbooks not yet exercised by an operator"),
 96: ("PARTIAL", [O + "incident-response.md"], [], "no tabletop exercise recorded; " + APPROVAL),
 97: ("PARTIAL", [G + "review-process.md"], [], "first review not yet held"),
 98: ("IMPLEMENTED", [G + "waiver-register.md"], [T + "test_release_tooling.py"], ""),
 99: ("IMPLEMENTED", ["tools/exit_gate.py", "evidence/exit_gate.json"], [T + "test_release_tooling.py"], ""),
 100: ("OPEN", [G + "release-policy.md", "CODEOWNERS"], [], "branch protection and required reviewers must be configured on the hosting platform"),
}


def titles() -> dict[int, tuple[str, str]]:
    text = CHECKLIST.read_text(encoding="utf-8")
    return {int(m.group(1)): (m.group(2).strip(), m.group(3))
            for m in re.finditer(r"### (\d+)\. (.+)\n\n\*\*Priority:\*\* (P\d)", text)}


def build() -> dict:
    tt = titles()
    rows, missing = [], []
    for i in range(1, 101):
        status, arts, tests, residual = M[i]
        for a in arts + tests:
            if not (ROOT / a).exists():
                missing.append(f"#{i}: {a}")
        rows.append({"id": i, "control_id": f"INV55-CL-{i:03d}", "title": tt[i][0], "priority": tt[i][1],
                     "status": status, "artifacts": arts, "tests": tests, "residual": residual,
                     "owner": "<UNASSIGNED>", "gate": "tools/exit_gate.py"})
    summary = {}
    for r in rows:
        summary.setdefault(r["priority"], {}).setdefault(r["status"], 0)
        summary[r["priority"]][r["status"]] += 1
    return {"format": "inv55-traceability/1", "version": (ROOT / "VERSION").read_text().strip(),
            "summary": summary, "missing_artifacts": missing, "components": rows}


def main() -> int:
    out = build()
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "traceability.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"], indent=1))
    if out["missing_artifacts"]:
        print("MISSING:", *out["missing_artifacts"], sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
