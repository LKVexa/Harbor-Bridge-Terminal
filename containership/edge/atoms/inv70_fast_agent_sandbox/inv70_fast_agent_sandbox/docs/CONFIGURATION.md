# Configuration (C035 overlays, C036 provenance, C037 atomic activation)

- **Layers:** `base` → `env:<dev|staging|prod|edge>` → `site:<name>`. The schema is closed and typed (`config.SCHEMA`). Unknown keys, wrong types, out-of-range values and cross-field violations are rejected.
- **Provenance record:** every activation stores `digest, previous, layers, environment, actor, reason, activated_at, overlay` in `ConfigStore.history` and writes `config.activated` to the tamper-evident audit log.
- **Atomicity:** the candidate is fully resolved and validated, then the optional precheck (canary) runs, then the audit record is written, and only after all of that is the active config swapped under a lock. Any failure leaves the active config and digest unchanged.
- **Rollback:** `rollback()` re-applies the previous record's stored overlay (last known good) and records a new activation.
- **Degraded control plane:** `ConfigStore.frozen` blocks activations while the sandbox keeps serving on the last known good config.
