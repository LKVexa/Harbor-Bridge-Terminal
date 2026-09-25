# INV-05 Missing Components Inventory — status at 4.3.0

**Baseline audited:** 4.2.0 · **Status as of:** 4.3.0 (2026-09-22)
Generated from `traceability/mc_status.json` and `traceability/CHECKLIST_STATUS.json` (regenerate with `python traceability/mc_source.py`).

Sub-item totals (2346 items): blocked-external 101 · done 1859 · done-single-member 42 · open-approval 221 · partial 123

`done` = implemented and backed by an automated test or evidence in this package. `done-single-member` = proven for the single-member topology only. `open-approval` = needs a human decision. `blocked-external` = needs an artefact or system that was not supplied. Every non-done item carries an exception in `docs/EXCEPTIONS.json`.

| ID | P | Component | Status | Exception | Sub-items done | Main implementation |
|---|---|---|---|---|---|---|
| MC-001 | P0 | pk_core framework/runtime dependency | **blocked-external** | EX-003 | 14/45 | backend.py::runtime_self_test |
| MC-002 | P0 | MASTER.md master prompt/workflow corpus | **open-approval** | EX-002 | 33/44 | tools_check.py::check_master_md |
| MC-003 | P0 | Requirements-to-evidence traceability matrix | **done** | EX-006 | 38/45 | tools_check.py::check_trace, traceability/trace_source.py |
| MC-004 | P0 | Approved production backend/version pin | **blocked-external** | EX-001 | 12/44 | backend.py::ExternalBackendContract |
| MC-005 | P0 | Production backend adapter/client | **partial** | EX-001 | 33/45 | backend.py::LocalBackend, backend.py::classify_backend_error |
| MC-006 | P0 | Persistent durable storage path | **done** | — | 41/46 | wal.py::DurableStore, wal.py::WriteAheadLog |
| MC-007 | P0 | Consensus/member-management integration | **blocked-external** | EX-001 | 11/45 | backend.py::ExternalBackendContract |
| MC-008 | P1 | Revision-aware read/list/range API | **done** | — | 40/45 | store.py::ControlStore.range, store.py::ControlStore.get |
| MC-009 | P1 | Delete/tombstone semantics | **done** | — | 40/45 | store.py::ControlStore.delete |
| MC-010 | P1 | Full transaction success/failure branches | **done** | — | 40/45 | store.py::ControlStore.txn |
| MC-011 | P1 | Rich compare predicates | **done** | — | 40/45 | store.py::COMPARE_TARGETS |
| MC-012 | P0 | Versioned typed wire schemas | **done** | — | 40/45 | schema.py::MESSAGES |
| MC-013 | P1 | Structured machine-readable error model | **done** | — | 40/45 | errors.py::ERROR_CATALOG |
| MC-014 | P1 | Streaming watch transport | **done** | — | 40/45 | server.py::_Handler._stream_watch, watch.py::Watcher |
| MC-015 | P1 | Watch session lifecycle and slow-consumer controls | **done** | — | 40/45 | watch.py::WatchHub |
| MC-016 | P1 | Typed event schema | **done** | — | 39/45 | store.py::Event |
| MC-017 | P1 | Consistent snapshot + relist protocol | **done** | — | 40/45 | store.py::ControlStore.snapshot, client.py::Mirror |
| MC-018 | P1 | Lease/TTL/session ownership subsystem | **done** | — | 40/45 | store.py::ControlStore.lease_grant, store.py::Lease |
| MC-019 | P1 | Compaction/retention controller | **done** | — | 40/45 | backup.py::CompactionController |
| MC-020 | P1 | Interface/resource limits | **done** | — | 40/45 | limits.py::Limits |
| MC-021 | P0 | Tenant/environment/site/workload isolation implementation | **done** | — | 40/45 | security.py::Namespace, service.py::ControlStateService._map_op |
| MC-022 | P0 | Authentication / node and peer identity | **done** | — | 38/45 | security.py::MTLSAuthenticator |
| MC-023 | P0 | Authorization / capability policy | **done** | — | 40/45 | security.py::Authorizer |
| MC-024 | P0 | Secrets/KMS/key-rotation integration | **partial** | — | 37/45 | security.py::SecretProvider, wal.py::Keyring |
| MC-025 | P0 | Encryption in transit and at rest | **done** | — | 40/45 | security.py::server_tls_context, wal.py::Sealer |
| MC-026 | P1 | Timeout/cancellation/retry/idempotency contract | **done** | — | 40/45 | service.py::OP_CLASSES, client.py::Client.call |
| MC-027 | P1 | Protocol/version negotiation and compatibility matrix | **partial** | EX-004 | 35/45 | schema.py::negotiate |
| MC-028 | P1 | Declarative configuration subsystem | **done** | — | 41/46 | config.py::build |
| MC-029 | P1 | Deterministic production bootstrap | **done** | — | 40/45 | bootstrap.py::build_service |
| MC-030 | P1 | Health/readiness/version/capability endpoints | **done-single-member** | EX-001 | 36/44 | service.py::ControlStateService.readiness |
| MC-031 | P1 | Graceful drain, freeze, quarantine, and emergency-disable controls | **done** | — | 40/45 | service.py::ControlStateService.freeze, service.py::ControlStateService.quarantine |
| MC-032 | P1 | Production metrics instrumentation | **done** | — | 40/45 | observability.py::Metrics |
| MC-033 | P1 | Structured logging | **done** | — | 40/45 | observability.py::StructuredLogger |
| MC-034 | P1 | Distributed tracing | **done** | — | 40/45 | observability.py::Tracer |
| MC-035 | P2 | Decision/explainability view | **done** | — | 39/45 | observability.py::ExplainStore |
| MC-036 | P2 | Telemetry privacy/retention/export policy | **done** | — | 40/45 | observability.py::METRIC_CATALOG |
| MC-037 | P1 | Dashboards and alert rules | **partial** | EX-005 | 37/45 | observability/dashboards/overview.json |
| MC-038 | P0 | Tamper-evident security audit log | **done** | — | 40/45 | audit.py::AuditLog |
| MC-039 | P0 | Backup/restore integration and restore verification | **done** | — | 41/46 | backup.py::create_backup, backup.py::restore_backup |
| MC-040 | P1 | Disaster recovery / site failover plan | **partial** | EX-001 | 36/45 | replication.py::ReplicaApplier |
| MC-041 | P1 | GAP-05 replication/consistency integration | **partial** | EX-004 | 37/45 | replication.py::ReplicationSource, replication.py::ReplicaApplier |
| MC-042 | P1 | Reproducible benchmark and capacity suite | **partial** | EX-005 | 36/46 | bench.py::run |
| MC-043 | P0 | Linearizability/concurrency history checker | **done-single-member** | EX-001 | 37/45 | linearizability.py::check |
| MC-044 | P1 | Fault-injection/chaos suite | **done-single-member** | EX-001 | 37/45 | wal.py::SimulatedCrash |
| MC-045 | P1 | Fuzzing and adversarial security tests | **done** | — | 40/45 | schema.py::loads |
| MC-046 | P1 | Adjacent-layer integration and compatibility tests | **blocked-external** | EX-004 | 11/45 | server.py::ControlStateHTTPServer |
| MC-047 | P1 | Public contract tests and conformance fixtures | **done** | — | 39/45 | conformance/runner.py::run_file |
| MC-048 | P0 | CI/release acceptance pipeline and machine-readable evidence | **partial** | EX-008 | 36/46 | tools/ci_gate.py, tools/release_gate.py |
| MC-049 | P0 | Dependency lock, SBOM, vulnerability policy, artifact provenance/signing | **partial** | EX-009 | 35/46 | tools_check.py::sbom, tools_check.py::provenance |
| MC-050 | P1 | Deployment/upgrade/migration/rollback package | **done** | — | 41/46 | server.py::ControlStateHTTPServer.graceful_shutdown, serve.py::main |
| MC-051 | P1 | Day-0/day-1/day-2 and incident runbooks | **done** | — | 41/46 | bootstrap.py::main |
| MC-052 | P2 | Governance package: owner, ADR, exceptions, reviews, license | **open-approval** | EX-006 | 30/46 | tools_check.py::check_exceptions |

