# Failure modes and recovery (INV-40-C051..C060)

| Failure | Detection | Behaviour | Test |
|---|---|---|---|
| Primitive unavailable | HostProbe | refuse; ready=false | `test_no_software_fallback` |
| Provider transient | `PROVIDER_UNAVAILABLE` | bounded jittered retry | `test_transient_provider_failure_retried` |
| Provider persistent | consecutive failures ≥ threshold | circuit opens; half-open probe after reset | `test_breaker_opens_then_recovers` |
| Guest OS fails to start | `GUEST_START_FAILED` (terminal) | no retry; hypervisor destroyed | `test_guest_os_start_failure_is_terminal` |
| Footprint over ceiling | runtime refusal | hypervisor destroyed, no orphan | `test_footprint_breach_leaves_no_orphan` |
| Process crash | restart replays journal | running guests reconciled to stopped; leases released | `test_crash_restart_reconciles` |
| Torn journal write | CRC mismatch on last record | tail discarded, reported | `test_torn_tail_corrupt_middle_compact_backup` |
| Journal corruption before tail | CRC mismatch | hard error (cannot be a crash) | same |
| Overload | queue full | shed retryable | `test_admission_shed_and_quota`, bench burst |
| Controller partition | stale epoch | rejected | `test_split_brain_prevented` |
| Telemetry sink down | sink exception | degraded, counted | `test_telemetry_outage_is_degraded_not_fatal` |
| Identity/key/time down | exception | fail closed | `test_trust_services_unavailable_fail_closed` |
| Node / site loss | — | **failover not implemented**: guests on a lost node are not restarted elsewhere by this tier; placement (upstream) decides; isolation/residency preserved by refusing rather than relocating | BLOCKED (DIST-STORE, PROD-ENV) |

Health / stall thresholds (C052, PROPOSED): boot > `boot_budget_ms` ⇒ degraded; op latency p99 > `op_timeout_ms` ⇒ stall alert; breaker open ⇒ not ready; admission shed rate > 5 %/5 min ⇒ overload alert (`ops/alerts.json`).
Quarantine (C059): guest / tenant / tier scopes; tier scope needs a human admin.
