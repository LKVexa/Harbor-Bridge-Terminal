# Wasm runtime (INV-70-C031) — status: BLOCKED on engine install

| Item | Where | State |
|---|---|---|
| Engine choice + rationale | ADR-0001 | proposed |
| Exact pin | `requirements/wasm.lock` (`wasmtime==25.0.0`) | version pinned; **wheel hash UNSET** |
| Lock check in CI | `tools/check_lock.py` | fails while the hash is UNSET or any range operator is present |
| Per-operation model | `executor.WasmBackend.execute` | new Engine/Store per run → validate module → StoreLimits (memory, 1 table, 1 instance) → fuel → epoch deadline timer → link only `inv70.<cap>` imports that are granted and registered → call `run` → map traps → drop the store |
| WASI / ambient authority | none linked; any other import → `capability denied` | |
| Trap mapping | fuel → `out of fuel` (FB-R001), epoch → `deadline exceeded` (FB-T001), other → `guest trap`, bad module → FB-R016 | |
| Artifact gate | `security.verify_artifact` runs before compilation (C045) | verified |
| Compiled-module cache | **not allowed** in 4.3.0 (ADR-0001). A later cache would be keyed by module digest + engine version + config digest. | |
| Fail-closed | pinned engine missing or wrong version → `FB-I002` | verified |
| Tests | `tests/test_wasm.py`: loop, memory growth, WASI import, invalid module, OK | 5 SKIP here; FAIL under `INV70_REQUIRE_WASM=1` |

**To unblock:** install the pinned wheel on a CI runner, record its sha256 in `wasm.lock`, run with `INV70_REQUIRE_WASM=1`, then switch `backend` to `wasm` in the staging overlay.

**ABI (v1):** the guest exports `run: () -> i64`. Host capability imports are `inv70.<name>: (i64) -> i64`. A typed WIT world (`wit/inv70.wit`) comes with ABI v2. Until then, arguments and results are exact i64 and are checked on both sides.
