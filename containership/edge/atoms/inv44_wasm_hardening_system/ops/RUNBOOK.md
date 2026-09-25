# Runbook — INV-44 (C091, C095, C096)

Every refusal carries a structured code (`errors.CODES`). Find it in the audit
log (`outcome: refused`, `code`) or the logs, then:

| Code | Meaning | First action | Never |
|---|---|---|---|
| WH-HARDENING-INCOMPLETE | engine missing a feature | check active config (`ConfigStore.active`) and host guard-page support | remove the feature from REQUIRED_HARDENING |
| WH-RECEIPT-INVALID / WH-OUTPUT-MALFORMED | bytes/receipt mismatch or malformed module | re-run the verifier on the exact artifact; compare sha256 | hand-issue a receipt |
| WH-TOOLCHAIN-UNAPPROVED | compiler identity not allowlisted | security owner reviews the toolchain digest | add a toolchain without review |
| WH-AMBIENT-IMPORT | module imports ungranted host function | grant the import on the token if justified | grant `*` |
| WH-TENANT-MISMATCH | cross-tenant request | investigate as a security event | reuse an engine across tenants |
| WH-AUTHZ-DENIED / WH-CAPABILITY-EXPIRED | missing/expired/revoked capability | re-issue with least privilege | extend TTL past 24 h |
| WH-DEPENDENCY-UNAVAILABLE | clock or revocation source down | restore the dependency; admissions stay refused meanwhile | bypass the check |
| WH-OVERLOADED | admission control shed | scale out or raise quota after capacity review | disable admission control |
| WH-AUDIT-CHAIN-BROKEN | audit log tampered or truncated | preserve the file, compare with the external head anchor, open an incident | "repair" the chain |
| WH-CONFIG-INVALID / WH-CONFIG-CONFLICT | bad or concurrent config | fix the document; re-read active version and retry | edit files under versions/ |

## Rollback
`ConfigStore.rollback(n, activated_by=...)` re-activates an earlier immutable version.
Code rollback: redeploy the previous wheel whose provenance envelope verifies.

## Audit head anchoring
After each batch, record `AuditLog.head()` somewhere the log's writer cannot
modify (owner decision: WORM bucket, ticket, or signed release notes). Verify
with `verify(expected_head=...)`.

## Review cadence (C097)
Quarterly: toolchain allowlist, key rotation, waivers (ops/WAIVERS.json), alert thresholds. Owner UNASSIGNED.
