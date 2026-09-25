# INV-35 Threat Model (C041, with C042–C050)

Method: STRIDE per boundary (`docs/architecture/BOUNDARY_INVENTORY.md`) plus the
mandated attacker classes. Approval: **PENDING** (security_owner). Every threat
has a mitigation in code and a test id in `tests/security/test_adversarial.py`
(T-xx) or another named suite.

## Attacker classes

| Class | Capability assumed |
|---|---|
| AC1 Malicious guest | full control of its ring contents, timing, and memory |
| AC2 Compromised vhost worker / VMM thread | holds a valid *bulk* capability for its queues |
| AC3 Rogue or stale controller | holds a valid control capability; may be partitioned or superseded |
| AC4 Malicious co-tenant | valid credentials for *its own* tenant |
| AC5 Network/on-path attacker on control channel | can replay, reorder, tamper captured messages |
| AC6 Supply-chain attacker | can tamper with release artifacts or config documents in transit |
| AC7 Insider with log/metric access | reads telemetry; tries to harvest secrets |
| AC8 Resource exhaustion attacker | any of the above, aiming at DoS |

## Threats and mitigations

| ID | STRIDE | Class | Threat | Mitigation | Test |
|---|---|---|---|---|---|
| T01 | E | AC2 | Bulk credential used for control actions (privilege escalation) | disjoint action sets; `_auth` on every entry point | T01 |
| T02 | I/T | AC4 | Cross-tenant submit, queue hijack by re-registration | tenant bound on capability + queue owner; duplicate registration refused | T02 |
| T03 | E | AC2 | Using a token beyond its queue scope | queue set in claims | T03 |
| T04 | E | all | Ambient authority (unauthenticated entry point) | every public method authenticates; reflection test | T04 |
| T05 | S/T | AC5 | Forged/tampered/non-canonical capability; foreign key | HMAC-SHA-256 over canonical claims; canonical-form check | T05 |
| T06 | S | AC5 | Replay of captured single-use capability | nonce LRU window (bounded) | T06 |
| T07 | S | AC5 | Expired/future tokens; cache used to bypass expiry | validity checked on every call, even cached | T07 |
| T08 | T | AC6 | Key compromise | rotation; retirement invalidates old tokens and flushes cache; ≥256-bit keys | T08 |
| T09 | D/E | all | Trust services fail and component fails open | fail closed E306; not-ready | T09 |
| T10 | T/E | AC1 | Descriptor points at host memory / outside regions (escape) | exact range check vs region union; wrap-around safe | T10, fixtures, fuzz |
| T10b | D | AC1 | Chain loop hangs datapath | visited-set + chain limit | fixtures |
| T10c | T | AC1 | TOCTOU: ring mutated during validation | snapshot + frozen descriptors | `test_chain_mapping_is_snapshotted` |
| T10d | T | AC1 | Slot shadowing via duplicate indices on the wire | duplicate slot ⇒ E101 | fixture `duplicate_slot_shadowing` |
| T11 | T | AC6 | Config injection: unknown fields, secrets, relaxing security fields | closed schema; secret-name detector; tighten-only fields; provenance digest | T11, ConfigTest |
| T12 | D | AC8/AC4 | Quota/queue exhaustion, noisy neighbour | tenant share + rate bucket + queue-count cap; rollback on refusal | T12 |
| T13 | D | AC8 | Telemetry cardinality explosion | 256 series/metric then overflow | T13 |
| T14 | I | AC7 | Secrets leaking into logs/audit/decisions | recursive redaction by field name | T14 |
| T15 | R/T | AC7 | Audit tampering, deletion, reorder | SHA-256 hash chain + per-entry HMAC | T15 |
| T16 | I | AC4 | Timing side channel on MAC comparison | `hmac.compare_digest`; static test forbids `==` on MACs | T16 |
| T17 | T/E | AC3 | Stale/duplicate controller (split brain) | monotonically increasing epoch; stale commands refused | T17 |
| T18 | D | AC1 | Lost wakeup via suppression | pending ⇒ notify; stall detector; NO_SUPPRESSION mode | concurrency, faults |
| T19 | T | AC6 | Tampered release artifact | manifest digests verified by gate | `verify.py` |
| T20 | I | AC4 | Microarchitectural side channels across guests | **out of scope**: INV-43 owns mitigations (optional peer) | documented |

## Residual risks (tracked)

* Evidence sealing is HMAC with an operator-held key (TD-002 → Sigstore).
* Keys are in-process in the reference model; production must bind `KeyRing` to an HSM/KMS (`CRYPTO_AND_KEY_POLICY.md`).
* Real hypervisor/backend conformance is not exercised in this repository (WVR-002).
