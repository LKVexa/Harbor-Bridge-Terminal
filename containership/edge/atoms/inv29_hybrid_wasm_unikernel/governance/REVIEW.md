# Recurring review procedure (INV29-MC099)

| Cadence | Scope | Inputs | Output |
|---|---|---|---|
| Every release | gate, waivers, ownership, SBOM/scan deltas | `conformance/PK_GATE_RESULTS.json`, `governance/WAIVERS.json` | signed-off release checklist |
| Quarterly (even without a release) | threat model, denylist, SLOs, compatibility matrix, capacity baseline, alert noise | docs/*, ops/*, perf/* | review record appended to the evidence ledger (`kind: review`) |
| On material change | any change to schemas, admission, model, signing | PR diff | security-owner approval (CODEOWNERS) |

Each review appends a ledger entry: date, reviewers, documents reviewed with digests, decisions, follow-up issues.
