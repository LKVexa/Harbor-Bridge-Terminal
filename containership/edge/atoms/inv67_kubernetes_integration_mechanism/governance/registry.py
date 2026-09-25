"""Component registry: the 68 checklist components mapped to the artifacts in
this repository that implement them. Titles/priorities/audit mappings are
parsed from the checklist itself so the registry cannot drift from it."""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/governance/INV67_v4.2.0_MISSING_COMPONENT_IMPLEMENTATION_CHECKLIST.md"

ARTIFACTS: dict[int, list[str]] = {
    1: ["docs/OWNERSHIP.md", "docs/governance/ownership.json", ".github/CODEOWNERS"],
    2: ["docs/architecture/ADR-001-integration-pattern.md"],
    3: ["docs/requirements.json", "docs/REQUIREMENTS.md"],
    4: ["plane/lifecycle.py", "docs/architecture/LIFECYCLE.md"],
    5: ["plane/compat.py", "docs/architecture/COMPATIBILITY.md"],
    6: ["plane/resilience.py", "docs/architecture/CAPACITY.md"],
    7: ["docs/architecture/DISCONNECTED.md", "plane/controller.py"],
    8: ["plane/policy.py", "docs/architecture/PRECEDENCE.md"],
    9: ["docs/requirements.json", "governance/gate.py"],
    10: ["api/crds/wasmworkloads.inv67.linearfinance.org.yaml", "plane/manifests.py"],
    11: ["plane/controller.py"],
    12: ["plane/kube.py"],
    13: ["plane/status.py", "schemas/INV67_CONDITION_v1.schema.json"],
    14: ["plane/downstream.py", "schemas/PK_K8S_PLACE_v1.schema.json"],
    15: ["plane/identity.py"],
    16: ["plane/compat.py"],
    17: ["deploy/base/deployment.yaml", "deploy/base/rbac.yaml", "deploy/base/networkpolicy.yaml", "deploy/base/pdb.yaml",
         "deploy/base/kustomization.yaml", "deploy/overlays/dev/kustomization.yaml", "deploy/overlays/prod/kustomization.yaml"],
    18: ["plane/config.py", "schemas/INV67_CONFIG_v1.schema.json", "examples/config.json"],
    19: ["plane/config.py"],
    20: ["plane/config.py"],
    21: ["plane/secrets.py"],
    22: ["plane/bootstrap.py"],
    23: ["docs/architecture/THREAT_MODEL.md"],
    24: ["plane/authz.py"],
    25: ["plane/authz.py", "deploy/base/rbac.yaml"],
    26: ["plane/artifact.py"],
    27: ["plane/audit.py", "plane/secrets.py"],
    28: ["plane/audit.py"],
    29: ["tests/security/test_adversarial.py"],
    30: ["plane/observability.py", "plane/controller.py"],
    31: ["plane/resilience.py"],
    32: ["plane/resilience.py"],
    33: ["plane/leader.py"],
    34: ["plane/journal.py"],
    35: ["plane/resilience.py", "docs/runbooks/emergency-freeze.md"],
    36: ["tests/fault/test_faults.py"],
    37: ["tests/performance/test_benchmark.py", "evidence/perf_baseline.json"],
    38: ["docs/architecture/SLO.md"],
    39: ["tests/performance/test_benchmark.py"],
    40: ["plane/capacity.py", "docs/architecture/CAPACITY.md"],
    41: ["plane/observability.py"],
    42: ["plane/observability.py"],
    43: ["plane/observability.py"],
    44: ["plane/observability.py"],
    45: ["plane/observability.py"],
    46: ["docs/telemetry/POLICY.md"],
    47: ["docs/telemetry/POLICY.md", "docs/telemetry/alerts.yaml", "docs/telemetry/dashboard.json"],
    48: ["tests/contract/test_contracts.py", "plane/schema.py"],
    49: ["tests/integration/test_end_to_end.py"],
    50: ["plane/compat.py", ".github/workflows/ci.yml"],
    51: ["tests/fuzz/test_property.py"],
    52: ["tests/concurrency/test_races.py"],
    53: ["tests/performance/test_benchmark.py"],
    54: ["governance/gate.py", "schemas/INV67_EVIDENCE_v1.schema.json"],
    55: ["governance/gate.py"],
    56: ["docs/SUPPORTED_VERSIONS.md"],
    57: ["docs/VULNERABILITY_POLICY.md"],
    58: ["docs/runbooks/backup-restore.md"],
    59: ["docs/runbooks/install.md", "docs/runbooks/upgrade-rollback.md", "docs/runbooks/degraded-mode.md",
         "docs/runbooks/orphan-cleanup.md", "docs/runbooks/emergency-freeze.md"],
    60: ["docs/INCIDENT_RESPONSE.md"],
    61: ["docs/REVIEW_PROGRAM.md"],
    62: ["docs/governance/exceptions.json"],
    63: ["docs/RELEASE_GATE.md", "governance/gate.py"],
    64: ["pyproject.toml"],
    65: [".github/workflows/ci.yml"],
    66: ["NOTICE", "sbom.cdx.json", "governance/release.py"],
    67: ["pyproject.toml"],
    68: ["governance/release.py"],
}

# Items whose evidence can only be design/process artifacts plus tests of the
# code they describe; items needing things absent here list their exceptions.
EXTERNAL = {  # item -> exception ids beyond the universal EXC-002
    1: ["EXC-001", "EXC-003"], 2: ["EXC-003"], 3: ["EXC-003"], 4: ["EXC-003"], 5: ["EXC-003", "EXC-006"],
    6: ["EXC-003"], 7: ["EXC-003"], 8: ["EXC-003"], 10: ["EXC-005"], 11: ["EXC-005"], 12: ["EXC-005"],
    14: ["EXC-006"], 15: ["EXC-006"], 16: ["EXC-006"], 17: ["EXC-005"], 23: ["EXC-003"], 24: ["EXC-008"],
    27: ["EXC-008"], 37: ["EXC-007"], 38: ["EXC-007"], 39: ["EXC-007"], 40: ["EXC-007"], 44: ["EXC-011"],
    49: ["EXC-005", "EXC-006"], 50: ["EXC-005"], 53: ["EXC-007"], 54: ["EXC-004"], 55: ["EXC-009"],
    58: ["EXC-007"], 59: ["EXC-003"], 60: ["EXC-003"], 63: ["EXC-001", "EXC-004"], 65: ["EXC-004"],
    66: ["EXC-004", "EXC-010"], 67: ["EXC-012"], 68: ["EXC-004"],
}


def components() -> list[dict]:
    text = CHECKLIST.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"^## (\d{2})\. (.+?)\n\n\*\*Audit mapping:\*\* (.+?)  \n\*\*Priority:\*\* (P\d)", text, re.M):
        n = int(m.group(1))
        out.append({"item": n, "title": m.group(2).strip(), "audit_mapping": m.group(3).strip(), "priority": m.group(4),
                    "artifacts": ARTIFACTS[n], "exceptions": ["EXC-002"] + EXTERNAL.get(n, [])})
    return out
