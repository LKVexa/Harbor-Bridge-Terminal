# INV-25 requirements and semantics (C011–C019, C032, C065)

## Functional (testable)
| ID | Requirement | Test |
|---|---|---|
| F1 | Only `paravirtual` devices may be catalogued; forbidden and unknown classes fail closed | `DeviceModelTest`, `FuzzTest` |
| F2 | Every entry declares its guest-visible registers, a rationale and a reviewer | `ErrorContractTest` |
| F3 | A changed entry can only enter through `replace()` with a new version, returning a surface diff | `DeviceModelTest` |
| F4 | Catalogue changes are proposed, independently approved and CAS-activated | `ActivationTest` |
| F5 | Runtime can attach only catalogued, non-disabled devices | `IntegrationContractTest` |
| F6 | Contexts: cloud / datacenter / near-edge / far-edge run the same pure-Python package; far-edge sites may carry a narrower environment catalogue and may lack a backend (runtime must refuse, never substitute) | `IntegrationContractTest.test_missing_backend_is_terminal_not_substituted` |

## Non-functional
- **Determinism:** identical canonical content ⇒ identical `sha256` digest (`ActivationTest.test_digest_semantics`).
- **Consistency:** readers observe a complete old or new catalogue (`ConcurrencyTest`).
- **Durability:** commit point is an fsync'd atomic file replace (`PersistenceAndFaultTest`).
- **Latency:** budgets in `conformance/performance/thresholds.json`.
- **Availability:** reads continue from last-known-good when dependencies fail; mutations stop.

## Outcome semantics (C014)
| Outcome | Meaning | Signal |
|---|---|---|
| success | candidate activated / query answered | activation record |
| partial success | not permitted — a candidate is all-or-nothing | — |
| degraded | dependency or audit sink down: reads OK, `ready=false`, mutations refused | `health()` |
| retryable failure | `retryable: true` codes (`CONCURRENT_MODIFICATION`, `RATE_LIMITED`, `DEPENDENCY_UNAVAILABLE`, `AUDIT_UNAVAILABLE`) | `PK_DEVICE_ERROR/1` |
| terminal failure | all other codes — do not retry unchanged | `PK_DEVICE_ERROR/1` |

## Lifecycle (C015)
Candidate: `proposed → approved → activated` (or discarded). Catalogue version: `active → superseded →
(rollback target) → active`. Device: `catalogued ⇄ emergency-disabled`. Illegal: activate unapproved,
self-approve, activate on stale base, roll back to an unrecorded digest.

## Intermittent connectivity (C018)
The package performs no network I/O. When the policy engine / audit sink / identity provider is
unreachable the store fails closed for mutations, and the runtime keeps using the last activated
catalogue. No offline mutation queue exists by design.

## Precedence (C019)
Security > residency > correctness > SLO > cost. A policy denial overrides catalogue presence;
catalogue absence overrides any policy allow (policy may narrow, never expand).

## Immutable vs mutable (C032)
Immutable: package code, schemas, activated catalogue snapshots (content-addressed by digest).
Mutable: active pointer, pending candidates, disabled-device set, audit log (append-only).

## Serialization/copy review (C065)
Candidates deep-copy one catalogue document (≤ 1 MiB by ceiling); canonical JSON is computed once per
digest. Measured costs in `evidence/benchmarks/`. No avoidable network hops exist (in-process library).
