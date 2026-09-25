# Lifecycle state machines (M11)

Provider: `starting → ready | failed | stopped`; `ready ↔ degraded`; `ready|degraded → draining | disabled | failed | stopped`; `draining → stopped | disabled | ready`; `disabled → ready | stopped`; `failed → starting | stopped`; `stopped → starting`. Serving states: ready, degraded (degraded serves only the declared degraded op set).

Link: `pending → active | revoked`; `active → active (update) | suspended | draining | revoked`; `suspended → active | revoked`; `draining → revoked | active`; `revoked` terminal. Re-linking creates a new generation whose config_version is strictly above the tombstone.

Illegal transitions raise PK_PROVIDER_INVALID_LINK. Tested in `tests/test_runtime_units.py::Lifecycle`.
