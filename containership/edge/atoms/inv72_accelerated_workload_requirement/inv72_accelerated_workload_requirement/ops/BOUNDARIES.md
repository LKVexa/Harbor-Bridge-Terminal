# INV-72 boundary inventory (C021, C023, C024)

Exhaustive list of the places data or control crosses into or out of INV-72. Anything not listed
here does not exist; `IDENTITY_INVENTORY.json` lists who may cross each boundary.

| # | Boundary | Direction | Schema / form | AuthN | AuthZ capability | Limits |
|---|---|---|---|---|---|---|
| B1 | `AcceleratorService.request` | in (GAP-11, INV-69) | PK_ACCEL_REQ/1 → PK_ACCEL_MATCH/1 | PK_ACCEL_TOKEN/1 (HMAC) | `accel.reserve` / `accel.match` + tenant scope | count ≤ 64, ids ≤ 128, deadline ≤ 60 s |
| B2 | `AcceleratorService.release` | in | reservation id + tenant | token | `accel.release` + tenant | — |
| B3 | operator controls (`quarantine`, `drain`, `disable`, `enable`) | in | args | token | `accel.operate` | — |
| B4 | `ConfigStore.activate` / `rollback` | in (operator tooling) | PK_ACCEL_CONFIG/1 | host (caller must hold `accel.config`) | author required | schema bounds |
| B5 | `status()` / `explain()` | out | PK_ACCEL_STATUS/1 / text | token for explain | `accel.read` | ring of 1000 |
| B6 | discovery intake `InventoryCache.refresh` | in (GAP-02) | PK_ACCEL_INVENTORY/1 | per-source HMAC | source registration | ≤ 4096 devices |
| B7 | key service `KeyProvider` | in (host identity) | key bytes + grants | host | — | fail closed |
| B8 | journal file | out/in (disk) | JSON lines, hash chain | filesystem ACL (host) | — | append-only |
| B9 | audit export | out | PK_ACCEL_AUDIT_EVENT/1 | host sink | — | buffer bound |
| B10 | metrics / logs | out | Prometheus text / JSON lines | host sink | — | series bound |
| B11 | pk_core conformance (`component.py`, `contract.py`) | in (test/gate time only) | pk_core API | n/a | n/a | — |
| B12 | legacy `match()` / `decide()` | in-process library | Python objects | none (library call; trusted caller) | none | same limits |

No WIT, RPC transport, hypervisor or device boundary exists in INV-72: transport is the host's, and
device/hypervisor access belongs to GAP-02/GAP-11 (README "Explicitly does not own").
