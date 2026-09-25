# INV-63 State and Configuration

| Field | Value |
|---|---|
| Document ID | INV63-ARCH-STATE-CONFIG |
| INV-63 C-IDs covered | C032, C033, C034, C035, C036, C037, C057 |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Config admin (role), SRE lead (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when journal record kinds / config keys change. |

## 1. Three physically separate layers (C032)

| Layer | Location | Mutability | Contents |
|---|---|---|---|
| Immutable package | package dir (`*.py`, `schemas/*.json`, `pins.json`, `MANIFEST.sha256`) | read-only at runtime; never rebuilt per site (C035) | code, schemas, pins |
| Configuration | `deploy/config/base.json`, `deploy/config/env/<env>.json`, `deploy/config/site/<site>.json` | changed by config-admin via activation | `PK_DEPLOY_CONFIG/1` data |
| State | `<state_dir>/journal.jsonl`, `<state_dir>/epoch` | written only by the leader `Journal` handle | hash-chained records; fencing epoch |

`state_dir` is supplied by the operator (`tools/bootstrap.py --state-dir ...` creates it with mode 0700 and opens a sealed journal); it must not be inside the package directory (not enforced in code — open item).

## 2. Configuration (C033–C037)

- Composition: `config.compose(*layers)` = `SECURE_DEFAULTS` ← base ← env ← site (deep merge `_merge`), then `validate`. `config.load_layers(config_dir, environment, site)` reads the three files if present.
- Secure defaults (`SECURE_DEFAULTS`): `environment=prod`, `tier=cloud`, `require_signed_artifacts=true`, `require_encryption_at_rest=true`, `allow_unauthenticated=false`, `request_timeout_ms=5000`, `max_inflight=64`, `queue_depth=1024`, `offline_autonomy_s=3600`, `max_clock_skew_s=30`, `telemetry_sampling=0.1`, `stall_threshold_s=120`, `retry_max_attempts=4`, `circuit_failure_threshold=5`, `reconcile_interval_s=30`, `max_unavailable_default=1`.
- Validation order (`config.validate`): (1) secret scan `_scan_secrets` → `INV63-E-SECRET-IN-CONFIG` (paths only, value never echoed); `secret_refs.*` must start `env:`/`file:`; (2) schema `PK_DEPLOY_CONFIG/1` → `INV63-E-CONFIG-INVALID`; (3) prod: `SECURITY_CRITICAL` keys must hold their secure values; (4) far-edge: `offline_autonomy_s >= 300`; (5) `tenant_quotas.<t>.max_instances` non-negative int.
- Overlays shipped:

| File | Keys |
|---|---|
| `base.json` | `site=default`, `secret_refs` (`token_keys`, `data_key`, `lattice_creds` — all `file:/run/secrets/...`), `trusted_key_ids=["release-2026"]` |
| `env/dev.json` | `environment=dev`, `require_signed_artifacts=false`, `telemetry_sampling=1.0` |
| `env/staging.json` | `environment=staging`, `telemetry_sampling=0.5` |
| `env/prod.json` | `environment=prod`, `telemetry_sampling=0.05` |
| `site/dc-1.json` | `site=dc-1`, `tier=datacenter` |
| `site/edge-site-a.json` | `site=edge-site-a`, `tier=far-edge`, `offline_autonomy_s=86400`, `max_inflight=8`, `queue_depth=64`, `reconcile_interval_s=120` |

- Activation provenance (C036): `ConfigStore.activate(layers, author, reason)` returns `Activation(version, digest, author, activated_at, reason, previous_digest)`; `digest = config_digest(cfg)` = `sha256:` of canonical JSON (`sort_keys`, compact separators). When a journal is given, a `config_activated` record is appended.
- Atomicity (C037): candidate fully composed and validated before any change; swap is a single reference assignment (`self.active = candidate`). Failure leaves `active` untouched.
- Rollback: `ConfigStore.rollback(author, reason)` re-activates the previous candidate as a new version (`INV63-E-PRECONDITION` if none).
- Tested by `tests/test_platform.py::ConfigTest` (`test_secure_defaults_and_fail_closed_validation`, `test_secrets_rejected_in_config`, `test_environment_and_site_overlays_without_rebuild`, `test_provenance_atomic_activation_and_rollback`).

Gaps: `ConfigStore.history` is in memory; after restart the active config comes from re-composing files, not the journal. `DeploymentService` takes a plain `config` dict and does not hot-reload. `status()["config_digest"]` uses `config.config_digest`, so it equals `Activation.digest` for the same composed config. With `require_encryption_at_rest` the service refuses to start unless the journal has a `Sealer` (`INV63-E-CONFIG-INVALID`).

## 3. State journal (C057)

Record: `{seq, epoch, ts, kind, data, prev, digest}`; `digest = sha256(canonical({seq,epoch,ts,kind,data,prev}))`; `prev` of the first record = 64 zeros (`GENESIS`). `data` is replaced by an AES-256-GCM token when a `Sealer` is injected.

Record kinds written by `service.py`: `desired_set`, `lifecycle`, `control`, `host_quarantine`, `emergency_disable`, `offline_intent`, `resynced`, `idempotency`, `action_committed`, `rollout_batch`, `rollback`; by `config.py`: `config_activated`; by `Journal.compact`: `snapshot` (always seq 1). `desired_deleted` is replayed but never written in 4.3.0 (count 0 → lifecycle `DELETED`, the `desired_set` stays).

Crash consistency:
- Append = one `write` of a full line + `flush` + `os.fsync`; acknowledged only after fsync.
- Open (`_load`): lines verified in order (seq contiguous, `prev` chain, digest); a final line without `\n` is a torn write → truncated + fsync, `recovered_torn_tail=True`; any earlier fault → `INV63-E-STATE-CORRUPT`, refuse to start.
- Epoch: `acquire()` writes a temp file, fsyncs, `os.replace`s `epoch`, fsyncs the directory. `append` rejects if `epoch` changed (`INV63-E-STALE-EPOCH`) or file size changed underneath (`INV63-E-CONFLICT`).
- Replay: `DeploymentService._recover` loads a leading `snapshot` (`_load_snapshot`) if present, then rebuilds desired, lifecycle (`Lifecycle.restore`), controls, host quarantine, emergency disable, pending offline intents, idempotency cache; acquires a new epoch only if this handle's epoch is 0.
- Not persisted: `manager.actual` (re-observed from lattice), `DecisionLog`, metrics, traces, logs, breaker/admission state.
- Size: `max_bytes` = 256 MiB → `INV63-E-QUOTA` (message points to `compact()`).
- Compaction: `DeploymentService.compact()` = `Journal.compact(self.snapshot())`, leader only (`INV63-E-STALE-EPOCH`); writes one `snapshot` record (desired, lifecycle, controls, host quarantine, emergency disable, pending, last 10k idempotency keys, `_compacted.previous_head/previous_records`) to a temp file, fsync, `os.replace`, fsync dir. Prior history — including earlier `desired_set` versions used by `op_rollback` — is gone unless backed up first. Operator-triggered only.
- Durability relies on A-12 (fsync honoured); not qualified on any target storage.
