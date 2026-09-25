# GAP-06 Threat Model (MC-15) — v5.0.0 reference

Status: **engineering draft, not independently reviewed.** Residual-risk owners and acceptance authorities are UNASSIGNED (see `governance/OWNERS.json`); no penetration test of a production architecture has been run because none exists.

## Assets
| ID | Asset | Where it lives in v5.0.0 |
|---|---|---|
| AS1 | Verdicts (node trust level + expiry) | `DurableStore` table `verdicts` |
| AS2 | Outstanding / consumed challenges | table `challenges` (`mc/replay.py`) |
| AS3 | Enrollment bindings (EK fp ↔ node ↔ AK) | tables `nodes`, `ek_binding` |
| AS4 | Active signed measurement policy | tables `policy_active`, `policy_history` |
| AS5 | Trust anchors / CRLs | `certchain.TrustStore` (in memory, supplied by operator) |
| AS6 | Service signing keys (audit, workload) | `keys.SoftwareKeyStore` (process memory) |
| AS7 | Audit ledger | `audit.jsonl` + externally anchored head |

## Trust boundaries
TB1 node ↔ verifier (network, mTLS in `mc/transport.py`) · TB2 operator/policy publisher ↔ verifier · TB3 verifier ↔ state store · TB4 verifier ↔ key custody · TB5 verifier ↔ enforcement peers (GAP-01, SCH-01) · TB6 disconnected site ↔ centre.

## Attacker classes
A1 remote unauthenticated · A2 authenticated malicious node · A3 compromised workload on an attested node · A4 malicious/compromised operator · A5 compromised policy approver (single) · A6 network adversary (relay, delay, replay) · A7 attacker with a copy of VM/vTPM state (clone) · A8 attacker with physical access to firmware.

## Threat → control → executable evidence
| ID | STRIDE | Threat | Control (module) | Executable evidence |
|---|---|---|---|---|
| TH01 | S | Forged quote with attacker key | AK signature over TPMS_ATTEST with enrolled key (`verifier`) | `VerifierTest.test_other_key_and_revoked`, `test_negative_vectors` |
| TH02 | R/T | Replay of a valid quote | single-use durable nonce (`replay.ChallengeBook`) | `ReplayTest.*`, `EndToEndTest.test_replay_idempotency_and_conflict` |
| TH03 | T | Replay after restart / restore | WAL persistence, restore generation floor | `ReplayTest.test_restart_does_not_reopen_replay`, `DurableStoreTest.test_snapshot_backup_restore_floor` |
| TH04 | S | Nonce theft / cross-node burning | nonce bound to node + audience, side-effect-free rejection | `EndToEndTest.test_other_node_cannot_attest_or_steal`, `test_unbound_evidence_cannot_quarantine` |
| TH05 | S | Relay / cuckoo | optional channel binding, duplicate-active-device detection | `VerifierTest.test_relay_channel_binding_and_duplicate_device` — **partial**: no TPM credential activation, no locality |
| TH06 | S | Cloned EK/AK | one active node per EK, one node per AK | `EnrollmentTest.test_clone_refused_until_revoked_and_replace` — **partial**: VM snapshot clones of the *same* node are not detectable without TPM counters from real hardware |
| TH07 | T | Event-log body tampering / type relabel | data-bound types verified, unknown types rejected, replay to PCRs | `EventLogTest.*`, `PropertyFuzzTest.test_random_mutation_never_trusted` |
| TH08 | T | Approved-but-vulnerable firmware | policy lists exact digests; SVN floor for TEE | `TeeAdapterTest.test_cases` — **gap**: no vulnerability feed tied to measurements |
| TH09 | D | Parser amplification | size/count caps before crypto, bounded reader | `tools/fuzz.py` → `evidence/fuzz.json`, `QuoteParserTest.test_truncation_every_offset` |
| TH10 | D | Resource exhaustion via challenges/principals | capacity ceiling, bounded LRU admission | `ReplayTest.test_capacity_audience_and_cross_node`, `AdmissionTest.*` |
| TH11 | E | Policy poisoning by one approver | M-of-N Ed25519 quorum, monotonic version | `PolicyTest.*` |
| TH12 | T | Policy rollback | version monotonicity; restore floor | `PolicyTest.test_rollback_env_staging` |
| TH13 | S | Poisoned CRL / rogue intermediate | CRL signature must verify to known CA; CA checks, pathLen | `CertChainTest.*` |
| TH14 | I | Secrets in logs/errors | `errors.redact`, audit redaction, telemetry redaction | `ErrorsSchemasTest.test_registry_and_redaction`, `AuditTest.test_redaction_and_unknown_type`, `OpsTest.test_telemetry` |
| TH15 | E | Cross-tenant / cross-site access, confused deputy | scoped principals, node may attest only as itself | `IsolationTest.test_scopes`, workload tenant checks |
| TH16 | R | Audit tampering / truncation | hash chain + Ed25519 per event + external anchor | `AuditTest.*` |
| TH17 | T | Wall-clock manipulation | TrustedClock: monotonic projection, skew poison, stale-sync refusal | `ClockTest.test_unsynced_skew_stale_monotone` |
| TH18 | T | TPM counter rollback / unsafe clock | ClockTracker per AK | `ClockTest.test_monotonic_counters` |
| TH19 | E | Stale replica writes after failover | lease + fencing token | `ReplayTest.test_lease_fencing` — single-store simulation only |
| TH20 | D | Enforcement peer outage leaves node schedulable | durable outbox, `enforced()` false until all acks | `OpsTest.test_quarantine_outbox_acks` |
| TH21 | I | Side channels in TEE adapters | — | **not analysed**: no real TEE adapter exists |
| TH22 | E | Break-glass misuse | — | **not implemented** |

## Residual risks (unowned — cannot be accepted by the builder)
R1 no real hardware vectors (TH01/05/06 proven only against a software attester) · R2 in-memory key custody (AS6) · R3 single-process store; no HA consensus · R4 idempotency rows unbounded (measured in `evidence/bench.json`) · R5 CPython cannot guarantee zeroization.

## Review triggers (15.13)
Any change to `mc/tpm.py`, `mc/verifier.py`, `mc/algorithms.py`, `mc/certchain.py`, `mc/schemas.py`, `mc/replay.py` or `mc/policy.py` requires this document to be re-reviewed; `tools/release.py` records this file's digest in the evidence bundle so a stale review is detectable.
