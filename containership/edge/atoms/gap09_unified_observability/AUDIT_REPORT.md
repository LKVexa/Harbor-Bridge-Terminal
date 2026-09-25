# GAP-09 Unified Observability - Audit Report

**Input version:** 4.1.0  
**Hardened version:** 5.0.0  
**Audit date:** 2026-09-22

## Executive result

The uploaded 4.1.0 package had a useful latest-value reference store, but it could not substantiate its own production trust claims: `signed=True` and a caller-supplied attestation-level string were accepted as proof. Its test suite also returned `OK (skipped=3)` when `pk_core` was absent, leaving the runtime itself untested in that environment. The package furthermore advertised a `MASTER.md` file that was not present.

Version 5.0.0 separates the runtime from optional orchestration, introduces a verifier-backed production ingestion path, hardens validation/state handling/resource bounds, adds standalone tests and interface schemas, and documents what is still missing. The major version bump is intentional because the secure production trust path is a behavioral/API boundary change.

## Defects found and fixed

1. **Caller-asserted trust:** booleans/strings were treated as attestation/signature proof. Fixed with `submit_verified` + `TrustVerifier` + scoped `ReporterAuthority`; legacy trust is disabled by default.
2. **No reporter scope authorization:** any accepted reporter could attribute data to arbitrary tenants/environments/sites/workloads. Fixed with per-authority scope checks.
3. **Environment boundary omitted from runtime keys:** the contract declared environment scoping, but `Sample`/storage/query keys did not contain an environment dimension, allowing same-named workloads across environments to collide. Environment is now mandatory and part of authorization, storage and query attribution.
4. **Replay ambiguity:** submissions had no stable replay identifier. Added bounded `(reporter, submission_id)` replay detection.
5. **Equal-timestamp overwrite:** `>=` let a different value overwrite an existing value at the same timestamp. Exact same-reporter duplicates are now idempotent; value/reporter conflicts fail closed.
6. **Reporter provenance loss:** accepted values retained attribution but not the verified reporter/submission that supplied them. Latest records now preserve reporter, submission ID and receive time; query responses repeat all attribution dimensions.
7. **Public mutable state:** callers could mutate `latest` / `last_submission` directly and bypass ingestion controls. Internal state is now private and exposed only through immutable snapshots.
8. **Empty batch liveness spoof:** an empty accepted batch refreshed `last_submission`. Empty batches are now refused.
9. **Unsafe numeric domain:** NaN was rejected, but infinities and arbitrarily huge integers were accepted; the latter could also trigger conversion/serialization failures. Values are now finite, non-boolean and bounded to binary64 magnitude.
10. **Weak runtime type/identifier validation:** annotations were trusted at runtime and identifiers could contain problematic control/format or non-normalized Unicode. Added type, length, NFC and control-character validation.
11. **Unbounded iterable materialization:** converting arbitrary submissions directly to a tuple could exhaust memory on a very large/infinite iterable before the batch limit was checked. Materialization is now capped at `max_batch_size + 1`.
12. **Unbounded envelope fields:** signature and attestation containers had no store-level limits. Added configurable signature-size and attestation-field bounds.
13. **Unsafe time domain / regression:** reads could produce negative age if caller time moved behind the stored sample; sample time could postdate envelope issue time; negative/pathologically huge integer timestamps were not bounded. Timestamps are now constrained to non-negative signed-64-bit range and ordering violations fail closed as `InvalidTime`.
14. **Expiration-edge ambiguity:** attestation remained valid at its exact expiry instant. Expiry is now enforced at `now >= expires_at`.
15. **Config inconsistency:** reads used global `STALENESS_BOUND` while reporter silence used instance configuration. Reads now honor `SignalStore.staleness_bound`.
16. **Unbounded memory growth:** signal keys, reporters, rejection history and replay state were unbounded. Added explicit limits and bounded histories.
17. **Rejection-log amplification:** invalid reporter values could be retained verbatim in the rejection log. Rejection labels are now bounded/sanitized.
18. **No concurrency guard:** shared state had no synchronization. Added an `RLock`, transactional staged commits and a concurrent newest-timestamp regression test.
19. **Ambiguous error surface:** failures were mostly generic built-ins. Added stable `SignalError.code` values and machine-readable details, including `trust_unavailable`.
20. **Missing internal observability:** isolation denials and ingest/rejection/resource state were not counted. Added metrics snapshot counters/gauges.
21. **Runtime coupled to orchestration:** importing the package failed without `pk_core`. Core runtime is now independent; `pk_core` glue is optional at import time.
22. **False-positive test posture:** all uploaded tests skipped without `pk_core`. Added standalone runtime regression coverage that actually executes in this archive.
23. **Missing external schema artifacts:** interfaces were named but not represented as schemas. Added JSON Schema references for submission/query/catalogue and checked them against Draft 2020-12.
24. **Breaking query shape left on `/1`:** the hardened query adds required environment scope and provenance fields, so retaining the old protocol number would make compatibility ambiguous. v5 emits `PK_SIGNAL_QUERY/2`; the legacy `/1` shape is retained only as a migration schema.
25. **Checklist evidence mis-mapping:** behavioral evidence for zero/absence, out-of-order samples, unattributed samples and staleness had been written into unrelated checklist slots (for example configuration provenance/atomic update and resilience quarantine). The v5 overrides now only mark checklist items whose requirement matches the behavior exercised.
26. **README inconsistency:** documentation claimed `MASTER.md` was included, but the archive did not contain it. Corrected and tracked as missing.

## Verification performed

- Python stdlib unit discovery against the hardened tree: **34 discovered, 31 passed, 3 skipped only because `pk_core` is absent**.
- `compileall`/syntax compilation.
- Optimized-mode runtime tests (`python -O`) for standalone logic: **31/31 passed**.
- Draft 2020-12 meta-schema validation for all four JSON Schema artifacts.
- Archive path safety checks before extraction and before repackaging.
- Version consistency checks across `VERSION`, `__init__.py`, README and tests.

The `pk_core`-dependent 100-requirement conformance tests cannot be fully executed from this uploaded archive because `pk_core` is not present. That limitation is explicit; no full production-gate claim is made from skipped tests.

Authenticated query identity remains an integration requirement: the in-process `read()` method can enforce that a supplied caller tenant matches the requested tenant, but this archive has no network/query authentication adapter that proves who supplied that caller identity. That boundary is therefore listed as P0 rather than overstated as complete.
