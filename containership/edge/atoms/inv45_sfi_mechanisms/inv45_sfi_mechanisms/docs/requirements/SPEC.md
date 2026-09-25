# INV-45 normative requirements specification

**Document id:** INV45-SPEC · **Version:** 1.0.0 (component 4.3.0) · **Status:** DRAFT — pending review by the
accountable owners named in `OWNERSHIP.md` (all roles currently UNASSIGNED).
Key words MUST/SHALL, SHOULD and MAY are used as in RFC 2119. Every `S-*` id is stable, is mapped in
`requirements/requirements.json`, and is checked by `tools/rtm.py` against code symbols and tests.

Covers C011–C019 and is the normative source for C014/C015/C016/C017/C018/C019 semantics.

## 1. Scope and source function (C011)

Source function: *strengthen multi-tenant Wasm execution*. It is translated into five measurable
security properties:

| Id | Requirement | Verification |
|---|---|---|
| S-SEC-01 | Memory confinement: every linear-memory load/store of an accepted module SHALL access only bytes in `[base, base + 2^k + 8)` of its tenant partition. | V8 canary tests `EngineEndToEnd`, escape fuzz, verifier unit tests |
| S-SEC-02 | Verifier completeness: the verifier SHALL accept a memory instruction only when the canonical mask sequence or a statically confined constant address immediately precedes it; any other form SHALL be `SFI_UNMASKED_ACCESS`. | `RewriteVerifyTest`, `ConstantFoldTest`, fixtures |
| S-SEC-03 | Control-flow confinement: indirect calls SHALL be confined to the module's own non-imported, non-exported, non-growable table; direct branches are structured by Wasm validation. | `ProfileAndPolicyTest.test_permitted_indirect_targets`, policy fixtures |
| S-SEC-04 | Fail-closed loading: the trusted loader SHALL execute nothing that is not bound by a valid sealed descriptor to the exact bytes, active profile, active config, tenant and version. | `T01`–`T08` security tests |
| S-SEC-05 | Tenant separation: no principal bound to tenant A SHALL submit, load, execute, quarantine-release or observe tenant B artifacts. | `T04_CrossTenantConfusedDeputy`, `T12` |

## 2. Functional requirements by deployment context (C012)

| Id | Context | Requirement |
|---|---|---|
| S-FUN-01 | all | The component SHALL rewrite (optional) and verify WebAssembly 1.0 binaries under profile `PK-SFI-WASM32-MVP-1` and SHALL reject every feature outside it with `SFI_UNSUPPORTED_FEATURE`. |
| S-FUN-02 | all | Verification SHALL produce a deterministic `PK_SFI_PROOF/1` whose digest is sealed into a `PK_SFI_SEALED_DESCRIPTOR/1`. |
| S-FUN-03 | cloud / datacenter | Multiple tenant modules MAY share one imported linear memory; each SHALL receive a disjoint partition plus guard. |
| S-FUN-04 | near-edge | The component SHALL operate with the control plane disconnected for up to `trust.trust_max_age_seconds` (see §7). |
| S-FUN-05 | far-edge | Far-edge nodes with < 64 MiB RAM or without a Node ≥ 20 engine are **N/A — unsupported** (ASSUMPTIONS.md U-07); preflight SHALL report `ok: false`. |
| S-FUN-06 | all | Operators SHALL be able to quarantine (freeze/disable) a global, tenant or artifact scope at runtime. |

## 3. Non-functional requirements (C013)

| Id | Property | Target | Status of target |
|---|---|---|---|
| S-NFR-01 | Verification latency | small module p99 ≤ 10 ms; 10k-function module p50 ≤ 3 s | PROPOSED (thresholds.json PERF-05/06) |
| S-NFR-02 | Runtime overhead | ≤ 15 % p50 (contract SLO) | **Not met on the worst-case load-bound microbenchmark (≈36 %)**; met on compute-mixed (≈0 %). See PERFORMANCE.md |
| S-NFR-03 | Determinism | Same input bytes + profile SHALL yield byte-identical rewrite output and proof | Enforced (fixtures drift test) |
| S-NFR-04 | Availability | Health SHALL distinguish ready / degraded / quarantined / dependency_stale | Enforced |
| S-NFR-05 | Recovery | Restart SHALL restore quarantine, anti-rollback floors, config generation and audit chain with no ephemeral trust (instances) resurrected | Enforced (FM05) |
| S-NFR-06 | Isolation strength | Security invariants have **no error budget** (never traded for availability or cost) | Normative |

