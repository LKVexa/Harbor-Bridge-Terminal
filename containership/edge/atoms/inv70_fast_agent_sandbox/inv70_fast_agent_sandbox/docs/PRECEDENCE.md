# Constraint-conflict precedence (INV-70-C019)

When two constraints disagree, the higher-ranked class wins. The losing option is recorded as `overridden` and never silently dropped (`semantics.resolve_conflict`). On a tie, `deny` wins, then lexical order.

1. security  2. tenant_isolation  3. residency  4. correctness  5. resource_limits  6. availability  7. performance  8. cost

Where this is applied in code:
- Capabilities = the caller's request ∩ the token grant. The token (security) wins, and each dropped capability is written as an explain note.
- Fuel: a caller may tighten the budget but never raise it above config (resource_limits beats the caller's wishes).
- Degraded modes: loss of trust, time or audit forces HALT even while draining or overloaded (`derive_mode`).
- Failover never trades isolation, residency or config consistency for availability (`select_failover` returns None).
