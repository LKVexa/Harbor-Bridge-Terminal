# Configuration Reference — `PK_GAP04_CONFIG/1` (C21, C23)

All durations are **integer seconds**. Unknown keys are rejected. Changes activate atomically via `ConfigManager.activate` (author ≠ approver, reason required, `config_version` must increase) and roll back via `ConfigManager.rollback`. Every change is restart-required for the node (the node validates its config at open and binds `config_version` to every decision). Lint/dry-run: `python -m gap04_disconnected_operation_controller.runtime.config <file.json>`.

| Key | Default | Safe range | Notes |
|---|---|---|---|
| `scope.*` | site-a/t0/c0/edge/prod | non-empty | must equal the lease scope exactly |
| `lease.max_lifetime_s` | 86400 | 60 … 604800 | local cap on accepted lease length |
| `tier_schedule` | [[0,full],[1800,sustain],[7200,freeze]] | starts [0,full], strictly increasing, narrowing only, last < lease max | replaces 4.2.0 constants 0/30/120 ticks |
| `max_policy_staleness_s` | 86400 | 60 … 2592000 | decisions refused beyond |
| `max_decisions_per_partition` | 10000 | 1 … 10^7 | size with CAPACITY_MODEL.md |
| `journal.max_bytes` | 64 MiB | ≥ 64 KiB | see capacity formula |
| `journal.reserve_bytes` | 1 MiB | ≥ 4 KiB, < max/2 | control/audit frames only |
| `journal.min_disk_free_bytes` | 16 MiB | ≥ 0 | decisions refused below |
| `clock.max_drift_s` | 30 | 1 … 3600 | anchor jump bound |
| `clock.tolerance_s` | 2 | small | rollback tolerance |
| `clock.persist_interval_s` | 10 | 1 … 60 | HWM persistence cadence |
| `clock.allow_rtc_after_reboot` | false | — | true caps authority at freeze |
| `reachability.up_after/down_after` | 3 / 2 | ≥ 1 | hysteresis |
| `reachability.flap_window_s/flap_threshold` | 300 / 6 | — | flapping ⇒ treated as partitioned |
| `admission.max_concurrency/max_queue` | 16 / 256 | 1…4096 / 0…10^6 | load shedding |
| `admission.retry_budget_percent` | 10 | 1 … 100 | GAP-05 retries |
| `overrides.two_person_required` | true | must be true in prod | |
| `overrides.max_ttl_s` | 86400 | 60 … 604800 | |
| `reconcile.batch_size/max_attempts` | 200 / 5 | ≤ 400 (frame bound) | |
| `quotas.decisions_per_minute` | 600 | — | reserved; not yet enforced (W-013) |

Dangerous values: disabling two-person control, a last tier threshold ≥ lease lifetime (freeze unreachable), reserve < 4 KiB (freeze cannot be recorded). All are rejected by validation.
