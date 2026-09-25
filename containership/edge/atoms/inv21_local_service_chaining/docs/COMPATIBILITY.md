# Supported-Version Compatibility Matrix (4.3.0)

| Dimension | Supported | Verified in authoring env | Notes |
|---|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 | all four, Linux x86_64 (full suite) | `requires-python >=3.10,<3.14` |
| CPU arch | x86_64, aarch64 (pure Python) | x86_64 only | aarch64 untested → GAP-029 residual |
| OS | Linux; macOS/Windows expected (stdlib only) | Linux only | |
| pk_core | pinned in `pyproject [tool.inv21.pk_core]` | **UNRESOLVED** | release gate fails until pinned |
| PK_LOCAL_CHAIN | /1 | yes | |
| PK_CALL_CONTEXT, PK_RESIDENCY, PK_CHAIN_DEPTH, PK_CAPABILITY, PK_CHAIN_ERROR, PK_CHAIN_CONFIG, PK_CHAIN_AUDIT | /1 | yes (golden fixtures) | |
| INV-20 / INV-10 / INV-16 / INV-13 / SCH-01 | interface as consumed (see `tests/test_adjacent_contracts.py`) | stand-ins only | real-package interop BLOCKED (GAP-028) |

**Rolling upgrades (N / N-1)**: 4.3 peers speak only PK_LOCAL_CHAIN/1; 4.2 had no wire protocol (sentinel tuple), so there is no N-1 wire peer. The 4.2 in-process API (`Chainer.call`, `capability_checker`, `remote_dispatch`, legacy handler signature) remains supported in development mode; `tests/test_runtime.py` (the unchanged 4.2 suite) is the N-1 API compatibility test.

**Downgrade**: 4.3 → 4.2 is supported for development-mode deployments only; production-mode deployments have no 4.2 equivalent (4.2 lacks authentication) — downgrade = quarantine.

**Unknown fields**: rejected at every public boundary (`additionalProperties: false`). Adding an optional field is a minor schema change; the peer must be upgraded first.
