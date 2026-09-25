# Threat model — INV-15 capability boundary

**Assets:** subtask authority (handle tokens), result payloads, host memory/slots, tenant isolation, audit integrity.
**Trust boundaries:** guest ↔ host (every guest op goes through an `InstanceView`); instance ↔ instance; tenant ↔ tenant; process ↔ process (serialized handles).

| Attacker | Capability | Control | Test |
|---|---|---|---|
| Guest code | forge / guess handles | 128-bit CSPRNG token + slot + generation, constant-time compare | `TestCore.test_uniform_foreign_error`, property `forge` op |
| Same-instance module | reuse retired handle | tombstone → HANDLE_CONSUMED; generation bump | `TestGenerations` |
| Cross-tenant caller | use / probe another tenant's handle | view binding; uniform FOREIGN_HANDLE envelope | `TestSideChannel` |
| Network / IPC peer | replay serialized handle | HMAC over handle + tenant/instance, epoch in handle | `TestReplayTenant`, `TestTeardownRestart.test_restart_epoch` |
| Any guest | exhaust memory / CPU | hierarchical budgets, fair share, memory ceilings, bounded wait sets, waiters, tombstones, idempotency window, metric series | `TestBudgetsFairness`, `TestSoakOverload` |
| Compromised host extension | arbitrary host code | **out of scope** — same address space, no defence possible in this model |

Non-goals: confidentiality of payloads in host memory; side-channel resistance beyond error-shape uniformity (timing is measured, not constant-time).
Review trigger: any change to serialization, tenant scope, or the handle layout. **No independent security review has been performed.**
