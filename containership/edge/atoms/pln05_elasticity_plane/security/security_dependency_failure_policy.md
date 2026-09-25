# PLN-05 security-dependency failure policy

| Dependency | Class | Max cache age | Behaviour on loss | Test |
|---|---|---|---|---|
| identity issuer | bounded fail-static | token lifetime (≤ 1 h) | existing tokens valid until expiry; no new authority | `test_T10_expired_and_revoked` |
| key material (KMS/HSM) | fail-closed at key expiry | key `not_after` | no active key → unready, nothing verifies or publishes | `test_FS15` |
| revocation source | fail-static | key/token lifetime | last known revocations kept | `KeysTest` |
| capability policy | n/a (in package, versioned) | — | — | — |
| attestation (via GAP-09) | fail-closed | — | unattested reporters have no token | `test_T01` |
| trusted time | fail-closed | — | clock step back > 1 s → refuse to decide, unready | `test_FS05` |
| coordination (lease) | bounded fail-static | granted lease | decide only inside the lease; then `E_NOT_LEADER` | `test_FS07` |
| audit sink | buffered then fail-closed | 256 records | ≥ 75 % buffer → security-degraded (no scale-up); 100 % → refuse audited actions and decisions | `test_T19`, `test_FS16` |

Invariant: **no outage expands authority.** During authorisation uncertainty the target is held (never raised); a frozen/quarantined/disabled scope stays so.

Audited events (`PK_AUDIT/1`): authentication failures, authorisation denials, limits updates, ceiling lowering, configuration change/rollback/rejection, freeze/quarantine/disable/resume (proposed, applied, denied), break-glass use (actor class `emergency_admin`). Fields: seq, event_id, ts, actor, actor_class, tenant, site, action, result, reason_code, correlation_id, object_revision, prev, hash. Retention: durable sink 400 days (restricted access, export only to the security team); in-memory window 4096.