## 4. Result classes (C014)

| Class | Meaning | Codes |
|---|---|---|
| success | operation completed; artifacts bound | — |
| success-with-warning | completed; non-security information recorded (e.g. custom sections stripped) | `RewriteResult.stripped_custom_sections` |
| degraded-but-safe | service running with a non-critical dependency impaired; no new trust from impaired inputs | health `degraded` |
| retryable failure | transient; caller MAY retry with backoff+jitter | `retryable: true` in ERROR_CATALOG.md |
| terminal policy rejection | deterministic; MUST NOT be retried unchanged | categories `security`, `policy` |
| malformed artifact | bytes are not valid Wasm | `SFI_MALFORMED_ARTIFACT`, `SFI_INVALID_MODULE` |
| unsupported artifact | valid Wasm outside the profile | `SFI_UNSUPPORTED_FEATURE`, `SFI_UNSUPPORTED_VERSION` |
| internal failure | invariant broken; fail closed | `SFI_INTERNAL_INVARIANT` |

S-RES-01: every public negative path SHALL raise `SfiError` with a registered code (fuzz invariant 1).
S-RES-02: partial success is not permitted for trust decisions: a submit either returns a sealed descriptor or no descriptor.

## 5. Lifecycle (C015)

`DISCOVERED → VALIDATED → VERIFIED → SEALED → LOADED ⇄ RUNNING → STOPPED`, with `REJECTED` reachable from the
first four states and `QUARANTINED → STOPPED` reachable from SEALED/LOADED/RUNNING. The table is
`production/controls.py::TRANSITIONS`.

S-LC-01: no state SHALL reach LOADED except through SEALED (checked exhaustively in `ControlsTest`).
S-LC-02: an illegal transition SHALL raise `SFI_ILLEGAL_TRANSITION`.

## 6. Versioning and compatibility (C016, C027)

S-VER-01: every schema, profile and descriptor carries an explicit id; peers SHALL require an exact
supported id and SHALL fail with `SFI_UNSUPPORTED_VERSION` otherwise (no negotiation; see COMPATIBILITY.md).
S-VER-02: error codes are append-only; a code SHALL NOT change meaning (pinned registry digest).
S-VER-03: anti-rollback floors SHALL refuse artifact versions below the highest version loaded per workload.

## 7. Offline / intermittent connectivity (C018)

S-OFF-01: with the control plane unreachable, cached trust material MAY be used until
`trust.trust_max_age_seconds` (default 3600 s, max 86400 s) after its last refresh.
S-OFF-02: after expiry, no new submit or load SHALL be granted (`SFI_TRUST_STALE`); health SHALL report
`dependency_stale`; already running instances continue (their trust decision was made while fresh).
S-OFF-03: reconnect (refresh) SHALL restore service without restart (`FM06_PartitionFromControlPlane`).

## 8. Capacity, quotas and fairness (C017)

S-CAP-01: global concurrency `admission.max_concurrent`, per-tenant `admission.max_per_tenant` (≤ global),
bounded wait queue `admission.max_queue`; excess is shed with retryable `SFI_OVERLOADED` (never queued
unboundedly). Per-tenant caps guarantee that one tenant cannot hold more than its share of slots.
S-CAP-02: parser/verifier work is bounded by `limits.*` before and during parsing (see INTERFACES.md §Limits).

## 9. Conflict precedence (C019)

When objectives conflict, precedence is: **1 security/isolation → 2 data residency → 3 correctness/determinism →
4 availability/SLO → 5 performance → 6 cost**. S-PREC-01: no optimisation, degraded mode or cost control SHALL
weaken S-SEC-01..05 (example: the C066 constant-fold optimisation is accepted only because the verifier re-proves it).
