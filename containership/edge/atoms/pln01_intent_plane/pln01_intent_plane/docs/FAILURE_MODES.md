# Failure-mode catalog (MC-024)

| ID | Failure | Detection | Blast radius | Behaviour / state transition | Recovery | Code | Test |
|---|---|---|---|---|---|---|---|
| F01 | Dependency cycle declared | `_would_create_cycle`, `order()` | one request | rejected, graph unchanged | fix declaration | E0002 | core |
| F02 | Concurrent writers, stale version | expected_version | one request | rejected | re-read, retry | E0003 | core, concurrency |
| F03 | Disconnected site | report staleness | nodes at site | steps held | automatic on fresh report | — | DisconnectedSites |
| F04 | Downstream rejects released step | executor reports | one step | drift stays open; next plan re-emits | investigate executor | — | adjacent fake |
| F05 | Identity service down | authenticator raises | all requests | fail closed, readiness fails | restore PLN-07 | E0010 | AuthAndAuthz |
| F06 | Policy engine down/erroring | adapter | mutations | deny | restore GAP-13 | E0005 | AuthAndAuthz |
| F07 | Disk full / write error | WAL append raises | one mutation | mutation rolled back, not acked | free space; retry | E9999→ops alert | DurableState |
| F08 | Torn trailing WAL record | chain read at open | none | truncated, prior state intact | automatic | — | DurableState |
| F09 | Mid-log corruption / tamper | hash/MAC mismatch | whole plane | fail-stop | restore from backup | E0020 | DurableState |
| F10 | Crash between snapshot and compaction | anchor check | none | replay skips covered records | automatic | — | DurableState |
| F11 | Lost lease / partition | `FileLease.check` | writer | mutations refused | failover to new holder | E0019 | DurableState |
| F12 | Overload | bulkhead | excess requests | shed | client backoff | E0012 | FlowControl |
| F13 | Tenant flood | token bucket | that tenant | throttled | backoff | E0011 | Adversarial |
| F14 | Deadline expiry | Deadline | one request | aborted | retry | E0013 | FlowControl |
| F15 | Newer on-disk format | migrate() | startup | refuse to start | run newer binary | E0020 | DurableState |
| F16 | History aged out | `_state_at` | diff/rollback | refused | restore from backup | E0007 | core |
| F17 | Transaction step fails | exception in txn | the transaction | compensating rollback to start version | fix and resubmit | E0022 | Transactions |
| F18 | Stall (no progress) | Health.stalled | process | liveness fails → restart | orchestrator restart | — | Observability |
