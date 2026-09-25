# GAP-11 operating modes (GAP11-*.16)

| Component | startup | steady | degraded | recovery | maintenance | shutdown |
|---|---|---|---|---|---|---|
| GAP11-P0-01 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P0-02 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P0-03 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P0-04 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P0-05 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P0-06 | collect inventory; unknown vendor -> refused | periodic collect + diff | provider outage => devices UNKNOWN, never removed | reappearing device -> QUARANTINED | drain before partition reconfigure | no privileged op left without evidence record |
| GAP11-P0-07 | collect inventory; unknown vendor -> refused | periodic collect + diff | provider outage => devices UNKNOWN, never removed | reappearing device -> QUARANTINED | drain before partition reconfigure | no privileged op left without evidence record |
| GAP11-P0-08 | collect inventory; unknown vendor -> refused | periodic collect + diff | provider outage => devices UNKNOWN, never removed | reappearing device -> QUARANTINED | drain before partition reconfigure | no privileged op left without evidence record |
| GAP11-P0-09 | keyring loaded from secret refs; missing key -> not ready | verify every call | identity/policy/KMS outage -> privileged ops fail closed | live key rotation, no restart | emergency revoke via Keyring.retire | nonce cache discarded (window bounded) |
| GAP11-P0-10 | keyring loaded from secret refs; missing key -> not ready | verify every call | identity/policy/KMS outage -> privileged ops fail closed | live key rotation, no restart | emergency revoke via Keyring.retire | nonce cache discarded (window bounded) |
| GAP11-P0-11 | keyring loaded from secret refs; missing key -> not ready | verify every call | identity/policy/KMS outage -> privileged ops fail closed | live key rotation, no restart | emergency revoke via Keyring.retire | nonce cache discarded (window bounded) |
| GAP11-P0-12 | bind loopback only (plaintext) | bounded in-flight | OVERLOADED / NOT_LEADER typed retryable errors | clients retry with same request_id | MAINTENANCE_MODE for mutations | server.shutdown(); no half-applied mutation |
| GAP11-P0-13 | bind loopback only (plaintext) | bounded in-flight | OVERLOADED / NOT_LEADER typed retryable errors | clients retry with same request_id | MAINTENANCE_MODE for mutations | server.shutdown(); no half-applied mutation |
| GAP11-P0-14 | pure functions; no state | deterministic decisions | missing thermal/health input -> device inadmissible | n/a (stateless) | drained devices excluded | n/a |
| GAP11-P0-15 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P0-16 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P1-17 | pure functions; no state | deterministic decisions | missing thermal/health input -> device inadmissible | n/a (stateless) | drained devices excluded | n/a |
| GAP11-P1-18 | pure functions; no state | deterministic decisions | missing thermal/health input -> device inadmissible | n/a (stateless) | drained devices excluded | n/a |
| GAP11-P1-19 | collect inventory; unknown vendor -> refused | periodic collect + diff | provider outage => devices UNKNOWN, never removed | reappearing device -> QUARANTINED | drain before partition reconfigure | no privileged op left without evidence record |
| GAP11-P1-20 | collect inventory; unknown vendor -> refused | periodic collect + diff | provider outage => devices UNKNOWN, never removed | reappearing device -> QUARANTINED | drain before partition reconfigure | no privileged op left without evidence record |
| GAP11-P1-21 | recover store from snapshot+WAL; refuse mutations until leader | all ops | store read-only / not leader: reads only, mutations refused with typed code | reconcile() before serving; SCRUBBING->QUARANTINED | freeze(): reads only | step_down(); in-flight commit either fsynced or discarded |
| GAP11-P1-22 | pure functions; no state | deterministic decisions | missing thermal/health input -> device inadmissible | n/a (stateless) | drained devices excluded | n/a |
| GAP11-P1-23 | pure functions; no state | deterministic decisions | missing thermal/health input -> device inadmissible | n/a (stateless) | drained devices excluded | n/a |
| GAP11-P1-24 | keyring must have an active audit key | bounded buffers | sink failure counted as dropped, control path unaffected | ledger verified on open | n/a | ledger fsynced per append |
| GAP11-P1-25 | keyring must have an active audit key | bounded buffers | sink failure counted as dropped, control path unaffected | ledger verified on open | n/a | ledger fsynced per append |
| GAP11-P1-26 | keyring must have an active audit key | bounded buffers | sink failure counted as dropped, control path unaffected | ledger verified on open | n/a | ledger fsynced per append |
| GAP11-P1-27 | keyring must have an active audit key | bounded buffers | sink failure counted as dropped, control path unaffected | ledger verified on open | n/a | ledger fsynced per append |
| GAP11-P1-28 | keyring must have an active audit key | bounded buffers | sink failure counted as dropped, control path unaffected | ledger verified on open | n/a | ledger fsynced per append |
| GAP11-P1-29 | built-in secure defaults | validated layered config | activation hook failure -> previous config kept | rollback() | freeze() | n/a |
| GAP11-P1-30 | keyring loaded from secret refs; missing key -> not ready | verify every call | identity/policy/KMS outage -> privileged ops fail closed | live key rotation, no restart | emergency revoke via Keyring.retire | nonce cache discarded (window bounded) |
| GAP11-P1-31 | keyring must have an active audit key | bounded buffers | sink failure counted as dropped, control path unaffected | ledger verified on open | n/a | ledger fsynced per append |
| GAP11-P1-32 | built-in secure defaults | validated layered config | activation hook failure -> previous config kept | rollback() | freeze() | n/a |
| GAP11-P2-33 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-34 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-35 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-36 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-37 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-38 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-39 | hermetic temp dirs | tools/run_checklist.py | missing lane reported NOT RUN, never PASS | rerun is idempotent | n/a | evidence archived under evidence/ |
| GAP11-P2-40 | n/a | ci.sh | missing signer -> release refused | rebuild from source revision | n/a | n/a |
| GAP11-P2-41 | n/a | ci.sh | missing signer -> release refused | rebuild from source revision | n/a | n/a |
| GAP11-P2-42 | n/a | ci.sh | missing signer -> release refused | rebuild from source revision | n/a | n/a |
| GAP11-P2-43 | n/a | ci.sh | missing signer -> release refused | rebuild from source revision | n/a | n/a |
| GAP11-P2-44 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
| GAP11-P2-45 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
| GAP11-P2-46 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
| GAP11-P2-47 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
| GAP11-P2-48 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
| GAP11-P2-49 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
| GAP11-P2-50 | n/a | reviewed on cadence | expired exception -> gate fails | n/a | n/a | n/a |
