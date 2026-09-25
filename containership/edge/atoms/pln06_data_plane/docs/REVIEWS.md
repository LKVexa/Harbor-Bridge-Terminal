# Recurring control reviews — PLN-06 (WP #51, C098)

| Review | Cadence | Owner (role) | Inputs | Output (retained in `reviews/`) |
|---|---|---|---|---|
| Access & capabilities | 90 days | security_contact | issued credential inventory, CODEOWNERS, KMS access | `reviews/YYYY-MM-access.md` |
| Residency policy | 30 days | service_owner | GAP-13 revisions, refusal metrics | `reviews/YYYY-MM-policy.md` |
| Dependencies & SBOM | 30 days | technical_lead | `sbom.cdx.json`, scanner output | `reviews/YYYY-MM-deps.md` |
| Configuration | 90 days | sre_oncall_target | `config-history.jsonl`, overlays | `reviews/YYYY-MM-config.md` |
| Architecture & threat model | each MINOR release / 90 days | technical_lead + security | ADRs, THREAT_MODEL, incidents | `reviews/YYYY-MM-architecture.md` |
| Waivers/exceptions | 30 days | service_owner | `WAIVERS.json` | `reviews/YYYY-MM-waivers.md` |
| Ownership | 90 days | service_owner | `OWNERSHIP.json` | `reviews/YYYY-MM-ownership.md` |

Overdue reviews: `tools/release_gate.py` fails when `OWNERSHIP.json.last_reviewed` is older than `review_cadence_days` or null; overdue remediation escalates along `escalation_chain`. Use `reviews/TEMPLATE.md`.
