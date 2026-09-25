# Governance processes (MC-37, 46, 48, 49, 50)

## Ownership (MC-37)
`governance/OWNERS.json` lists every required role. All are **UNASSIGNED**: assigning a person is an organisational decision this build cannot make. The production gate treats an unassigned owner as a blocker.

## Vulnerability, patch and EOL policy (MC-46) — proposed
- Inventory = `evidence/sbom.cdx.json` (generated per release).
- Severity SLA (proposed, not approved): Critical 7 days, High 30 days, Medium 90 days.
- Advisory ingestion: **not implemented** (no advisory feed reachable from the build); the SBOM is the input such a job would consume.
- EOL: Python 3.11 upstream EOL 2027-10; `cryptography` follows OpenSSL support — track in the periodic review.

## Periodic review (MC-48) — proposed cadence
Quarterly: roles/ACLs (`SoftwareKeyStore.acl`, principal maps), trust anchors, approver set, dependency versions, ADR assumptions. Out-of-cycle after any SEV1/SEV2. Findings become waiver or remediation entries.

## Exceptions and waivers (MC-49)
`governance/WAIVERS.json` is the register; its schema requires `id, control_ids, scope, rationale, risk, compensating_controls, owner, approver, created_utc, expires_utc`. `tools/release.py` fails the gate on any expired waiver, any waiver without owner/approver, and any waiver naming a P0 foundational invariant (replay, false trust, tenant isolation). The register is currently empty: **no waivers were granted, and none can be granted by the builder.**

## Production exit gate (MC-50)
`tools/release.py` computes `governance/PRODUCTION_GATE.json` mechanically from the item status table, test results, fuzz/bench evidence, owners and waivers. It can only ever output `GO` if every item is `[x]` or waived and a signed approver record exists; the builder cannot produce either.
