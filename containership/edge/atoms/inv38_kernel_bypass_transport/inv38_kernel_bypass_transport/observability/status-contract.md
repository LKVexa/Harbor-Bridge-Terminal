# Health/status contract (INV-38-C071)

`status.py` renders a secret-free health/status snapshot bound to one lifecycle
`generation`: liveness vs readiness (separated so orchestration does not restart
healthy-but-degraded processes), version/build/config digests, backend, dependency
freshness (identity/policy/key/time/pk_core/telemetry), active capability set
(including whether kernel fallback is active), and a resource/saturation summary.
Schema: `observability/health.schema.json`. Tests: `tests/test_status.py`.
**Status:** `DONE`.
