# Recurring review controls (MC-062)

| Review | Cadence | Inputs | Output |
|---|---|---|---|
| Access (tokens, operator caps, key holders) | monthly | key fingerprints, issued-capability log | signed review record |
| Policy/config | each revision + quarterly | config history, overlays | approval in audit log |
| Dependencies / Firecracker CVEs | weekly | upstream advisories | manifest update or waiver |
| Threat model | quarterly + on ADR change | `THREAT_MODEL.md` | updated doc |
| Architecture/ADR | semi-annual | ADRs | re-approval |
| Waiver/debt registry | monthly | `release/WAIVERS.json` | expiries enforced by gate |

Template: `release/REVIEW_TEMPLATE.json`. Reviewer assignment: UNASSIGNED (BLOCKED).
