# Operation semantics, reason codes, precedence and quotas (MC-61, MC-62, MC-63)

## Lifecycle
`issued → (attenuated)* → verified* → revoked | expired → tombstoned → compacted`

| State | Meaning | Verify result |
|---|---|---|
| issued/attenuated | signed, in window | `grant.valid` |
| not yet valid | `now + skew < not_before` | `grant.not_yet_valid` |
| expired | `now - skew > not_after` (any link) | `grant.expired` |
| revoked | any ancestor's fingerprint or legacy id revoked | `grant.revoked` |
| tombstoned | revoked, retained until `not_after + retention` | `grant.revoked` |

## Success / degraded / failure
- **Success:** `ok: true`, stable success code (`grant.issued`, `grant.attenuated`, `grant.valid`, `grant.revoked`).
- **Degraded:** health `degraded` (a watchdog loop stalled or a dependency breaker is open). Issuance is refused if its dependency is down; verification continues from local durable state only while no site horizon is breached. Never fails open.
- **Failure:** `ok: false` + `code` + `error.details`. Callers must treat any non-`ok` as deny.

## Reason codes
| Code | Cause |
|---|---|
| `api.unsupported_version` | no common `api_version` / unknown grant type |
| `api.malformed` | missing/extra/invalid fields, chain too long |
| `auth.failed` | authentication failed (uniform message) |
| `auth.attestation` | environment requires attestation the caller lacks |
| `policy.denied` | issuer role, tenant, capability, TTL, residency, holder check |
| `policy.quota` | tenant outstanding-issuance quota exhausted |
| `admission.overloaded` | shed by token bucket |
| `control.frozen` | plane/tenant/subject/site quarantined |
| `time.unavailable` / `time.rollback` | trusted time missing, split or rolled back |
| `grant.expired`, `grant.not_yet_valid`, `grant.revoked`, `grant.revocation_unavailable` | lifecycle |
| `grant.signature`, `grant.unsigned` | cryptographic failure |
| `grant.tenant`, `grant.environment`, `grant.site`, `grant.workload`, `grant.audience` | boundary mismatch |
| `grant.capability`, `grant.depth`, `grant.widening`, `grant.expiry_widening`, `grant.cycle`, `grant.version`, `grant.policy_unavailable` | chain/structure |
| `revocation.stale_epoch`, `revocation.corrupt` | controller fencing / log integrity |
| `config.invalid` | configuration rejected or rolled back |

## Constraint precedence (MC-63)
`security > residency > SLO > cost` (`policy.PRECEDENCE`). Any deny wins; the reported deny is the highest-precedence one. No rule → deny.

## Quota and fairness (MC-62)
Per-tenant cap on outstanding issued grants (`tenant_quota_default`, overridable per tenant). Revocation releases quota. One tenant hitting its cap does not affect others. Admission control is global and sheds before any tenant work is done.
