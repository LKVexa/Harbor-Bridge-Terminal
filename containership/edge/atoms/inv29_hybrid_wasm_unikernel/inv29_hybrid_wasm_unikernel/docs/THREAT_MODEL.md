# INV-29 Threat model (INV29-MC013)

Method: STRIDE per trust boundary (see `docs/ARCHITECTURE.md`). Each threat maps to a mitigation in code and to the test that proves it. Residual risk is stated honestly; items needing external components are marked.

## Assets

A1 the two-layer invariant · A2 import closure · A3 tenant isolation · A4 integrity of composition records · A5 signing/attestation keys · A6 evidence ledger and gate verdict · A7 availability of admission.

## Actors

Malicious tenant workload · compromised/misconfigured upstream signer · network attacker between INV-29 and PLN-04 · careless operator · insider with repo write access.

## Threats → mitigations → evidence

| ID | STRIDE | Threat | Mitigation | Evidence (test) | Residual |
|---|---|---|---|---|---|
| T1 | Tampering | Composition silently reduced to Wasm-only (unikernel misconfigured) | `compose()` refuses unless both layers verify; `sealed` must be attested, the boolean alone is not trusted | `test_model::test_either_layer_failure_refused`, `test_admission::test_boolean_alone_is_not_trusted` | Real INV-27 signer integration BLOCKED_EXTERNAL |
| T2 | Elevation | Module import satisfied by escape hatch outside the host image | Import closure; denylist on imports and host exposure | `test_admission::test_denylisted_import_refused_even_if_exposed`, `test_host_exposing_denylisted_capability_refused` | Denylist content needs owner review |
| T3 | Tampering | Capability with drifted signature linked by name | typed link check (local + INV-11) | `test_interfaces::test_breaking_cases`, `test_admission_enforces_typed_link_in_addition_to_names` | INV-11 authority BLOCKED_EXTERNAL |
| T4 | Spoofing | Attestation for a different artifact reused | attestation subject must equal admitted digest | `test_admission::test_attestation_for_other_artifact_refused` | — |
| T5 | Spoofing | Forged / relabelled / unknown-key / revoked-key attestation | HMAC verify, claim match, keyring revocation | `test_forged_mac_refused`, `test_swapped_claims_refused`, `test_unknown_and_revoked_key_refused` | HMAC is symmetric: verifier can forge. Asymmetric signatures required for production — BLOCKED_EXTERNAL (MC049/MC050) |
| T6 | Repudiation / replay | Old admission replayed; stale evidence reused | nonce guard, TTL, attestation age, future-skew | `test_replay_refused`, `test_stale_and_future_attestations_refused`, `test_concurrency::test_same_nonce_admitted_exactly_once_under_race` | Replay cache is per-process |
| T7 | Tampering | Record modified between INV-29 and PLN-04 | signed record, schema, expiry; PLN-04 must `verify_record` | `test_record_tamper_and_expiry_detected`, `test_properties::test_admission_signatures_bind_every_field` | PLN-04 adoption BLOCKED_EXTERNAL |
| T8 | DoS | Oversized / deeply nested / hostile input | size, depth, count, length limits; fuzzing | `test_records::test_parser_hostile_inputs`, `test_fuzz` | — |
| T9 | DoS | Replay cache exhaustion | bounded cache refuses when full (fail closed) + alert | `test_replay_cache_saturation_fails_closed` | Availability loss by design |
| T10 | Info disclosure | Secrets in logs/metrics/exports | `records.redact`, keyring repr, label sanitiser, cardinality cap | `test_telemetry::test_structured_logs_are_json_and_redacted`, `test_cardinality_cap`, `test_keyring_never_leaks_material` | — |
| T11 | Tampering | Stored state / backup / ledger edited | per-document digest, backup manifest digest, hash-chained ledger | `test_lifecycle::test_store_integrity_check`, `test_tampered_backup_refused`, `test_evidence::test_ledger_chain_and_tamper_detection` | Not signed at rest (keys are OWNER_ACTION) |
| T12 | Elevation | Policy silently rolled back to a weaker generation | `set_policy` monotonic; rollback is explicit + audited | `test_emergency_disable_and_policy_monotonicity` | — |
| T13 | Elevation | Gate verdict asserted by prose | `derive_gate` computes verdict; P0 un-waivable; stale manifest blocks | `test_evidence::*` | — |
| T14 | DoS | Upstream dependency hang/crash turns into allow | adapters: timeout, bounded retry, breaker; states ≠ AVAILABLE refuse | `test_deps::test_fault_modes_fail_closed`, `test_circuit_breaker_opens_and_recovers_after_partition` | — |
| T15 | Layer confusion | Relying on the sandbox for isolation the hypervisor gives | composition record names the guarantee each layer contributes; single-layer is a different tier | `component.py::assess_architecture` | Needs pk_core to execute |
| T17 | Tampering | Type confusion: subclasses of frozenset/str/model classes lying to set/equality operations | exact built-in type checks on every trust-relevant input | `test_regressions_review::R1*`, `R2` | — |
| T18 | Tampering | Restore of an old backup resurrecting revoked work | terminal states never downgraded on restore | `test_regressions_review::test_N2_restore_cannot_resurrect_revoked` | backup digests unkeyed until owner keys exist |
| T16 | Elevation | Telemetry hook failure changes a decision | hook exceptions swallowed after the decision | `test_decision_hook_failure_cannot_change_outcome` | — |

## Out of scope
Hypervisor escapes, Wasm runtime JIT bugs, side channels between co-resident tenants, and unikernel toolchain compromise belong to INV-27 / INV-44 / the hypervisor owner. INV-29's job is to refuse compositions that lack their evidence.
