# GAP-06 Audit Report - v4.2.0

Date: 2026-09-22  
Input version: 4.1.0  
Output version: 4.2.0

## Executive result

The supplied package was a compact reference scaffold, not a production device-attestation subsystem. Its central state machine had several trust-boundary weaknesses that could invalidate replay resistance or allow denial-of-service/trust-state mutation. Those defects were repaired and covered by standalone tests. Production hardware attestation, persistence, external schemas, distributed replay protection, HA, telemetry, and operational governance remain absent and are explicitly tracked in `MISSING_COMPONENTS.md`.

## Findings fixed or mitigated

| ID | Severity | Finding in 4.1.0 | 4.2.0 disposition |
|---|---|---|---|
| A-01 | Critical | Challenge nonce was deterministic from environment/node/time and truncated to 64 bits; repeated challenges at the same tick collided. | Replaced with 256-bit cryptographic randomness and uniqueness checks. |
| A-02 | Critical | `attest()` marked/popped a nonce before verifying that it belonged to the presenting node, allowing cross-node challenge burning. | Node ownership is checked before consumption; wrong-node evidence is side-effect-free. |
| A-03 | Critical | Measurement checks happened before challenge ownership, so self-chosen/unissued evidence could quarantine a node. | Challenge ownership is established before trust-state mutation. |
| A-04 | High | `hardware_rooted=True` alone granted hardware trust. | Mitigated in the reference model: hardware trust now also requires an enrolled matching hardware identity. Production cryptographic quote proof remains P0. |
| A-05 | High | No challenge expiry or outstanding challenge bound existed. | Added challenge TTL, expiry handling, pruning, and capacity ceiling. |
| A-06 | High | No enrollment/revocation state existed despite the documented `enrol` responsibility. | Added enrollment and revocation APIs; revocation invalidates verdicts/challenges. |
| A-07 | High | Evidence binding used ambiguous delimiter concatenation and only 128 bits of SHA-256 output; environment was not bound. | Canonical JSON, environment binding, and full SHA-256 are used. |
| A-08 | High | Caller-supplied logical time could move backwards and make an old verdict appear trusted again. | Stateful operations reject logical-clock rollback. |
| A-09 | Medium | Evidence accepted arbitrary lengths/counts, unsorted values, and duplicates. | Added type/size/canonicalization limits and duplicate rejection. |
| A-10 | Medium | Accepted measurement mutations were not version-reflected in verdicts. | Added measurement-set version state, atomic replacement, and versioned verdicts. |
| A-11 | Medium | Shared mutable sets/dicts had no synchronization. | Added an `RLock` around state mutations/reads. |
| A-12 | Medium | Core tests could not run at all without `pk_core`; the whole conformance class skipped. | Trust core is stdlib-only and independently testable; only framework tests skip. |
| A-13 | Low | README claimed `MASTER.md` was included, but the archive contained no such file. | Documentation corrected; artifact listed as missing. |
| A-14 | Low | Mutable verdict/evidence objects made accidental post-verification mutation possible. | Security value objects are frozen/slotted dataclasses. |

## Validation performed

- `python -m compileall`: PASS
- stdlib unittest discovery: 19 PASS, 2 SKIPPED (`pk_core` unavailable)
- security-core tests under `python -O`: 17 PASS
- package version pin: PASS (`4.2.0` in module and `VERSION`)
- JSON checklist parse: PASS (100 unique requirements expected by supplied manifest)

## Validation limitation

The archive does not contain `pk_core`, so the two framework-level tests that instantiate the 100-item component assessment cannot be executed in this isolated package. They remain present and will run when `pk_core` is supplied through the normal environment/`PK_CORE_PATH` path.

## Security boundary after this pass

The reference state machine now fails closed for challenge, replay, measurement drift, enrollment, hardware identity matching, expiry, and time rollback. However, matching a `hardware_identity` string is **not** equivalent to cryptographically verifying a TPM/TEE quote. Do not treat this package alone as a production attestation authority until the P0 items in `MISSING_COMPONENTS.md` are implemented.


## v5.0.0 addendum (2026-09-22)

The missing-components pass added `mc/` and found and fixed seven defects in its own work (listed in `CHANGELOG.md`). Evidence: `evidence/test_results.json`, `evidence/fuzz.json`, `evidence/bench.json`, signed (ephemeral key) `evidence/EVIDENCE_MANIFEST.json`. Nothing in this addendum is an independent audit: the same session built and checked the code.
