# Recurring Review Process (C53)

| Domain | Cadence | Required approvers (roles) | Checklist / evidence |
|---|---|---|---|
| Access & identities (authz rules, SPIFFE ids, operators) | monthly | security owner + ops owner | export of `Authorizer` rules, operator list |
| Trust bundle / signers | monthly + on rotation | security owner | bundle_version, revoked keys removed after expiry |
| Policy semantics & drift across sites | quarterly | policy owner (GAP-13) | policy digests per site vs baseline |
| Configuration drift | monthly | ops owner | `config_digest` per site vs approved |
| Dependencies / CVEs / runtime EOL | monthly + every release | release owner | SBOM scan report |
| Cryptography profile | annually + on change | security owner | `PK_CRYPTO/1` review |
| Threat model & ADRs | semi-annually + on architecture change | architecture + security | THREAT_MODEL.md, ADR index |
| SLOs, alert quality, false negatives | monthly | SRE owner | burn reports, alert log |
| Capacity model vs production | quarterly | SRE owner | `capacity.py` vs observed |
| Waivers / debt | monthly | component owner + approver of each waiver | `evidence/waivers.json` |
| Backup/restore & quarantine exercises | quarterly | ops owner | exercise record |

Findings are tracked with owner, due date and closure evidence; overdue P0/P1 findings escalate automatically to the accountable owner's manager and block the next release gate (`runtime/gate.py` reads `waivers.json` expiry). Out-of-cycle review after SEV1/SEV2, security events, architecture or cryptographic changes. Records are retained with release evidence. **Owners for each row are unassigned (W-001).**