---

## Original 4.2.0 inventory (kept for history)


**Audited version:** 4.2.0  
**Date:** 2026-09-22  
**Scope:** contents of this standalone archive only. A component is listed when the archive does not contain an implementation, schema, evidence artifact, or operational integration sufficient to substantiate the corresponding production capability. Items explicitly outside INV-05 ownership are marked **External dependency** rather than silently treated as satisfied.

Priority: **P0** = blocks trustworthy production certification; **P1** = required production capability; **P2** = hardening/scale/operability requirement; **P3** = governance/completeness.

| ID | Priority | Missing component | Current state / required completion | Checklist linkage |
|---|---|---|---|---|
| MC-001 | P0 | `pk_core` framework/runtime dependency | Not bundled. Full 100-item assessment, evidence ledger, gate, and verifier cannot execute in this archive. Pin an approved version and provide a reproducible resolution path. | C020, C090, C100 |
| MC-002 | P0 | `MASTER.md` master prompt/workflow corpus | README previously claimed this file was included, but it is absent. Restore the authoritative artifact or remove it from the product definition and traceability model. | C020 |
| MC-003 | P0 | Requirements-to-evidence traceability matrix | `CHECKLIST.json` defines 100 requirements, but the archive lacks a standalone matrix mapping every item to concrete implementation, test, evidence, owner, and status. | C020, C090 |
| MC-004 | P0 | Approved production backend/version pin | The checklist names etcd, but there is no pinned etcd release/specification, compatibility constraint, checksum, or support policy. | C010, C031, C093 |
| MC-005 | P0 | Production backend adapter/client | `state.py` is an in-memory reference model only. Add the real storage adapter, endpoint discovery, session management, and backend error translation. | C021, C030, C031 |
| MC-006 | P0 | Persistent durable storage path | No WAL, durable database, fsync policy, snapshot persistence, crash recovery, or durability test exists in the package. | C013, C057, C095 |
| MC-007 | P0 | Consensus/member-management integration | **External dependency by design.** No integration contract proves quorum, leader/member lifecycle, split-brain handling, or membership change behavior. | C003, C055, C058 |
| MC-008 | P1 | Revision-aware read/list/range API | The model exposes `get()` only; no versioned public API exists for point reads, prefix/range reads, pagination, or consistent list/relist. | C011, C015, C021 |
| MC-009 | P1 | Delete/tombstone semantics | Transactions only write replacement values. There is no delete operation, delete event, tombstone model, or delete/watch/compaction test. | C011, C015, C021 |
| MC-010 | P1 | Full transaction success/failure branches | The declared `PK_CSTATE_TXN/1` interface says compare then success **or failure** operations; the model only applies success writes or returns `False`. | C011, C014, C021 |
| MC-011 | P1 | Rich compare predicates | Only `mod_revision` equality is modeled. Production transactions typically require existence/version/value/lease or equivalent typed predicates. | C011, C022 |
| MC-012 | P0 | Versioned typed wire schemas | `PK_CSTATE_TXN/1`, `WATCH/1`, and `COMPACT/1` are names only. No protobuf/WIT/JSON Schema/IDL definitions or compatibility fixtures are included. | C021, C022, C027 |
| MC-013 | P1 | Structured machine-readable error model | No stable error codes/details exist for compare failure, compaction, invalid request, unavailable backend, auth failure, quota, overload, timeout, or cancellation. | C014, C026 |
| MC-014 | P1 | Streaming watch transport | `watch()` returns an in-memory list snapshot; there is no long-lived stream/server, ordered event delivery transport, heartbeat, or cancellation protocol. | C021, C025 |
| MC-015 | P1 | Watch session lifecycle and slow-consumer controls | No reconnect/resume token, cancellation, progress notification, bounded queue, backpressure, slow-consumer eviction, or stream quota behavior. | C025, C028, C054, C067 |
| MC-016 | P1 | Typed event schema | History tuples do not define create/update/delete type, prior value, transaction identity, tenant/workload identity, correlation metadata, or schema version. | C022, C073, C078 |
| MC-017 | P1 | Consistent snapshot + relist protocol | Compaction raises `Compacted`, but no production protocol obtains an atomic snapshot/revision pair and resumes watching without a race. | C014, C055, C057 |
| MC-018 | P1 | Lease/TTL/session ownership subsystem | Example code uses a “lease” key, but there is no lease object, TTL, renewal, expiry, fencing token, session loss, or stale-owner prevention. | C015, C058 |
| MC-019 | P1 | Compaction/retention controller | Manual `compact()` exists only in the model. Missing retention policy, scheduler, safety margin, compaction observability, and operator override. | C017, C057, C069 |
| MC-020 | P1 | Interface/resource limits | No enforced key-size, value-size, transaction-op, watch, connection, history, memory, queue, concurrency, or request-rate limits. | C017, C028, C054, C067 |
| MC-021 | P0 | Tenant/environment/site/workload isolation implementation | Boundaries are declared in the contract but not enforced by keyspace partitioning, credentials, network policy, quotas, or tests. | C006, C046, C064 |
| MC-022 | P0 | Authentication / node and peer identity | No mTLS, workload identity, certificate validation, node identity, peer authentication, rotation, or trust bootstrap is present. | C023, C044, C048 |
| MC-023 | P0 | Authorization / capability policy | **External ownership is declared**, but no integration point, RBAC/ABAC/capability check, deny-by-default policy, or authorization test is supplied. | C024, C042, C046 |
| MC-024 | P0 | Secrets/KMS/key-rotation integration | No secret provider, key hierarchy, rotation, unavailable-KMS behavior, or secret-redaction contract is present. | C039, C047, C048 |
| MC-025 | P0 | Encryption in transit and at rest | No TLS policy/ciphers, certificate policy, encrypted storage configuration, key rotation, or verification evidence. | C047 |
| MC-026 | P1 | Timeout/cancellation/retry/idempotency contract | No bounded retry/backoff/jitter matrix, idempotency semantics, cancellation propagation, request deadlines, or retry-safety classification. | C025, C053 |
| MC-027 | P1 | Protocol/version negotiation and compatibility matrix | No peer-version negotiation, N/N-1 policy, downgrade behavior, migration compatibility, or adjacent-version matrix. | C016, C027, C084, C093 |
| MC-028 | P1 | Declarative configuration subsystem | Missing typed config schema, secure defaults, environment/site overlays, validation, atomic activation, provenance, and rollback. | C032-C038 |
| MC-029 | P1 | Deterministic production bootstrap | No empty-node bootstrap procedure, trust bootstrap, backend initialization, seed/member discovery, initial policy, or bootstrap verification. | C040 |
| MC-030 | P1 | Health/readiness/version/capability endpoints | No liveness/readiness/stall detection endpoint or dependency-health exposure exists. | C052, C071 |
| MC-031 | P1 | Graceful drain, freeze, quarantine, and emergency-disable controls | No admission freeze, watch drain, write freeze, maintenance mode, unsafe-node quarantine, or controlled shutdown semantics. | C059, C092 |
| MC-032 | P1 | Production metrics instrumentation | Contract lists signal names, but no counters/histograms/exporter for request rate, conflicts, latency, saturation, compaction, backlog, storage, or resources. | C061-C069, C072 |
| MC-033 | P1 | Structured logging | No stable structured log schema, correlation IDs, node/site/tenant/workload identifiers, redaction rules, or log-level policy. | C073, C075 |
| MC-034 | P1 | Distributed tracing | No trace-context propagation, spans, sampling, exporter, or backend-call correlation. | C074, C079 |
| MC-035 | P2 | Decision/explainability view | No operator-readable explanation connects transactions/refusals/compactions to input state, policies, topology, constraints, or release lineage. | C076-C078 |
| MC-036 | P2 | Telemetry privacy/retention/export policy | No retention, sampling, high-cardinality controls, privacy classification, export allowlist, or tenant-data safeguards. | C075, C079 |
| MC-037 | P1 | Dashboards and alert rules | No dashboards or alert thresholds distinguish normal load, overload, compaction pressure, dependency loss, security rejection, or software defects. | C062, C069, C080 |
| MC-038 | P0 | Tamper-evident security audit log | No append-only/auditable record for authentication, authorization, transaction, compaction, configuration, membership, or administrative operations. | C049 |
| MC-039 | P0 | Backup/restore integration and restore verification | **Backups are non-owned**, but production requires an integrated backup/restore contract, schedule, retention, encryption, restore test, and RPO/RTO evidence. | C003, C095 |
| MC-040 | P1 | Disaster recovery / site failover plan | No site-loss, partition, provider loss, reconnect, degraded-control-plane, or residency-safe failover procedure/evidence. | C018, C051, C055, C089 |
| MC-041 | P1 | GAP-05 replication/consistency integration | Dependency is named but no adapter, handshake, lag/fencing contract, conflict semantics, or cross-site consistency test is bundled. | C003, C030, C055 |
| MC-042 | P1 | Reproducible benchmark and capacity suite | No p50/p95/p99/worst-case baseline, throughput/overload/scale test, memory/storage/network profile, saturation model, or release regression gate. | C061-C070, C088 |
| MC-043 | P0 | Linearizability/concurrency history checker | The new local thread race test is useful, but there is no Jepsen/Porcupine-style or equivalent history-based verification under process/node/network faults. | C013, C058, C086, C089 |
| MC-044 | P1 | Fault-injection/chaos suite | No crash, stall, disk-full, latency, packet-loss, partition, dependency-failure, clock/service-loss, or recovery-objective tests. | C051-C060, C089 |
| MC-045 | P1 | Fuzzing and adversarial security tests | No fuzzers/property tests for keys, revisions, schemas, protocol frames, replay, spoofing, injection, resource exhaustion, or privilege boundaries. | C041, C050, C085, C087 |
| MC-046 | P1 | Adjacent-layer integration and compatibility tests | No executable tests with INV-04, GAP-05, INV-07, PLN-03, backend versions, architectures, runtimes, or site tiers. | C030, C083, C084 |
| MC-047 | P1 | Public contract tests and conformance fixtures | Standalone unit tests exist, but no golden request/response fixtures, schema vectors, wire-level contract tests, or cross-implementation conformance pack. | C029, C082 |
| MC-048 | P0 | CI/release acceptance pipeline and machine-readable evidence | No workflow runs unit/optimized/integration/security/performance gates and emits signed acceptance evidence before release. | C070, C090, C100 |
| MC-049 | P0 | Dependency lock, SBOM, vulnerability policy, artifact provenance/signing | No dependency lockfile, SBOM, vulnerability scan policy, signature, provenance attestation, approved digest set, or verification step. | C045, C094 |
| MC-050 | P1 | Deployment/upgrade/migration/rollback package | No service definition, deployment manifest, upgrade choreography, schema/data migration, canary, staged rollout, rollback, or emergency-disable implementation. | C038, C092, C095 |
| MC-051 | P1 | Day-0/day-1/day-2 and incident runbooks | README gives only a short outline. Missing detailed operator commands, diagnosis trees, paging/severity, containment, recovery, escalation, and validation procedures. | C096, C097 |
| MC-052 | P2 | Governance package: owner, ADR, exceptions, reviews, license | No accountable owner/escalation artifact, approved ADR, waiver/debt register, recurring review evidence, `LICENSE`, or `NOTICE` is bundled. | C009, C010, C098, C099 |

## Summary

- **52 missing or externally required components** are identified.
- The highest-risk gaps are not defects in the new reference model; they are missing production-system layers: real backend/persistence, typed network contracts, identity/authorization, durability/DR, observability, test certification, and supply-chain/release controls.
- The archive should therefore be treated as a **hardened reference/conformance component**, not a production control-state service, until the P0 and P1 items are implemented and independently evidenced.
