# RB-INCIDENT — Incident response and on-call (MC-065)

## Severity (PROPOSED)
| Sev | Examples | Ack / engage |
|---|---|---|
| SEV1 | unadmitted manifest forwarded; `ECP_AUDIT_TAMPERED`; identity or signer key compromise; cross-tenant disclosure | 15 min; page security + service owner |
| SEV2 | admissions failing (journal down, not ready); INV-63 delivery backlog > 30 min | 30 min |
| SEV3 | elevated denials, a single dependency degraded, quota disputes | next business day |

Paging: alert routing in `ops/alerts/inv66-rules.yml` (the `severity` label). Rotations are UNASSIGNED (`governance/owners.json`).

## Containment playbooks
- **Global freeze:** `emergency_disable(principal, reason)`, i.e. a freeze at the org root.
- **Tenant/lattice quarantine:** `freeze("acme/<tenant>[/<lattice>]")`.
- **Signer/registry revocation:** new generation with the signer `revoked: true` or the registry removed; run `policy_impact` first; activate with N approvers.
- **Credential rotation:** remove the compromised key from the IdP JWKS config (new generation), rotate the anchor/TLS keys (RB-DAY2).
- **Disable forwarding:** freeze the affected scope. Pending deliveries are not resumed while it is frozen.

## Evidence preservation (before any repair)
1. `cli export ROOT > export-<ts>.json` and a copy of `journal/anchors/`.
2. Save `/metrics`, the logs for the window, the active generation (`/version`), the trusted-key set, and the affected decision ids (`/v1/explain/<id>`).
3. Hash every artifact (`sha256sum`) and store the hashes in the ticket.

## Recovery criteria before unfreezing
`verify-journal` INTACT · root cause fixed · the generation reviewed · affected workloads identified through `policy_impact` · 2-person release.

## Communications
The incident commander (service owner) owns status updates every 30 min for SEV1. The security owner decides on compliance/customer notification.

## Post-incident review
Within 5 business days: root cause, failed controls, corrective actions with owners and dates, and updates to `docs/THREAT_MODEL.md` and the runbooks.

## Exercises
Quarterly tabletop and a semi-annual game day. The disaster suite (`tests/disaster`) is the automated floor, not a substitute.
