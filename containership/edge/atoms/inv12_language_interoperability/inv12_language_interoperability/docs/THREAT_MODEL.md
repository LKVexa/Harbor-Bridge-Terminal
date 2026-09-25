# INV-12 Threat Model (MC-051)

**Method:** STRIDE per trust boundary + abuse cases, each mapped to a control and to the test or gate that
proves it. Assets: component isolation, value integrity, resource ownership, configuration/mapping policy,
availability of the boundary.

## Trust boundaries

1. Guest linear memory and guest-returned pointers (untrusted).
2. Schemas / descriptors (untrusted input).
3. Host values supplied by a caller component (untrusted shapes, possibly hostile objects).
4. Control plane: configuration, mapping profile, artifact policy (trusted only after verification).
5. Trust layer: capability tokens, trusted time.

## Abuse cases → controls → evidence

| # | Threat (STRIDE) | Abuse case | Control | Evidence |
|---|---|---|---|---|
| T1 | Tampering / EoP | Malicious guest returns out-of-bounds, overflowing or misaligned pointer/length | `GuestMemory._check` order bounds→overflow→alignment; checked u32 arithmetic | `MaliciousMemoryTest`, corpus invalid vectors, `evidence/wasm_guest.json` |
| T2 | Tampering | Forged discriminant / flag bits / char / UTF-8 | lift rejects every invalid encoding | corpus `bad-*` vectors (all 4 languages) |
| T3 | DoS | Length bombs (huge list count, zero-size elements, 16 MiB+ strings, deep nesting) | `Limits`, `Budget`, zero-size guard, pre-work checks | `evidence/bench.json` DoS rows |
| T4 | DoS | Hostile schema (deep nesting, huge text) | schema limits, no recursion errors | fuzz `schema` target + regression seeds |
| T5 | EoP | Hostile host object runs code during copy (`__deepcopy__`, `__iter__`) | exact-type admission | `test_hostile_subclasses_refused` |
| T6 | Info disclosure | Payload/secret leaks via error text, metrics labels, spans | redaction, closed label vocabulary, span allow-list | `ErrorEnvelopeTest`, `ObservabilityTest` |
| T7 | Tampering | Aliasing: caller mutates after lower / receiver mutates shared value | detached copies both ways | `test_no_alias_across_boundary`, `test_detached_copy_no_alias` |
| T8 | Spoofing / EoP | Use of foreign, stale or duplicated resource handles (confused deputy) | per-table handles with generations; move semantics | `ResourceTest`, concurrency stress |
| T9 | Repudiation / Tampering | Borrow held past call; double drop; double post-return | `CallScope` revocation; lifecycle state machine | `test_leaked_borrow_fails_call`, `test_lifecycle_exactly_once_and_rollback` |
| T10 | Tampering | Hostile `realloc` returns overlapping/misaligned/out-of-range region | `CheckedRealloc` | `test_hostile_realloc_rejected`, wasm harness check 4 |
| T11 | Tampering | Downgrade of ABI/interface/profile during negotiation | highest-common + policy floors + transcript digest | `NegotiationEvolutionTest` |
| T12 | Tampering / EoP | Unapproved config or mapping profile activation, replay of old config | quorum HMAC approvals, increasing revision, pinned profile digest, audit chain | `ConfigTrustTest` |
| T13 | Tampering | Substituted binding/fixture/runtime artifact (compromised toolchain) | `ArtifactPolicy` digest+version pinning; SBOM | `test_artifact_provenance`, `evidence/artifact_policy.json` |
| T14 | Spoofing | Forged/expired capability token; missing trusted time | MAC/kid/exp/capability checks; fail closed | `test_capability_gate_and_outage_policy` |
| T15 | Tampering | Audit log edited, truncated, reordered | hash chain + HMAC | `test_audit_chain_detects_tampering` |
| T16 | DoS | Tenant exhausts shared capacity | fair-share admission | `test_health_and_capacity` |
| T17 | Tampering | Concurrent double-lift / double-move races | lock-guarded transfer, ordered two-table locks | `test_parallel_transfers_lends_and_drops` |

## Residual risks (accepted until closed)

* R1 No production Component Model runtime adapter (Wasmtime) — T1/T10 proven against the reference adapter
  and a V8-hosted Wasm guest only.
* R2 HMAC (symmetric) trust primitives — a compromised verifier key can forge approvals; target Ed25519/Sigstore.
* R3 x86-64 Linux is the only executed platform; ARM64/macOS/Windows are declared in CI but not yet run.
* R4 No sanitizers (ASan/Miri/`-race`) over native fixtures in this environment.
* R5 `pk_core` gate not executable here.
