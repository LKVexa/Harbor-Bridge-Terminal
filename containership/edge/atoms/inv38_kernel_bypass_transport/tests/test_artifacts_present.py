import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ["docs/OWNERSHIP.md",".github/CODEOWNERS","ops/escalation.yaml",
  "docs/adr/ADR-0038-kernel-bypass-backend.md","SECURITY.md","docs/PATCH_AND_EOL_POLICY.md",
  "observability/resource-identity.schema.json","observability/lineage-correlation.md",
  "release/acceptance.schema.json","governance/waivers.schema.json","traceability/INV38_RTM.json"]
def test_all_required_artifacts_exist():
    missing = [p for p in REQUIRED if not os.path.exists(os.path.join(ROOT, p))]
    assert not missing, f"missing: {missing}"
