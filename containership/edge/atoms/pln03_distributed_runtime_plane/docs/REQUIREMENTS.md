# PLN-03 normative requirements (MC-003)

Key words SHALL / SHALL NOT / SHOULD are used per RFC 2119. Every ID is stable and appears in `TRACEABILITY.json`. Site classes: **cloud**, **datacenter**, **near-edge**, **far-edge** (`config.SITE_CLASSES`).

## Functional
| ID | Requirement | Site classes | Implementation | Verified by |
|---|---|---|---|---|
| REQ-API-01 | The plane SHALL expose state, messaging, secrets and invocation only through `PK_STATE/1`, `PK_MESSAGE/1`, `PK_SECRET/1`, `PK_INVOKE/1`. | all | `plane.py`, `wire.py` | test_contract |
| REQ-API-02 | Requests SHALL be validated against the packaged schema before any adapter is called. | all | `wire.check` | test_mc018, fuzz |
| REQ-SEC-01 | Every call SHALL present a valid, unexpired capability token naming the workload, tenant and capability; absence or expiry SHALL fail closed. | all | `tokens.TokenVerifier` | test_mc013_* |
| REQ-SEC-02 | A call SHALL be refused unless the revision binds `<workload>:<capability>`, independent of token content. | all | `plane._call`, `runtime._adapter` | test_mc013_valid_token_but_no_binding |
| REQ-SEC-03 | Keys, topics, secrets and invocation targets SHALL be tenant-namespaced; cross-tenant access SHALL NOT be possible under any configuration. | all | `runtime._key/_channel`, invoke target | test_mc031 |
| REQ-SEC-04 | Every read, write, publish, secret access, invocation, denial, lifecycle and config change SHALL emit a hash-chained audit event carrying no payload or secret. | all | `audit_log.py` | test_mc034_*, test_mc025_no_payload |
| REQ-SEC-05 | When time, key, revocation or policy dependencies are unavailable the plane SHALL fail closed with a retryable code. | all | `tokens.py` | test_mc033 |
| REQ-MSG-01 | Accepted publishes SHALL be delivered at least once; the idempotency key SHALL suppress duplicates, including across restart and reconnect. | all | `runtime`, `durability` | test_mc041, test_mc009 |
| REQ-DUR-01 | Durable adapters SHALL journal before applying; a torn final record SHALL be discarded; interior corruption SHALL halt start-up. | datacenter, near-edge, far-edge | `DurableAdapter` | test_mc041_* |
| REQ-DUR-02 | Writes SHALL carry a fencing epoch; a stale epoch SHALL be refused. | all | `DurableAdapter`, `LeaseManager` | test_mc041_fencing |
| REQ-DIS-01 | On partition, far-edge and near-edge sites configured with `degraded.allow_local_buffer` SHALL buffer publishes in a bounded store and reconcile on reconnect using original idempotency keys; otherwise the plane SHALL return `PK_ADAPTER_UNAVAILABLE`. | near-edge, far-edge | `OfflineBuffer`, `plane.reconcile` | test_mc009_mc040 |
| REQ-DIS-02 | When the offline buffer is full the plane SHALL refuse new writes with `PK_READ_ONLY` and SHALL NOT drop buffered data. | near-edge, far-edge | `OfflineBuffer.put` | test_mc009_mc040 |
| REQ-FO-01 | Failover SHALL select only targets inside permitted residency zones, then meeting required consistency and lag; otherwise enter read-only mode. | cloud, datacenter | `select_failover` | test_mc039 |
| REQ-CFG-01 | Configuration SHALL be validated in full before activation, activated atomically and recorded with author, source, reason, digest and time. | all | `config.ConfigStore` | test_mc021–mc024 |
| REQ-CFG-02 | Configuration SHALL NOT contain secret material; diagnostics SHALL redact secret-shaped keys and values. | all | `config.validate`, `redact` | test_mc025_* |
| REQ-LC-01 | The runtime SHALL follow the lifecycle in `lifecycle.LEGAL`; writes SHALL be served only in READY/DEGRADED. | all | `lifecycle.py` | test_mc006_* |
| REQ-OPS-01 | Operators SHALL be able to freeze, quarantine an adapter and emergency-disable the runtime; each action SHALL be audited. | all | `plane.freeze/quarantine_adapter/emergency_disable` | test_mc042_* |
| REQ-VER-01 | Peers SHALL negotiate the highest common interface major; no common major SHALL be terminal. | all | `negotiation.py` | test_mc016 |
| REQ-ERR-01 | Every failure SHALL be representable as `pk.error-envelope/1` with one outcome class, HTTP and gRPC mapping. | all | `envelope.py` | test_mc015_* |

## Non-functional — see `docs/NFR.md` (NFR-* IDs).
