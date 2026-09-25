# PLN-02 v4.2.0 → v4.3.0 overhaul report

**Work order:** `PLN02_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (39 MC items, 2026-09-23)
**Candidate:** `pln02_application_plane_v4.2.0_hardened.zip` (18 files) → v4.3.0
**Gate verdict:** **NO_GO** (all gate checks pass; not every item is IMPLEMENTED)

## Result
| Status | Count |
|---|---|
| IMPLEMENTED | 17 |
| PARTIAL | 15 |
| BLOCKED_OWNER | 4 |
| BLOCKED_EXTERNAL | 3 |

Tests: 88 (normal and `python -O`), 3 skipped (`pk_core` not supplied — reported, not counted as passes).
Fuzz: 10 seeds × 4 000 mutations per target clean after two defects were fixed. Perf (reference host):
resolve p99 8 ms at 200 components against the 500 ms contract SLO; full submit path p99 ≈ 8 ms at 20
components; 20 s soak memory growth < 2 KiB. Wheel builds byte-identically twice.

## Per-item disposition
| MC | Title | Status | Checklist ids | Open acceptance |
|---|---|---|---|---|
| MC-01 | Original master source archive | BLOCKED_OWNER | — | MASTER.md not supplied; recovery unresolved (recorded, nothing reconstructed). |
| MC-02 | ADR and accountable ownership | BLOCKED_OWNER | C009, C010 | ADR state is Proposed: approval by quorum not recorded.; Named owners are UNASSIGNED. |
| MC-03 | Normative requirements specification | PARTIAL | C011, C012, C013, C014, C015 | Spec awaits approval under ADR-PLN02-001. |
| MC-04 | Version policy, negotiation, compatibility | IMPLEMENTED | C016, C027, C093 | — |
| MC-05 | Capacity, quota, fairness, admission | PARTIAL | C017, C028, C054, C067, C069 | Quotas are per replica; estate-wide quota coordination needs a shared store. |
| MC-06 | Disconnected catalogue cache / GAP-04 | PARTIAL | C018, C048, C056, C089 | GAP-04 exercised through a lease mock only. |
| MC-07 | Constraint precedence and conflicts | IMPLEMENTED | C019, C055 | — |
| MC-08 | Traceability and acceptance record | IMPLEMENTED | C020, C090, C100 | — |
| MC-09 | OAM adapter | IMPLEMENTED | C011, C021 | — |
| MC-10 | WIT parser and type checker | PARTIAL | C021, C022, C027, C084, C085 | WIT subset only; no differential conformance against the reference wasm-tools parser (TD-003). |
| MC-11 | Boundary authentication and trust bootstrap | PARTIAL | C023, C044, C048 | Caller tokens implemented; node/peer mTLS and attestation belong to the hosting transport (external). |
| MC-12 | Capability entitlement / authorization | IMPLEMENTED | C024, C042, C046 | — |
| MC-13 | Timeout, cancellation, retry, idempotency | IMPLEMENTED | C025, C053 | — |
| MC-14 | Wire-level error schema | IMPLEMENTED | C026 | — |
| MC-15 | Adjacent-layer integration harness | PARTIAL | C030, C083 | All six peers are contract-faithful mocks; no live PLN-01/INV-65/PLN-03/SCH-01/INV-11/GAP-04. |
| MC-16 | Reproducible build and dependency lock | IMPLEMENTED | C031, C032, C040, C093 | — |
| MC-17 | Configuration, provenance, activation, rollback | IMPLEMENTED | C033, C034, C035, C036, C037, C038 | — |
| MC-18 | Secrets, encryption, key lifecycle | PARTIAL | C039, C047, C048 | KMS binding and encryption in transit/at rest are deployment-provided (external). |
| MC-19 | Threat model and adversarial plan | PARTIAL | C041, C050, C087 | Security review sign-off not recorded. |
| MC-20 | Ambient authority reduction / isolation | BLOCKED_EXTERNAL | C043, C046 | Profile written; no deployment attestation that it is applied. |
| MC-21 | Artifact signature, provenance, supply chain | PARTIAL | C045 | Default HMAC is symmetric (TD-002); SBOM/attestation generation runs only in unexecuted CI. |
| MC-22 | Tamper-evident audit ledger | IMPLEMENTED | C049 | — |
| MC-23 | Failure catalogue, health, stall detection | IMPLEMENTED | C051, C052 | — |
| MC-24 | Failover, split-brain, quarantine/freeze/disable | PARTIAL | C055, C058, C059 | Fencing is single-process per store root (TD-001); multi-process HA needs an external lease. |
| MC-25 | Revision store and durable lifecycle | IMPLEMENTED | C004, C032, C057, C095 | — |
| MC-26 | Tenant/environment/site context | IMPLEMENTED | C006, C046, C064, C073 | — |
| MC-27 | Provider catalogue client | IMPLEMENTED | C004, C021, C036, C044, C045, C051 | — |
| MC-28 | Provider selection and explain | IMPLEMENTED | C019, C076, C077 | — |
| MC-29 | Performance baseline and regression suite | PARTIAL | C061, C062, C063, C064, C065, C066, C067, C068, C069, C070 | Single reference host only; constrained-edge power/thermal (C068) not measured. |
| MC-30 | Runtime observability | IMPLEMENTED | C071, C072, C073, C074, C075, C076, C077, C078 | — |
| MC-31 | Telemetry governance, dashboards, alerts | PARTIAL | C079, C080 | Definitions only; not deployed to a monitoring backend. |
| MC-32 | Fuzz, property, concurrency, security tests | IMPLEMENTED | C081, C082, C085, C086, C087 | — |
| MC-33 | Fault injection, partition, reconnect | PARTIAL | C060, C089 | In-process fault injection only; no real network/site partition campaign. |
| MC-34 | Cross-platform / protocol CI matrix | BLOCKED_EXTERNAL | C084, C093 | Matrix defined (3 OS x 5 Python); only Linux/3.11 executed here. |
| MC-35 | Benchmark, soak, fleet-scale environment | BLOCKED_EXTERNAL | C088 | Short single-host soak only; fleet-scale environment not available. |
| MC-36 | CI/CD production gate and release evidence | PARTIAL | C070, C090, C100 | Gate is fail-closed and runs locally; pk_core full-estate run and signed attestation are external. |
| MC-37 | Canary, rollout, rollback, emergency disable | PARTIAL | C092, C096 | Controls exist and are tested; no production drill executed. |
| MC-38 | Support, vulnerability, incident, review governance | BLOCKED_OWNER | C091, C094, C097, C098, C099 | Policy written; no on-call owner, review or exercise evidence. |
| MC-39 | License, NOTICE, distribution policy | BLOCKED_OWNER | — | Owner chose to leave the licence unresolved; LICENSE records 'owner decision pending'. |

## Global rules applied
Fail-closed resolver and SHA-256 identity preserved · versioned public schemas · bounded parsing before
allocation · typed context · unknown semantics refused · no `assert` for validation (suite passes under `-O`) ·
secrets kept out of errors/logs/metrics · content digests on catalogue, config, revisions, evidence ·
canonical JSON everywhere a digest depends on it · atomic/fenced/idempotent durable mutations · degraded mode
never weakens authn/authz/signatures/residency · README claims match `TRACEABILITY.json`.

## What the owner needs to do to reach GO
1. Supply the original `MASTER.md` (MC-01) — or record an approved exception.
2. Approve ADR-PLN02-001 and fill named owners in `OWNERSHIP.yaml` (MC-02, MC-03, MC-19 sign-off).
3. Choose the licence (MC-39).
4. Stand up on-call, reviews and a first tabletop exercise (MC-38); run a rollout drill (MC-37).
5. Run the CI matrix and the release gate on real runners (MC-34, MC-36); deploy the isolation profile and
   attach attestation (MC-20); bind a KMS (MC-18); switch catalogue/artifact keys to Ed25519 (MC-21).
6. Exercise live peers and a fleet/partition campaign (MC-06, MC-15, MC-33, MC-35).
Items that cannot be closed can be carried as approved, time-bounded exceptions in
`docs/governance/registers/EXCEPTIONS.json` (`{{"mc", "approver", "expiry", ...}}`); the gate honours them.

## Chop-shop notes
No yard parts were pulled: the checklist is satisfied with stdlib code written for this package, so
`THIRD_PARTY_NOTICES.md` records no bundled third-party source.
