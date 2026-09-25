# Runtime configuration (MC-08)

Schema: `schema/config.schema.json` (generated from `config.FIELDS`, `inv36.config/1`). Implementation: `config.py`.

- **Immutable vs mutable**: the wheel (code, schemas, IDL) is immutable; configuration is a mutable, versioned snapshot; runtime state (sessions, dedup window, quarantine) is separate (`recovery.py`, `quarantine.py`).
- **Secure defaults** (`config.DEFAULTS`): `prod` environment, https telemetry, `info` logging, 64 KiB frame ceiling, 256 sessions / 64 per tenant, 1 h session max age, all dev-only flags off. `dev_allow_insecure_test_keys` is DEV ONLY and refused in stage/prod; `debug` logging is refused in stage/prod.
- **Overlays**: `defaults < base < environment < site < node`; later layers win per key; `feature_flags` merge per flag. Result is independent of dict ordering (property-tested).
- **Secrets**: only `secretref://<env>/<name>` handles; namespace must equal `environment`; PEM blocks and secret-like field names are rejected.
- **Units/ranges**: every numeric field has explicit unit and range (see schema descriptions). Unknown fields are rejected.
- **Cross-field rules**: HWM > LWM; per-tenant sessions <= process sessions; retry cap >= base; stall threshold > 2 x heartbeat; handshake timeout plausible vs connect timeout; frame limit <= protocol maximum.
- **Activation**: `ConfigStore.activate(...)` validates, builds an immutable `MappingProxyType` snapshot, persists it `tmp -> fsync -> rename`, and swaps one reference - readers never see a partial mix. Authorized actors only; optimistic concurrency via `expected_version`. `validate_only()` is the dry run and reports which changed fields need a restart.
- **Hot reload**: fields with `hot_reload=True` in the schema description apply immediately; others (`environment`, `site`, `node`, `listen_port`, `peer_cid`, `max_frame_bytes`, `identity_key_ref`, dev flags) require restart/rehandshake.
- **Provenance**: version, digest, source, author, approval, activation time, scope - exposed via `Snapshot.provenance()` and the explain view; audited as `config.activate`.
- **Rollback**: bounded known-good history (`history_limit`); automatic rollback when a post-activation health check fails; operator rollback to a specific version; revoked digests are refused for activation and rollback (`config.rollback_denied`).
- **Crash safety**: `ConfigStore.recover()` discards a partial `.tmp`, verifies the persisted digest and re-validates values.

Golden profiles: `fixtures/golden_config.json` (minimum, typical, maximum, invalid). Tests: `tests/test_control_planes.py::ConfigurationTest`.
