# Configuration (MC-015) and secrets (MC-016)

- Schema: `PK_MICROVM_CONFIG/1`; base `config/base.json`; environment overlays `config/overlays.json`.
- Layering base → environment → site. Overlays may only **narrow** (`NARROW_ONLY` fields, device set).
- `ConfigStore.propose()` stamps author/revision/activation time; `activate()` persists atomically,
  notifies listeners, and **rolls back** if any listener rejects; `rollback()` re-activates the prior
  revision as a new revision (history is never rewritten); a stale revision is refused (`STALE_EPOCH`).
- Secrets: only `secret://name` references are permitted in config; inline values or secret-looking
  strings are refused (`forbid_inline_secrets`). Values are resolved at use time by a `KeyProvider`.
