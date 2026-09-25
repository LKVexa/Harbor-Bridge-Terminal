# Compatibility, deprecation and supported versions (MC-008, MC-017, MC-082)

## Policy (proposed — owner approval pending)
* Package: SemVer. Wire protocols: independent major versions per family (`PK_TOPO_GRAPH/1` …).
* Within a major: fields and error codes are never removed or re-purposed; new optional request fields are
  introduced behind a `FEATURES` flag that clients must list in `required_features` to use.
* Deprecation: announce in CHANGELOG, keep for **two minor releases or 180 days** (whichever is longer),
  emit `inv62_deprecated_use_total`, then remove only in the next major.
* Config: `schema_version` gates the config document; unknown keys are rejected, so a newer config cannot be
  silently half-applied by an older binary.
* State: `inv62-state/1` export format; WAL/snapshot readers refuse unknown formats (fail closed).
* Upgrade order: (1) roll new binary to canary site with old config; (2) verify gates; (3) roll fleet;
  (4) only then activate config using new keys. Downgrade: roll back config first, then binary.

## Supported-version matrix

| Component | Supported | Tested in this archive | Notes |
|---|---|---|---|
| inv62-edge-topology | 4.3.x | 4.3.0 | |
| CPython | 3.10 – 3.13 | 3.11.15 only | other versions: declared, NOT tested here (MC-073 partial) |
| PK_TOPO_GRAPH / NEAREST / PARTITION | v1 | v1 | |
| Config schema | 1 | 1 | |
| State format | inv62-state/1 | inv62-state/1 | |
| cryptography (optional) | ≥42,<47 | 46.0.7 | only for `encrypt_at_rest` and release signing |
| pk_core | pinned version TBD | **absent** | 100-item gate NOT RUN |
| wasmCloud host / NATS | TBD | **absent** | see `WASMCLOUD_PIN.md` |
| OS / arch | Linux, Windows, macOS; x86_64, arm64 | Linux x86_64 only | |
