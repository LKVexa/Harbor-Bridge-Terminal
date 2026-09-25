# PLN-04 compatibility matrix (PLN-04-C084, PLN-04-C093)

| Dimension | Supported | Evidence |
|---|---|---|
| CPython | 3.10, 3.11, 3.12, 3.13 | 3.11 executed in this build; floor asserted by `tests/test_governance.py`; CI matrix in `ci/pipeline.yml` (not executed here) |
| OS for process tier | Linux (POSIX rlimits, sessions) | executed on Linux x86_64 |
| OS for control plane | any CPython platform (flock is POSIX-only; single-writer protection absent on Windows) | declared |
| CPU arch | x86_64 executed; aarch64 declared | declared |
| Wasm runtime | wasmtime CLI with `-W max-memory-size`, `-W fuel` | declared (not installed here) |
| microVM / unikernel / VM | any `CommandProvider` driver speaking the JSON-stdio protocol | protocol tested with a Python driver |
| Schemas | PK_ADMISSION/1 (additive fields in 4.3.0), PK_TIER_CATALOGUE/1, PK_TIER_LIFECYCLE/1 (additive events/states), PK_PROVIDER_REQUEST/1 (new), PK_PLANE_CONFIG/1 (new) | `tests/test_units.py` |
| State format | PK_PLN04_STATE/2; migrates from /1 | `test_compaction_backup_restore_and_migration` |

Compatibility rule: within `/1`, fields and enum values may only be *added*. Consumers must ignore unknown lifecycle events. Removing anything requires `/2`.
