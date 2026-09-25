# Technical-debt and deprecation register (MC-075)

| ID | Item | Kind | Owner | Exit criterion | Target |
|---|---|---|---|---|---|
| TD-1 | v1 API (`component.Toolchain`, `ToolchainRegister`, `PK_TOOLCHAIN/1`, `PK_TOOLCHAIN_SELECTION/1`) | deprecation | inv28-component-owner | No callers left. Remove in 5.0.0 | 5.0.0 |
| TD-2 | HMAC-only integrity (symmetric keys) | security debt | inv28-security-owner | KMS plus asymmetric signatures (D-005) | open |
| TD-3 | `schema_check.py` covers a JSON Schema subset | tooling | inv28-component-owner | Replace it with a full validator if a third-party dependency is ever accepted | open |
| TD-4 | Coverage via the stdlib `trace` module (line coverage only, no branch coverage) | tooling | inv28-component-owner | Branch coverage in CI once `coverage` is permitted | open |
| TD-5 | Catalog is example-only | product | inv28-register-owner | The owner registers `supported` entries with evidence | open |
| TD-6 | The selection cache key includes `now` to the microsecond, so hits need identical timestamps | performance | inv28-sre-owner | Decide a time quantum that stays safe with review, certificate and feed expiry | open |
| TD-7 | Pseudonym key is per process unless one is supplied | observability | inv28-sre-owner | Supply it from the KMS so pseudonyms correlate across instances | open |
| TD-8 | In-process threads contend on the CPython GIL. The 4-thread soak's throughput is below the single-thread baseline (see `evidence/SOAK_RESULTS.json`) | performance | inv28-sre-owner | Scale out across processes or replicas; the selector is stateless apart from its cache | open |
| TD-9 | Selection is O(entries): p99 at 1024 entries measured above the PROPOSED 25 ms (see `evidence/BENCH_RESULTS.json`) | performance | inv28-sre-owner | Pre-index entries by language and architecture while keeping the full elimination report, or approve a threshold based on reference hardware | open |
