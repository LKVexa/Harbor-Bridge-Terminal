# INV-35 Failure-Mode and Effects Analysis (C051, C055, C056, C058, C060)

Scale: Severity (S), Occurrence (O), Detection (D) 1–10; RPN = S×O×D. Approval: **PENDING**.

| # | Scope | Failure mode | Effect | S | O | D | RPN | Detection | Response / invariant preserved | Test |
|---|---|---|---|---|---|---|---|---|---|---|
| F01 | process | descriptor outside guest memory | host memory access | 10 | 6 | 1 | 60 | validation + `bounds_violations` | refuse E105, audit | fixtures, fuzz |
| F02 | process | chain loop / over-long | datapath hang | 8 | 5 | 1 | 40 | `chain_violations` | refuse E102/E103 | fixtures |
| F03 | process | lost wakeup | guest stalls | 8 | 3 | 3 | 72 | stall detector | force notify; NO_SUPPRESSION mode | concurrency, faults |
| F04 | process | crash mid-stream | reservations lost/duplicated | 8 | 3 | 2 | 48 | restart | journal replay; FROZEN on return; idempotency survives | faults |
| F05 | process | queue flood | host exhaustion | 7 | 6 | 2 | 84 | saturation, E200/E201 | depth + quota + breaker | T12 |
| F06 | VM | guest hostile/compromised | as F01–F05 | 10 | 5 | 1 | 50 | as above | quarantine queue | faults |
| F07 | node | key service outage | cannot authenticate | 9 | 2 | 1 | 18 | `dependencies.key_service` | fail closed E306, not ready | T09 |
| F08 | node | untrusted time | expiry unenforceable | 9 | 2 | 2 | 36 | `time_service` | fail closed E306 | T09 |
| F09 | node | backend failures | I/O errors | 6 | 4 | 2 | 48 | breaker state | open ⇒ E202; half-open probe | faults |
| F10 | site | control-plane partition | no orchestration | 6 | 4 | 2 | 48 | `control_plane` dependency | offline policy; datapath safety unaffected | PartitionTest |
| F11 | control plane | stale/duplicate controller | conflicting commands | 8 | 3 | 2 | 48 | epoch mismatch E307 | fencing | T17 |
| F12 | control plane | bad config pushed | unsafe limits | 9 | 3 | 1 | 27 | validation | refuse; active unchanged; rollback | ConfigTest |
| F13 | provider | vhost unavailable at site | slower path | 4 | 4 | 2 | 32 | `vhost_offload` | VMM-thread fallback, same semantics | profile |
| F14 | network | telemetry sink down | blind operations | 4 | 4 | 3 | 48 | scrape gaps (alert) | bounded buffers; never block datapath | T13 |
| F15 | supply chain | tampered artifact | arbitrary code | 10 | 2 | 1 | 20 | manifest digest | refuse promotion | verify gate |
| F16 | process | audit chain broken | lost forensics | 7 | 1 | 2 | 14 | `audit.verify()` | E505; SEV2 | T15 |

## Failover behaviour and invariant preservation (C055)

INV-35 is **host-local**: a queue lives on the host running its guest. Failover
therefore means (a) process restart on the same host — journal replay, queues
FROZEN until the owning controller (new epoch) resumes them; or (b) guest
migration to another host — the migration layer (INV-24) re-registers queues on
the destination; the source queue is DRAINING→STOPPED. Invariants preserved in
both: no descriptor accepted without validation, no reservation double-counted,
no idempotent request applied twice, quarantine never lifted implicitly.

## Degraded-operation modes (C056)

| Mode | Entered when | Behaviour | Exit |
|---|---|---|---|
| `no_notification_suppression` | suspected lost wakeups / stall alerts | every completion notifies | operator after root cause |
| `reduced_depth` | host pressure (operator/automation) | admission via lower `queue_depth` config | config rollback |
| `control_plane_unreachable` | partition | serve on last-good config; results carry E001 | restoration |

## Split-brain / duplicate owner / stale controller (C058)

Applicable. Protection: `Lifecycle.claim(epoch)` requires strictly increasing
epochs; every control command carries its epoch; mismatches are refused (E307)
and audited. Epoch source in production: the lease service that elects the
controller. Queues are single-tenant, so duplicate *tenant* ownership is refused
at registration (E305).

## Recovery objectives (C060)

| Fault | RTO (reference) | RPO | Verified by |
|---|---|---|---|
| KMS outage | first call after restore succeeds | n/a | `test_kms_outage_fail_closed_then_recover` |
| Backend fault storm | `breaker_cooldown_s` (1 s default) | n/a | `test_breaker_opens_and_half_opens` |
| Process crash | journal replay (32 records ≈ 0.2 ms ref.) + operator resume | 0 accepted chains lost | `test_crash_recovery_*`, bench |
| Partition | immediate DEGRADED; restore immediate | n/a | PartitionTest |
