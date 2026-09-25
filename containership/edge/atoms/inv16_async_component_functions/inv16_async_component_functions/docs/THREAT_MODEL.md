# INV-16 Threat Model (v4.3.0)

**Status:** draft for owner review · **Review trigger:** any change to ABI transport, serialization,
distributed admission, dependency boundaries, or the declaration schema.

## Trust boundaries

```
 guest component ──invoke/complete/cancel──▶ INV-16 runtime ──subtasks──▶ INV-15 ABI
        ▲                                         │   ▲                     (surrogate today)
        │ values (ABI envelope)                   │   └── build-time descriptor ◀── INV-11 compiler
        └─────────────────────────────────────────┘                               (surrogate today)
                       │ events/metrics/traces (one-way, non-blocking)
                       ▼
                 telemetry sinks (untrusted for correctness)
```

Trusted: the runtime process and its build-time descriptor (verified by digest). Untrusted: every call id,
value, cancellation text, traceparent and function name arriving from a guest or adjacent layer; telemetry
backends; the ambient `PYTHONPATH` (for `pk_core`).

## Protected assets

Per-call state and return values · declaration table (async-ness) · cancellation authority · admission budgets
(in-flight, queue, bridge waiters, call-id space, tombstones) · cross-instance isolation · evidence/provenance.

## Threats, controls and tests

| ID | Threat | Severity × likelihood | Preventive control | Detective control | Tests |
|---|---|---|---|---|---|
| T1 | Re-entrancy corrupts suspended callee state | High × Med | policy refuse/queue, stateful ≠ allow, one lock | `reentrancy_refusals`, overlap sampler | test_stress.ReentrancyStress, property mutants |
| T2 | Cross-call / cross-instance data leakage | High × Low | per-call `CallState`, ABI envelope bound to call id, fresh lifted objects | canary tests | test_security.T2 ×2, test_abi |
| T3 | Double delivery / replay of terminal events | High × Med | single atomic terminal transition, tombstones, `HistoryExpired` | `double_delivery_attempts` (critical, never sampled) | test_races, test_security.T3 |
| T4 | Async-ness changed at run time | High × Low | `MappingProxyType`, sealed attributes, descriptor digest drift check | `DeclarationError` | test_security.T4, test_declare |
| T5 | Flood of unknown/expired ids (CPU/memory/log amplification) | Med × Med | O(1) classification, bounded tombstones, bounded EventLog | expiry counters | test_security.T5 |
| T6 | Admission exhaustion | Med × Med | hard in-flight limit, bounded queue, bounded bridge waiters, call-id exhaustion fails closed | refusal counters, near-exhaustion event | test_security.T6, test_stress, test_bridge |
| T7 | Log/telemetry injection via reason text | Med × Med | control-char strip, secret redaction, length caps, structured JSON | — | test_security.T7 |
| T8 | Serialization confusion / type smuggling | High × Low | exact-type ABI lowering, strict canonical lifting, limits | `AbiError` | test_security.T8, test_abi fuzz |
| T9 | Dependency substitution / downgrade (`pk_core`) | High × Med | preflight: shadowing, surface, version range, fail closed | preflight report | test_security.T9, test_edges |
| T10 | Trace context used as an authority | Med × Low | trace ids are correlation only; malformed → new root | `trace_context_rejected` | test_security.T10 |
| T11 | TOCTOU between admission check and insert | High × Low | check+insert under one lock; faults evaluated before mutation | fault matrix | test_faults, test_races |
| T12 | Supply chain of the release itself | High × Low | reproducible build, SBOM, provenance, checksum signature | `release.py verify` | release verify evidence |

## Residual risk (requires owner acceptance)

1. Limits are process-local (ADR-0003); a multi-owner deployment is rejected by preflight but not
   technically prevented if preflight is skipped.
2. Adjacent-layer behaviour is proven only against surrogates until INV-15/10/11/17/20 fixtures are pinned.
3. Release signing uses an owner-held Ed25519 key that does not exist yet; provenance is SLSA L1 (local builder).
4. The Python model is not the production runtime; memory-safety properties of a native backend are out of scope.

Owner sign-off: ______________________  Date: __________
