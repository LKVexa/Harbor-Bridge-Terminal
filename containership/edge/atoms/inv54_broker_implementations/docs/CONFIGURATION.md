# Configuration  (components 26-33)
- **Schema (26):** `config.DEFAULTS` + `validate()`; exported as `schemas/config.schema.json` (`inv54.config/1`). Sections: provider, tls, auth, limits, quotas, retry, retention, storage, telemetry, features.
- **Fail-closed activation (27):** `ConfigStore.stage()` refuses any config with problems; the `production` profile additionally requires TLS for networked providers, auth≠none, hostname verification, a non-reference provider and fsync≠never.
- **Overlays (28):** `apply_overlays(base, *overlays)` deep-merge in order; overlays cannot change the schema version. Shipped: `config/base.json`, `config/overlays/{dev,production-kafka,edge-durable}.json` (all validated by tests).
- **Provenance (29):** each commit records digest, version, author, source, activation time and previous digest (`provenance_log()`).
- **Atomic update (30):** stage → commit with compare-and-swap on the current digest; the activation hook runs before the commit is recorded, so a failing activation leaves the known-good config in force.
- **Rollback (31):** `rollback()` re-activates the previous committed config and records it as a new version.
- **Secrets (32):** only `secret://<provider>/<name>` references are accepted; inline secret-named values are rejected; `Secret` never renders; rotation via key rings; unavailable provider → fail closed.
- **Bootstrap (33):** `tools/bootstrap.sh`.
