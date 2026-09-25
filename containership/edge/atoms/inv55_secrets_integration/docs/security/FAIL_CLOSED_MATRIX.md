# Dependency-outage fail-closed matrix (checklist #46)

| Dependency down | resolve | use | rotate | scope | health.ready | Test |
|---|---|---|---|---|---|---|
| Provider (no stale policy) | RETRYABLE `PROVIDER-UNAVAILABLE` / `CIRCUIT-OPEN` | from fresh cache only, else RETRYABLE | RETRYABLE | unaffected (local) | false (breaker open) | `test_outage_offline_deny_then_recovery` |
| Provider (stale policy, waiver) | DEGRADED within `max_stale_s`, audited | same | RETRYABLE | unaffected | false | `test_degraded_stale_serving_when_configured` |
| Provider sealed | as provider down | same | same | same | false (`provider_healthy`) | `test_service_over_vault_end_to_end` |
| Identity key unavailable | UNAUTHENTICATED | UNAUTHENTICATED | UNAUTHENTICATED | UNAUTHENTICATED | n/a | `Identity` tests |
| Audit sink unwritable | request fails (append raises) → INTERNAL, no grant returned | same | same | same | false (`audit_writable`) | design; see FMEA F-07 |
| Clock rollback | CLOCK (terminal) | CLOCK | CLOCK | CLOCK | — | `test_T10_clock_rollback` |
| Config invalid | not activated; previous stays | — | — | — | — | `Config.test_transactional_activation_and_rollback` |
No row returns plaintext or a grant when a security dependency is unavailable.
