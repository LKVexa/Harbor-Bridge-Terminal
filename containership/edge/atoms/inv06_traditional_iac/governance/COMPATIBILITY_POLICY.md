# Compatibility and Version Policy (MC-007)

Status: **Draft.**

- **Semantic versioning.** MAJOR changes wire schemas (`PK_IAC_*/<n>`) or removes public functions; MINOR adds; PATCH fixes.
- **Schemas.** Every document carries `schema: NAME/<major>`. Readers accept exactly the majors they list and refuse others (`InvalidPlan`, `InvalidState`, `StateCorrupt`). Unknown fields in plans are refused (fail closed).
- **State migration.** `durable.migrate_snapshot` upgrades `PK_IAC_STATE/0` (4.1.x) → `/1`. A new major ships a migration and a downgrade note; downgrade across a state major is unsupported and refused.
- **Deprecation window.** Deprecated APIs remain for two MINOR releases or 6 months, whichever is longer, and emit a WARN log.
- **Peers.** INV-01/07/08 and GAP-13 documents are version-tagged (`PK_INV01_INVENTORY/1`, `PK_INV07_CHANGESET/1`, `PK_INV08_POOL_HANDOFF/1`, `PK_POLICY_DECISION/1`); mismatches are refused, never coerced.
- **Engine/provider versions.** Exact pins only (no `~>`/ranges); upgrading a pin is a reviewed change with a new evidence run.
