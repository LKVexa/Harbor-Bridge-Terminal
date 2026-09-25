# SHALL-level requirements with stable identifiers — INV-44 (C011, C012, C014, C018, C019)

Derived from `contract.py` (the supplied binding contract), **not** from the
absent MASTER.md. Each id maps to code and tests.

| ID | Requirement | Code | Test |
|---|---|---|---|
| WH-R01 | The system SHALL refuse instantiation when any feature in REQUIRED_HARDENING is inactive. | runtime.Engine.check | RuntimeSecurityTest.test_every_required_feature_is_load_bearing |
| WH-R02 | The system SHALL NOT execute a module unless a receipt bound to its exact bytes, an approved toolchain and the full hardening profile verifies. | wasm_verify.verify_receipt, gateway | VerifierTest, CapabilityAndGatewayTest |
| WH-R03 | The system SHALL refuse structurally malformed Wasm binaries. | wasm_verify.parse_module | VerifierTest.test_malformed_modules_are_refused |
| WH-R04 | The system SHALL meter execution with fuel and trap stickily on exhaustion. | runtime.Instance.step | test_fuel_exhaustion_is_sticky |
| WH-R05 | The system SHALL cap linear memory at the engine ceiling and SHALL refuse modules whose declared max exceeds it or is absent. | runtime, gateway | test_environment_specific_memory_ceiling_is_enforced, unbounded memory case |
| WH-R06 | The system SHALL authenticate every caller and SHALL authorize each operation against an unexpired, unrevoked capability. | capability | CapabilityAndGatewayTest |
| WH-R07 | The system SHALL refuse any host function import not explicitly granted. | capability.check_imports | ambient import case |
| WH-R08 | The system SHALL refuse requests crossing the engine's tenant. | gateway | cross tenant case |
| WH-R09 | The system SHALL write an audit record for every admit and every refusal before an admitted instance becomes live. | gateway, audit_log | test_audit_write_failure_refuses_instantiation |
| WH-R10 | The system SHALL fail closed when clock, revocation or audit dependencies are unavailable. | capability, gateway | FaultInjectionTest |
| WH-R11 | Configuration SHALL be schema-valid, versioned, provenance-bearing, atomically activated and rollback-able. | config | ConfigTest |
| WH-R12 | The release gate SHALL be NO_GO unless every component is COMPLETE, every requirement verified, pk_core PASS and a human approval are present. | release_gate | ReleaseGateTest |

## Deployment contexts (C012)
| Context | Memory ceiling | Receipt max age | Network assumption |
|---|---|---|---|
| cloud / datacenter | per config (default 512 pages) | 24 h | revocation source reachable |
| near-edge | per config, lower | 24 h | intermittent |
| far-edge | per config, lowest | owner-set | may be absent |
Offline behaviour (C018): verification needs only local keys and bytes, so it
works offline; revocation and clock loss **refuse** (fail closed) rather than
admit. A far-edge deployment that needs offline admission must ship a signed
revocation snapshot with an explicit expiry — not implemented, owner decision.

## Outcome semantics (C014)
`success`, `degraded` (not currently produced), `retryable_failure`
(WH-OVERLOADED, WH-TIMEOUT, WH-CONFIG-CONFLICT, WH-DEPENDENCY-UNAVAILABLE),
`terminal_failure` (all others). See `errors.CODES`.

## Precedence when requirements conflict (C019)
1. Isolation and hardening completeness (never traded).
2. Security audit completeness.
3. Tenant residency.
4. SLOs (latency, throughput).
5. Cost.
A lower-ranked goal never relaxes a higher one; "run unhardened for performance" is a contract non-goal.
