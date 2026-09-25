# INV-32 Failure, Degraded-Operation and Failover Model (v4.3.0)

Precedence: security/integrity > isolation/residency > state correctness > SLO/availability > cost.

## Outcomes
See REQUIREMENTS REQ-OUT-001. Partial memory results → `partial_success`, no automatic compensation (the
confirmed value is safe by construction, within bounds). Partial vCPU → compensated (`rolled_back`) or
`unknown_outcome` → guest blocked, operator reconciliation. `unknown_outcome` always blocks further mutation
on that guest until `recover()` classifies it.

## Failure catalog

| # | Failure | Detection | Safety risk | Allowed ops | Auto recovery | Manual recovery | Escalation | Data loss |
|---|---|---|---|---|---|---|---|---|
| F01 | controller crash | restart; journal incomplete ops | duplicate/lost mutation | none until recover() | reconcile vs live (tested each phase) | inspect `ambiguous_quarantined` | SEV2 if ambiguous | none (fsync) |
| F02 | thread deadlock | watchdog `local_stall`, liveness | stuck guest | reads | none | restart | SEV3 | none |
| F03 | state-store outage (disk full / EIO) | append raises → request fails | unrecorded mutation | reads | none | free space; restart | SEV2 | none acknowledged |
| F04 | state-store corruption | checksum / digest on load | wrong expected state | none (not ready) | torn tail only | restore backup + reconcile | SEV1 | ≤ RPO |
| F05 | audit corruption | chain/head/anchor verification | repudiation | reads only | none | restore + anchor compare | SEV1 | ≤ RPO |
| F06 | provider timeout | `ProviderTimeout` | unknown apply | other guests | reconcile | quarantine clear after check | SEV3 | none |
| F07 | provider restart | `ProviderUnavailable` | lost request | retry (idempotent+CAS) | yes | — | SEV4 | none |
| F08 | guest-agent stall | balloon refused / stall watchdog | reclaim not honoured | grow still allowed | none | investigate guest | SEV4 | none |
| F09 | guest crash | lifecycle `crashed` | mutating a dead VM | none for guest | none | — | owner of guest | none |
| F10 | VM paused/migrating | lifecycle | double accounting | none for guest | resumes when running | — | — | none |
| F11 | host reboot | lease lost, provider gone | stale state | none | re-register guests (INV-33), recover() | — | SEV3 | none |
| F12 | host memory pressure | reserve refusal counters | OOM | reclaim | reclaim order (quota) | quarantine tenant | SEV2 | none |
| F13 | node isolation / controller partition | lease renew fails | split brain | FROZEN_WRITE | re-acquire on heal | forced takeover procedure | SEV2 | none |
| F14 | site loss | lease store unreachable | cross-site control | none | none | ADR-0003 | SEV1 | ≤ RPO |
| F15 | identity outage | authn fails | unattributed ops | none (fail closed) | none | break-glass | SEV2 | none |
| F16 | policy outage | `policy_unavailable` | unauthorized ops | none | retry | — | SEV2 | none |
| F17 | key service outage | secret resolve fails | cannot verify tokens / sign audit | existing keys until expiry; else FROZEN | none | rotate | SEV2 | none |
| F18 | clock failure | skew beyond ±30 s → authn failures; lease anomalies | expired creds accepted/rejected | FROZEN | none | fix NTP | SEV2 | none |
| F19 | telemetry outage | sink errors | blind operation | all (TELEMETRY_DOWN) | drop-oldest | — | SEV4 | telemetry only |
| F20 | dependency version mismatch | bootstrap exit 3 / capability gen change | undefined behaviour | none (not ready) | none | upgrade/downgrade | SEV3 | none |

Network: control-plane down → no requests arrive (safe); provider path down → circuit open; state-store path
down → requests fail before acknowledgment; telemetry down → continue.

## Degraded modes and exit criteria

| Mode | Entry | Allowed | Exit |
|---|---|---|---|
| READ_ONLY | `mode=read_only` config | reads, audit | config rollback |
| FROZEN_WRITE | lease invalid, emergency, unknown outcome, integrity failure | reads, audit, safety reconciliation | ready() all checks true |
| LOCAL_SAFE | lease provable + state verified but upstream control plane unreachable | local adjustments from INV-33 local agent only | upstream reachable |
| TELEMETRY_DOWN | telemetry disabled/failing | all | sink healthy |
| EXPORT_DOWN | anchor sink failing | all; anchors retained locally | sink healthy + anchors flushed |
| FREE_PAGE_DOWN | guest agent not reporting | all; reports treated as absent | fresh report within `free_page_report_stale_s` |

## Failover
Takeover requires: previous lease expired (or forced by operator with ticket), new epoch acquired, `recover()`
complete, `store.verify()` true, live state re-read for every registered guest. The new controller never
controls guests of another site. Failover is audited (`ownership_acquired` with epoch; `reconciled` events).

## Fault-injection evidence
`tests/test_durability.py::CrashInjectionTest` (crash at every phase), `tests/test_adapter_contract.py`
(timeout, partial, refusal, restart, transient RPC, lying provider, capability change),
`tests/test_durability.py::FencingTest` (stale controller, partition, delayed packet). Results are stored as
release evidence by `release.py evidence`.
