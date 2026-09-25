# Recurring review program (MC-70)

| Cadence | Review | Evidence |
|---|---|---|
| Every release | gate run, SBOM, bench diff | `evidence/EVIDENCE.json` archived with the release |
| Monthly | revocation-log and audit-chain verification, horizon-breach report | `health()` snapshot |
| Quarterly | key rotation drill, restore-from-log drill, freeze/thaw drill | runbook checklist signed |
| Quarterly | threat model refresh vs SECURITY.md, waiver ledger review | updated WAIVERS.md |
| Yearly | external security review | report stored beside evidence |
