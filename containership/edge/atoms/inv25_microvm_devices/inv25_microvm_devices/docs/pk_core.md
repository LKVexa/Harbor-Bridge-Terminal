# pk_core dependency (work item 1)

- **Distribution source:** PENDING owner decision (W-0006). pk_core is not in this archive. The
  package declares it as the optional extra `inv25-microvm-devices[pk]` with range `pk_core>=4.0,<5.0`
  (PROPOSED — the range must be confirmed against the real pk_core release history).
- **PK_CORE_PATH:** development only; refused when `INV25_RELEASE=1`.
- **Startup validation:** `pk_bootstrap.require_pk_core()` checks importability of
  `pk_core.checklist/component/contract`, required symbols (`ChecklistItem`, `Finding`, `Component`,
  `Contract`, `Dependency`, `Slo`) and the version range, and emits `PK_DEVICE_ERROR/1` on failure.
- The standalone modules (`model`, `errors`, `authz`, `audit`, `store`, `provenance`, `compat`) never
  import pk_core; the package imports cleanly without it and `COMPONENT` resolves lazily.
- CI job `pk-integration` runs `python -m pk_core list|run|gate|verify` once a source is declared.
