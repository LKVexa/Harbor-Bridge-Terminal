# INV-68 failure taxonomy, health model, failover and distributed safety (MC-17, MC-19; C051, C052, C055–C058)

## Failure taxonomy
| Layer | Failure | Detection | Response | Evidence |
|---|---|---|---|---|
| component | defect (unexpected exception) | `INTERNAL` + correlation id, alert A01 | error to caller, log, freeze if unsafe | FUZZ oracle |
| component | invalid input | validation | `INVALID_REQUEST`/`PAYLOAD_TOO_LARGE` | unit + fuzz |
| process | crash mid-activation | restart re-verifies store | old or new config, never mixed | FAULTS F09 |
| process | stall (request exceeds `stall_after_s`) | `status().stalled`, live=false | orchestrator restarts process | `test_MC17_stall_detection` |
| VM/node | host loss (capacity shrinks) | next capacity snapshot | repack with new capacity | FAULTS F04 |
| site | site disconnected | capacity staleness | `STALE_CAPACITY` (or explicit capacity) | FAULTS F02/F03 |
| network | capacity source partition | breaker | `DEPENDENCY_UNAVAILABLE` → `CIRCUIT_OPEN`, degraded | FAULTS F01 |
| provider | inventory API wrong/future timestamps | skew bound | `STALE_CAPACITY` | service code |
| control plane | stale/duplicate controller | epoch + CAS + lock | `STALE_EPOCH` / `CONFIG_CONFLICT` | FAULTS F10, STRESS S4/S7 |
| storage | corrupt snapshot / torn journal | digest re-verification | fall back to last intact, degraded | FAULTS F07/F08 |
| security service | audit sink down | append failure | buffer + count; refuse policy changes | FAULTS F05/F06 |

## Health states (PK_PACK_STATUS/1)
`ok` · `degraded` (breaker open, stall, audit buffered, recovered config) · `frozen` · `not_ready`.
`live` = not stalled; `ready` = config active and not frozen. Detection windows: stall
5 s (configurable `stall_after_s`); breaker opens after 3 consecutive failures, probes
after 5 s; capacity staleness 60 s default. False-positive budget: a stall flag on a
legitimately long batch is bounded by `max_workloads` (20 000 workloads ≈ 0.1 s), so
5 s gives > 40× margin.

## Failover and degraded operation
One instance per site (contract). Failover = start a standby with the restored store
(RTO seconds, BACKUP_RESTORE.md) and a *higher* epoch; the old instance is fenced
for configuration changes. Packing itself is stateless and deterministic, so two
instances serving the same request produce identical results — duplicate serving is
harmless; conflicting *configuration* is what the epoch fence prevents.
Non-critical dependencies (audit for pack decisions, metrics) degrade visibly;
critical ones (config, capacity freshness, identity) fail closed.

Return to normal is automatic when the cause clears: the breaker closes after one
successful half-open probe; staleness clears with the next fresh snapshot; a stall
clears when the request finishes; `degraded` from a recovered config clears on the
next successful activation. `frozen` never clears automatically (operator unfreeze).

## Restart / replay
Restart reloads the verified config, the freeze marker and the audit head. Replayed
requests (same idempotency key) after restart recompute identical results; the
in-memory idempotency cache is not persisted (DEBT-002).
