# INV-37 configuration, state separation and bootstrap

**Version:** 4.3.0 · Covers INV-37-C032–C040. Implementation: `config.py`; tests: `tests/test_config.py`.

## 1. Artifact / configuration / state separation (C032)

| Class | Location | Owner | Mutability | Lifecycle / backup |
|---|---|---|---|---|
| Release artifact (wheel) | site-packages, read-only | service_owner | immutable, identified by version + `source_digest` | replaced by upgrade; never written at runtime |
| Profile + site/env/node config | operator config root (e.g. `/etc/inv37/`) | sre_owner | changed only via activation | versioned in operator VCS; history in `config-history.json` |
| Secrets (key ring) | secret-manager-mounted file, mode 0600 | security_owner | rotated | never in config, logs, diagnostics or backups of config |
| Durable state (checkpoints, leases, quarantine) | `checkpoint.directory` (e.g. `/var/lib/inv37`) | sre_owner | runtime | see OPERATIONS.md §Backup; retention `checkpoint.retention` |
| Audit log | operator-chosen path | security_owner | append-only | ship to SIEM; retain per policy |
| Transient (regions, in-memory receivers, metrics) | memory / `/dev/shm` | runtime | ephemeral | lost on restart by design |

Preflight rejects a checkpoint directory inside the installed package (`state_in_package`); `CheckpointStore` refuses it too. Every persisted format carries a schema id: `INV37_CONFIG/1`, `INV37_CONFIG_PROVENANCE/1`, `INV37_CHECKPOINT/1`, `INV37_LEASE/1`, `PK_BULK_RESUME/2`, audit chain. `health()` reports version, artifact digest, config digest and policy digest together.

## 2. Declarative format and secure defaults (C033)

JSON, schema `INV37_CONFIG/1`, versioned independently of the package. Typed units: bytes `B|KiB|MiB|GiB|TiB`, durations `ms|s|m|h|d`. Unknown keys are rejected. No code execution. Defaults (`config.SCHEMA`) are production-safe: authentication required, fsync on, checkpointing on, 8 concurrent transfers, 1 GiB objects, 5 % trace sampling, telemetry export off. Example profiles: `config/profiles/{prod,edge,dev}.json`.

## 3. Layers and precedence (C035)

`built-in defaults < site < environment < node override`. The same artifact digest is promoted through dev/test/stage/prod by changing only layers. `limits.max_chunks` is not overridable by any layer; `security.require_authentication` and `checkpoint.fsync` are **invariants** — a layer may tighten but never weaken them. `load_file(..., root=…)` refuses paths escaping the approved config root. Render/validate without activating: `ConfigManager.dry_run(layers)` (returns effective config, findings, digest); `redacted()` hides secret paths for diagnostics.

## 4. Preflight validation (C034)

Deterministic and side-effect free. Findings are `fatal` (admission stays disabled; `BulkDataPlane` refuses to construct), `degraded` (e.g. `copy_fallback`), or `warning`. Fatal rules: non-positive limits, zero concurrency, worst-case memory > `host_memory_budget`, mapped > budget, inverted retry, authentication disabled outside dev/test, missing/unreadable/over-permissive key file, missing/unwritable checkpoint directory, state inside package, encryption required without provider, zero-copy/shm required without capability, file export without path, malformed tenants.

## 5. Provenance, atomic activation, rollback (C036–C038)

`ConfigManager.build()` records `{digest, profile, layers, author, source, package_version, created_at, activated_at, previous_digest}`. `activate()` swaps under a lock, runs the supplied health check, and **automatically restores the previous config** on failure (`auto_rollback`). `rollback(author=…)` is operator-driven. Every action (`activated`, `rejected`, `auto_rollback`, `operator_rollback`) is appended to `config-history.json` with an atomic write (tmp + fsync + rename + dir fsync). Config rollback is independent of artifact rollback.

## 6. Secrets (C039)

Keys named `*secret`, `*password`, `*token`, `*_key`, `*credential`, `*private` with non-empty values are rejected at load (`inline secret material is forbidden`); only `security.key_file` (a path) is permitted. Logs redact fields matching `payload|token|secret|key|password`; health reports limits but never key paths.

## 7. Deterministic bootstrap, empty node → healthy (C040)

```bash
python -m pip install inv37_bulk_data_plane-4.3.0-py3-none-any.whl          # 1 artifact
install -d -m 0700 /var/lib/inv37 /etc/inv37                                 # 2 state + config dirs
# 3 key ring from secret manager: {"keys":{"k1":"<64 hex>"},"active":"k1"}  mode 0600
python tools/bootstrap.py --profile config/profiles/prod.json \
    --site /etc/inv37/site.json --key-file /etc/inv37/keys.json --state-dir /var/lib/inv37
```

`tools/bootstrap.py` runs: capability probe → layer load → preflight (exit 2 on fatal) → activation with a live health check (constructs `BulkDataPlane`, runs `recover()`, checks `health().ready`) → prints effective (redacted) config, digest and health JSON. The same inputs always yield the same config digest.
