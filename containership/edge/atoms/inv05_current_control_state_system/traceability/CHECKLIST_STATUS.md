# 52-component checklist status — INV-05 4.3.0

Items: 2346 · blocked-external: 101 · done: 1859 · done-single-member: 42 · open-approval: 221 · partial: 123
Components: blocked-external: 4 · done: 34 · done-single-member: 3 · open-approval: 2 · partial: 9

Status vocabulary is defined in `traceability/mc_source.py`. Per-item detail: `CHECKLIST_STATUS.json`.

| ID | P | Component | Status | Exception | Items done / total | Evidence |
|---|---|---|---|---|---|---|
| MC-001 | P0 | pk_core framework/runtime dependency | blocked-external | EX-003 | 14 / 45 | test_config_bootstrap.BackendBoundaryTest.test_local_backend_identity_and_runtime_self_test; deploy/pk_core_pin.json, docs/COMPATIBILITY.md |
| MC-002 | P0 | MASTER.md master prompt/workflow corpus | open-approval | EX-002 | 33 / 44 | test_tooling.MasterMdTest; docs/adr/ADR-007-master-md.md |
| MC-003 | P0 | Requirements-to-evidence traceability matrix | done | EX-006 | 38 / 45 | test_tooling.TraceabilityTest; traceability/TRACE_MATRIX.md |
| MC-004 | P0 | Approved production backend/version pin | blocked-external | EX-001 | 12 / 44 | test_config_bootstrap.BackendBoundaryTest; deploy/backend_pin.json, docs/adr/ADR-002-backend-and-consensus.md |
| MC-005 | P0 | Production backend adapter/client | partial | EX-001 | 33 / 45 | test_config_bootstrap.BackendBoundaryTest; docs/adr/ADR-002-backend-and-consensus.md |
| MC-006 | P0 | Persistent durable storage path | done |  | 41 / 46 | test_durability, test_chaos; docs/adr/ADR-004-durability.md |
| MC-007 | P0 | Consensus/member-management integration | blocked-external | EX-001 | 11 / 45 | —; docs/CONSENSUS_CONTRACT.md |
| MC-008 | P1 | Revision-aware read/list/range API | done |  | 40 / 45 | test_store.ReadApiTest; docs/INTERFACES.md |
| MC-009 | P1 | Delete/tombstone semantics | done |  | 40 / 45 | test_store.DeleteTest; docs/REQUIREMENTS.md |
| MC-010 | P1 | Full transaction success/failure branches | done |  | 40 / 45 | test_store.TxnTest, test_linearizability; store.py |
| MC-011 | P1 | Rich compare predicates | done |  | 40 / 45 | test_store.TxnTest.test_rich_predicates; docs/INTERFACES.md |
| MC-012 | P0 | Versioned typed wire schemas | done |  | 40 / 45 | test_protocol; conformance/schema_lock.json, docs/adr/ADR-003-wire-schema.md |
| MC-013 | P1 | Structured machine-readable error model | done |  | 40 / 45 | test_protocol.ErrorModelTest; conformance/error_catalog_lock.json |
| MC-014 | P1 | Streaming watch transport | done |  | 40 / 45 | test_http.MTLSEndToEnd.test_watch_stream_events_and_progress, test_watch; docs/adr/ADR-006-watch-delivery.md |
| MC-015 | P1 | Watch session lifecycle and slow-consumer controls | done |  | 40 / 45 | test_watch; docs/adr/ADR-006-watch-delivery.md |
| MC-016 | P1 | Typed event schema | done |  | 39 / 45 | test_protocol.GoldenTest.test_event_roundtrip; conformance/golden_messages_v1.json |
| MC-017 | P1 | Consistent snapshot + relist protocol | done |  | 40 / 45 | test_store.SnapshotTest, test_http.MTLSEndToEnd.test_mirror_converges_under_writers_and_compaction; client.py |
| MC-018 | P1 | Lease/TTL/session ownership subsystem | done |  | 40 / 45 | test_store.LeaseTest; docs/adr/ADR-004-durability.md |
| MC-019 | P1 | Compaction/retention controller | done |  | 40 / 45 | test_backup_repl.CompactionControllerTest, test_store.CompactionTest; docs/operations/RUNBOOK_DAY2.md |
| MC-020 | P1 | Interface/resource limits | done |  | 40 / 45 | test_store.TxnTest.test_limits, test_fuzz.FuzzTest.test_resource_exhaustion_under_limits; docs/INTERFACES.md |
| MC-021 | P0 | Tenant/environment/site/workload isolation implementation | done |  | 40 / 45 | test_service.IsolationTest; deploy/k8s/networkpolicy.yaml |
| MC-022 | P0 | Authentication / node and peer identity | done |  | 38 / 45 | test_security.MTLSTest, test_http.MTLSEndToEnd; docs/adr/ADR-005-security.md |
| MC-023 | P0 | Authorization / capability policy | done |  | 40 / 45 | test_service.AuthzTest, test_fuzz.FuzzTest.test_authz_privilege_boundaries; docs/adr/ADR-005-security.md |
| MC-024 | P0 | Secrets/KMS/key-rotation integration | partial |  | 37 / 45 | test_security.SecretsTest, test_durability.DurabilityTest.test_encryption_at_rest_and_key_rotation; docs/adr/ADR-005-security.md |
| MC-025 | P0 | Encryption in transit and at rest | done |  | 40 / 45 | test_security.TLSConfigTest, test_http.MTLSEndToEnd.test_server_certificate_rotation_without_restart; docs/adr/ADR-005-security.md |
| MC-026 | P1 | Timeout/cancellation/retry/idempotency contract | done |  | 40 / 45 | test_service.DeadlineTest, test_http.MTLSEndToEnd.test_client_retries_respect_retry_after_and_budget; docs/INTERFACES.md |
| MC-027 | P1 | Protocol/version negotiation and compatibility matrix | partial | EX-004 | 35 / 45 | test_protocol.NegotiationTest; docs/COMPATIBILITY.md |
| MC-028 | P1 | Declarative configuration subsystem | done |  | 41 / 46 | test_config_bootstrap.ConfigTest; deploy/config/base.json |
| MC-029 | P1 | Deterministic production bootstrap | done |  | 40 / 45 | test_config_bootstrap.BootstrapTest; docs/operations/RUNBOOK_DAY0.md |
| MC-030 | P1 | Health/readiness/version/capability endpoints | done-single-member | EX-001 | 36 / 44 | test_service.HealthTest, test_http.MTLSEndToEnd.test_health_version_metrics; deploy/k8s/statefulset.yaml |
| MC-031 | P1 | Graceful drain, freeze, quarantine, and emergency-disable controls | done |  | 40 / 45 | test_service.ControlsTest; docs/operations/INCIDENTS.md |
| MC-032 | P1 | Production metrics instrumentation | done |  | 40 / 45 | test_service.ObservabilityTest; docs/TELEMETRY_POLICY.md |
| MC-033 | P1 | Structured logging | done |  | 40 / 45 | test_service.ObservabilityTest.test_structured_log_schema_redaction_and_storm_control; docs/TELEMETRY_POLICY.md |
| MC-034 | P1 | Distributed tracing | done |  | 40 / 45 | test_service.ObservabilityTest.test_trace_propagation_and_error_bias, test_service.ObservabilityTest.test_operational_spans; docs/TELEMETRY_POLICY.md |
| MC-035 | P2 | Decision/explainability view | done |  | 39 / 45 | test_service.ObservabilityTest.test_explain_record; docs/TELEMETRY_POLICY.md |
| MC-036 | P2 | Telemetry privacy/retention/export policy | done |  | 40 / 45 | test_service.ObservabilityTest.test_cardinality_cap; docs/TELEMETRY_POLICY.md |
| MC-037 | P1 | Dashboards and alert rules | partial | EX-005 | 37 / 45 | —; observability/alerts/inv05-rules.yml |
| MC-038 | P0 | Tamper-evident security audit log | done |  | 40 / 45 | test_service.AuditTest; docs/operations/AUDIT_RETENTION.md |
| MC-039 | P0 | Backup/restore integration and restore verification | done |  | 41 / 46 | test_backup_repl.BackupTest; docs/DR_PLAN.md, tools/restore_drill.py |
| MC-040 | P1 | Disaster recovery / site failover plan | partial | EX-001 | 36 / 45 | test_backup_repl.ReplicationTest; docs/DR_PLAN.md |
| MC-041 | P1 | GAP-05 replication/consistency integration | partial | EX-004 | 37 / 45 | test_backup_repl.ReplicationTest; replication.py |
| MC-042 | P1 | Reproducible benchmark and capacity suite | partial | EX-005 | 36 / 46 | —; docs/CAPACITY.md, evidence/bench/bench_fsync.json |
| MC-043 | P0 | Linearizability/concurrency history checker | done-single-member | EX-001 | 37 / 45 | test_linearizability; linearizability.py |
| MC-044 | P1 | Fault-injection/chaos suite | done-single-member | EX-001 | 37 / 45 | test_chaos, test_durability; docs/FAULT_CATALOG.md |
| MC-045 | P1 | Fuzzing and adversarial security tests | done |  | 40 / 45 | test_fuzz; docs/THREAT_MODEL.md |
| MC-046 | P1 | Adjacent-layer integration and compatibility tests | blocked-external | EX-004 | 11 / 45 | test_http; docs/COMPATIBILITY.md |
| MC-047 | P1 | Public contract tests and conformance fixtures | done |  | 39 / 45 | test_protocol.ConformanceRunnerTest; conformance/vectors_v1.json |
| MC-048 | P0 | CI/release acceptance pipeline and machine-readable evidence | partial | EX-008 | 36 / 46 | test_tooling.ReleaseGateTest; .github/workflows/ci.yml |
| MC-049 | P0 | Dependency lock, SBOM, vulnerability policy, artifact provenance/signing | partial | EX-009 | 35 / 46 | test_tooling.SupplyChainTest; requirements.lock, docs/SECURITY_POLICY.md |
| MC-050 | P1 | Deployment/upgrade/migration/rollback package | done |  | 41 / 46 | test_http.TokenLoopbackAndShutdown.test_bearer_tokens_and_graceful_drain; docs/ROLLOUT.md, deploy/Dockerfile |
| MC-051 | P1 | Day-0/day-1/day-2 and incident runbooks | done |  | 41 / 46 | —; docs/operations/RUNBOOK_DAY0.md, docs/operations/INCIDENTS.md |
| MC-052 | P2 | Governance package: owner, ADR, exceptions, reviews, license | open-approval | EX-006 | 30 / 46 | test_tooling.ExceptionsTest; docs/GOVERNANCE.md, docs/EXCEPTIONS.json |

## Items not done

| Item | Status | Reason |
|---|---|---|
| MC-001-01 | blocked-external | no pk_core release supplied |
| MC-001-03 | blocked-external | offline install path templated in pin; needs artefact |
| MC-001-04 | blocked-external | framework gate cannot run |
| MC-001-06 | partial | CI matrix has pk_core=absent axis only |
| MC-001-07 | blocked-external | licence unknown until pinned |
| MC-001-12 | blocked-external | EX-003 |
| MC-001-13 | blocked-external | EX-003 |
| MC-001-14 | blocked-external | EX-003 |
| MC-001-15 | blocked-external | EX-003 |
| MC-001-17 | blocked-external | EX-003 |
| MC-001-18 | blocked-external | EX-003 |
| MC-001-20 | blocked-external | EX-003 |
| MC-001-21 | blocked-external | EX-003 |
| MC-001-22 | blocked-external | EX-003 |
| MC-001-23 | blocked-external | EX-003 |
| MC-001-24 | blocked-external | EX-003 |
| MC-001-25 | blocked-external | EX-003 |
| MC-001-26 | blocked-external | EX-003 |
| MC-001-27 | blocked-external | EX-003 |
| MC-001-28 | blocked-external | EX-003 |
| MC-001-29 | blocked-external | EX-003 |
| MC-001-33 | open-approval | EX-006 |
| MC-001-34 | blocked-external | EX-003 |
| MC-001-36 | open-approval | EX-006 |
| MC-001-E01 | open-approval | requires named approver (EX-006) |
| MC-001-E03 | open-approval | requires named approver (EX-006) |
| MC-001-E04 | partial | boundary only |
| MC-001-D01 | blocked-external | see component status |
| MC-001-D02 | blocked-external | see EX-003 |
| MC-001-D03 | partial | open exception EX-003 |
| MC-001-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-002-01 | open-approval | deprecation proposed in ADR-007 |
| MC-002-05 | open-approval | moot if deprecated |
| MC-002-06 | partial | review rule documented; branch protection not in package |
| MC-002-32 | open-approval | EX-006 |
| MC-002-35 | open-approval | EX-006 |
| MC-002-E01 | open-approval | requires named approver (EX-006) |
| MC-002-E03 | open-approval | requires named approver (EX-006) |
| MC-002-D01 | open-approval | see component status |
| MC-002-D02 | partial | see EX-002 |
| MC-002-D03 | partial | open exception EX-002 |
| MC-002-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-003-04 | partial | owner/reviewer are role placeholders pending EX-006 |
| MC-003-33 | open-approval | EX-006 |
| MC-003-36 | open-approval | EX-006 |
| MC-003-E01 | open-approval | requires named approver (EX-006) |
| MC-003-E03 | open-approval | requires named approver (EX-006) |
| MC-003-D03 | partial | open exception EX-006 |
| MC-003-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-004-01 | open-approval | backend selection is an owner decision |
| MC-004-02 | blocked-external | blocked (EX-001) |
| MC-004-03 | partial | N/N-1 policy stated; concrete versions pending pin |
| MC-004-04 | blocked-external | blocked (EX-001) |
| MC-004-05 | blocked-external | blocked (EX-001) |
| MC-004-06 | blocked-external | blocked (EX-001) |
| MC-004-11 | blocked-external | EX-001 |
| MC-004-12 | blocked-external | EX-001 |
| MC-004-13 | blocked-external | EX-001 |
| MC-004-14 | blocked-external | EX-001 |
| MC-004-16 | blocked-external | EX-001 |
| MC-004-17 | blocked-external | EX-001 |
| MC-004-19 | blocked-external | EX-001 |
| MC-004-20 | blocked-external | EX-001 |
| MC-004-21 | blocked-external | EX-001 |
| MC-004-22 | blocked-external | EX-001 |
| MC-004-23 | blocked-external | EX-001 |
| MC-004-24 | blocked-external | EX-001 |
| MC-004-25 | blocked-external | EX-001 |
| MC-004-26 | blocked-external | EX-001 |
| MC-004-27 | blocked-external | EX-001 |
| MC-004-28 | blocked-external | EX-001 |
| MC-004-32 | open-approval | EX-006 |
| MC-004-33 | blocked-external | EX-001 |
| MC-004-35 | open-approval | EX-006 |
| MC-004-E01 | open-approval | requires named approver (EX-006) |
| MC-004-E03 | open-approval | requires named approver (EX-006) |
| MC-004-E04 | partial | boundary only |
| MC-004-D01 | blocked-external | see component status |
| MC-004-D02 | blocked-external | see EX-001 |
| MC-004-D03 | partial | open exception EX-001 |
| MC-004-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-005-02 | blocked-external | discovery/pooling apply to a remote backend |
| MC-005-03 | partial | local engine is canonical; remote translation pending |
| MC-005-05 | partial | request-level instrumentation; per-backend-call metrics pending remote adapter |
| MC-005-06 | blocked-external | no multi-node deployment |
| MC-005-33 | open-approval | EX-006 |
| MC-005-36 | open-approval | EX-006 |
| MC-005-E01 | open-approval | requires named approver (EX-006) |
| MC-005-E03 | open-approval | requires named approver (EX-006) |
| MC-005-D01 | partial | see component status |
| MC-005-D02 | partial | see EX-001 |
| MC-005-D03 | partial | open exception EX-001 |
| MC-005-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-006-34 | open-approval | EX-006 |
| MC-006-37 | open-approval | EX-006 |
| MC-006-E01 | open-approval | requires named approver (EX-006) |
| MC-006-E03 | open-approval | requires named approver (EX-006) |
| MC-006-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-007-01 | blocked-external | blocked (EX-001) |
| MC-007-02 | blocked-external | blocked (EX-001) |
| MC-007-03 | blocked-external | blocked (EX-001) |
| MC-007-04 | blocked-external | needs multi-node backend |
| MC-007-05 | blocked-external | blocked (EX-001) |
| MC-007-06 | blocked-external | needs multi-node backend |
| MC-007-07 | blocked-external | blocked (EX-001) |
| MC-007-12 | blocked-external | EX-001 |
| MC-007-13 | blocked-external | EX-001 |
| MC-007-14 | blocked-external | EX-001 |
| MC-007-15 | blocked-external | EX-001 |
| MC-007-17 | blocked-external | EX-001 |
| MC-007-18 | blocked-external | EX-001 |
| MC-007-20 | blocked-external | EX-001 |
| MC-007-21 | blocked-external | EX-001 |
| MC-007-22 | blocked-external | EX-001 |
| MC-007-23 | blocked-external | EX-001 |
| MC-007-24 | blocked-external | EX-001 |
| MC-007-25 | blocked-external | EX-001 |
| MC-007-26 | blocked-external | EX-001 |
| MC-007-27 | blocked-external | EX-001 |
| MC-007-28 | blocked-external | EX-001 |
| MC-007-29 | blocked-external | EX-001 |
| MC-007-33 | open-approval | EX-006 |
| MC-007-34 | blocked-external | EX-001 |
| MC-007-36 | open-approval | EX-006 |
| MC-007-E01 | open-approval | requires named approver (EX-006) |
| MC-007-E02 | blocked-external | no executable target |
| MC-007-E03 | open-approval | requires named approver (EX-006) |
| MC-007-E04 | partial | boundary only |
| MC-007-D01 | blocked-external | see component status |
| MC-007-D02 | blocked-external | see EX-001 |
| MC-007-D03 | partial | open exception EX-001 |
| MC-007-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-008-33 | open-approval | EX-006 |
| MC-008-36 | open-approval | EX-006 |
| MC-008-E01 | open-approval | requires named approver (EX-006) |
| MC-008-E03 | open-approval | requires named approver (EX-006) |
| MC-008-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-009-33 | open-approval | EX-006 |
| MC-009-36 | open-approval | EX-006 |
| MC-009-E01 | open-approval | requires named approver (EX-006) |
| MC-009-E03 | open-approval | requires named approver (EX-006) |
| MC-009-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-010-33 | open-approval | EX-006 |
| MC-010-36 | open-approval | EX-006 |
| MC-010-E01 | open-approval | requires named approver (EX-006) |
| MC-010-E03 | open-approval | requires named approver (EX-006) |
| MC-010-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-011-33 | open-approval | EX-006 |
| MC-011-36 | open-approval | EX-006 |
| MC-011-E01 | open-approval | requires named approver (EX-006) |
| MC-011-E03 | open-approval | requires named approver (EX-006) |
| MC-011-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-012-33 | open-approval | EX-006 |
| MC-012-36 | open-approval | EX-006 |
| MC-012-E01 | open-approval | requires named approver (EX-006) |
| MC-012-E03 | open-approval | requires named approver (EX-006) |
| MC-012-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-013-33 | open-approval | EX-006 |
| MC-013-36 | open-approval | EX-006 |
| MC-013-E01 | open-approval | requires named approver (EX-006) |
| MC-013-E03 | open-approval | requires named approver (EX-006) |
| MC-013-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-014-33 | open-approval | EX-006 |
| MC-014-36 | open-approval | EX-006 |
| MC-014-E01 | open-approval | requires named approver (EX-006) |
| MC-014-E03 | open-approval | requires named approver (EX-006) |
| MC-014-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-015-33 | open-approval | EX-006 |
| MC-015-36 | open-approval | EX-006 |
| MC-015-E01 | open-approval | requires named approver (EX-006) |
| MC-015-E03 | open-approval | requires named approver (EX-006) |
| MC-015-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-016-03 | partial | txn/request id carried; actor identity kept in audit, not in events (tenant privacy) |
| MC-016-33 | open-approval | EX-006 |
| MC-016-36 | open-approval | EX-006 |
| MC-016-E01 | open-approval | requires named approver (EX-006) |
| MC-016-E03 | open-approval | requires named approver (EX-006) |
| MC-016-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-017-33 | open-approval | EX-006 |
| MC-017-36 | open-approval | EX-006 |
| MC-017-E01 | open-approval | requires named approver (EX-006) |
| MC-017-E03 | open-approval | requires named approver (EX-006) |
| MC-017-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-018-33 | open-approval | EX-006 |
| MC-018-36 | open-approval | EX-006 |
| MC-018-E01 | open-approval | requires named approver (EX-006) |
| MC-018-E03 | open-approval | requires named approver (EX-006) |
| MC-018-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-019-33 | open-approval | EX-006 |
| MC-019-36 | open-approval | EX-006 |
| MC-019-E01 | open-approval | requires named approver (EX-006) |
| MC-019-E03 | open-approval | requires named approver (EX-006) |
| MC-019-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-020-33 | open-approval | EX-006 |
| MC-020-36 | open-approval | EX-006 |
| MC-020-E01 | open-approval | requires named approver (EX-006) |
| MC-020-E03 | open-approval | requires named approver (EX-006) |
| MC-020-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-021-33 | open-approval | EX-006 |
| MC-021-36 | open-approval | EX-006 |
| MC-021-E01 | open-approval | requires named approver (EX-006) |
| MC-021-E03 | open-approval | requires named approver (EX-006) |
| MC-021-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-022-04 | partial | hot reload supported; automated issuance belongs to platform PKI |
| MC-022-05 | partial | trust-anchor rotation documented; no automated test |
| MC-022-33 | open-approval | EX-006 |
| MC-022-36 | open-approval | EX-006 |
| MC-022-E01 | open-approval | requires named approver (EX-006) |
| MC-022-E03 | open-approval | requires named approver (EX-006) |
| MC-022-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-023-33 | open-approval | EX-006 |
| MC-023-36 | open-approval | EX-006 |
| MC-023-E01 | open-approval | requires named approver (EX-006) |
| MC-023-E03 | open-approval | requires named approver (EX-006) |
| MC-023-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-024-02 | partial | secret refs + file mode checks; KMS/HSM unwrap is platform-provided |
| MC-024-33 | open-approval | EX-006 |
| MC-024-36 | open-approval | EX-006 |
| MC-024-E01 | open-approval | requires named approver (EX-006) |
| MC-024-E03 | open-approval | requires named approver (EX-006) |
| MC-024-D01 | partial | see component status |
| MC-024-D02 | partial | see None |
| MC-024-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-025-33 | open-approval | EX-006 |
| MC-025-36 | open-approval | EX-006 |
| MC-025-E01 | open-approval | requires named approver (EX-006) |
| MC-025-E03 | open-approval | requires named approver (EX-006) |
| MC-025-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-026-33 | open-approval | EX-006 |
| MC-026-36 | open-approval | EX-006 |
| MC-026-E01 | open-approval | requires named approver (EX-006) |
| MC-026-E03 | open-approval | requires named approver (EX-006) |
| MC-026-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-027-05 | blocked-external | needs an N-1 server build to run mixed |
| MC-027-06 | partial | store formats unchanged vs 4.2 (no persistent format existed) |
| MC-027-33 | open-approval | EX-006 |
| MC-027-36 | open-approval | EX-006 |
| MC-027-E01 | open-approval | requires named approver (EX-006) |
| MC-027-E03 | open-approval | requires named approver (EX-006) |
| MC-027-D01 | partial | see component status |
| MC-027-D02 | partial | see EX-004 |
| MC-027-D03 | partial | open exception EX-004 |
| MC-027-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-028-34 | open-approval | EX-006 |
| MC-028-37 | open-approval | EX-006 |
| MC-028-E01 | open-approval | requires named approver (EX-006) |
| MC-028-E03 | open-approval | requires named approver (EX-006) |
| MC-028-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-029-33 | open-approval | EX-006 |
| MC-029-36 | open-approval | EX-006 |
| MC-029-E01 | open-approval | requires named approver (EX-006) |
| MC-029-E03 | open-approval | requires named approver (EX-006) |
| MC-029-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-030-06 | partial | dependency loss/overload/shutdown tested; quorum loss n/a until EX-001 |
| MC-030-32 | open-approval | EX-006 |
| MC-030-35 | open-approval | EX-006 |
| MC-030-E01 | open-approval | requires named approver (EX-006) |
| MC-030-E03 | open-approval | requires named approver (EX-006) |
| MC-030-D02 | partial | see EX-001 |
| MC-030-D03 | partial | open exception EX-001 |
| MC-030-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-031-33 | open-approval | EX-006 |
| MC-031-36 | open-approval | EX-006 |
| MC-031-E01 | open-approval | requires named approver (EX-006) |
| MC-031-E03 | open-approval | requires named approver (EX-006) |
| MC-031-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-032-33 | open-approval | EX-006 |
| MC-032-36 | open-approval | EX-006 |
| MC-032-E01 | open-approval | requires named approver (EX-006) |
| MC-032-E03 | open-approval | requires named approver (EX-006) |
| MC-032-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-033-33 | open-approval | EX-006 |
| MC-033-36 | open-approval | EX-006 |
| MC-033-E01 | open-approval | requires named approver (EX-006) |
| MC-033-E03 | open-approval | requires named approver (EX-006) |
| MC-033-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-034-33 | open-approval | EX-006 |
| MC-034-36 | open-approval | EX-006 |
| MC-034-E01 | open-approval | requires named approver (EX-006) |
| MC-034-E03 | open-approval | requires named approver (EX-006) |
| MC-034-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-035-06 | partial | records carry revisions/policy/config hash; replay tooling not provided |
| MC-035-33 | open-approval | EX-006 |
| MC-035-36 | open-approval | EX-006 |
| MC-035-E01 | open-approval | requires named approver (EX-006) |
| MC-035-E03 | open-approval | requires named approver (EX-006) |
| MC-035-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-036-33 | open-approval | EX-006 |
| MC-036-36 | open-approval | EX-006 |
| MC-036-E01 | open-approval | requires named approver (EX-006) |
| MC-036-E03 | open-approval | requires named approver (EX-006) |
| MC-036-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-037-33 | open-approval | EX-006 |
| MC-037-36 | open-approval | EX-006 |
| MC-037-E01 | open-approval | requires named approver (EX-006) |
| MC-037-E03 | open-approval | requires named approver (EX-006) |
| MC-037-D01 | partial | see component status |
| MC-037-D02 | partial | see EX-005 |
| MC-037-D03 | partial | open exception EX-005 |
| MC-037-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-038-33 | open-approval | EX-006 |
| MC-038-36 | open-approval | EX-006 |
| MC-038-E01 | open-approval | requires named approver (EX-006) |
| MC-038-E03 | open-approval | requires named approver (EX-006) |
| MC-038-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-039-34 | open-approval | EX-006 |
| MC-039-37 | open-approval | EX-006 |
| MC-039-E01 | open-approval | requires named approver (EX-006) |
| MC-039-E03 | open-approval | requires named approver (EX-006) |
| MC-039-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-040-04 | partial | routing change documented; not automated |
| MC-040-33 | open-approval | EX-006 |
| MC-040-36 | open-approval | EX-006 |
| MC-040-E01 | open-approval | requires named approver (EX-006) |
| MC-040-E03 | open-approval | requires named approver (EX-006) |
| MC-040-D01 | partial | see component status |
| MC-040-D02 | partial | see EX-001 |
| MC-040-D03 | partial | open exception EX-001 |
| MC-040-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-041-33 | open-approval | EX-006 |
| MC-041-36 | open-approval | EX-006 |
| MC-041-E01 | open-approval | requires named approver (EX-006) |
| MC-041-E03 | open-approval | requires named approver (EX-006) |
| MC-041-D01 | partial | see component status |
| MC-041-D02 | partial | see EX-004 |
| MC-041-D03 | partial | open exception EX-004 |
| MC-041-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-042-04 | partial | CPU/RSS/FD/threads recorded; storage IOPS and network not measured |
| MC-042-34 | open-approval | EX-006 |
| MC-042-35 | partial | EX-005 |
| MC-042-37 | open-approval | EX-006 |
| MC-042-E01 | open-approval | requires named approver (EX-006) |
| MC-042-E03 | open-approval | requires named approver (EX-006) |
| MC-042-D01 | partial | see component status |
| MC-042-D02 | partial | see EX-005 |
| MC-042-D03 | partial | open exception EX-005 |
| MC-042-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-043-05 | partial | process crash injected; node/network faults need multi-member backend |
| MC-043-33 | open-approval | EX-006 |
| MC-043-36 | open-approval | EX-006 |
| MC-043-E01 | open-approval | requires named approver (EX-006) |
| MC-043-E03 | open-approval | requires named approver (EX-006) |
| MC-043-D02 | partial | see EX-001 |
| MC-043-D03 | partial | open exception EX-001 |
| MC-043-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-044-01 | partial | network partition/delay only via transport interruption |
| MC-044-33 | open-approval | EX-006 |
| MC-044-36 | open-approval | EX-006 |
| MC-044-E01 | open-approval | requires named approver (EX-006) |
| MC-044-E03 | open-approval | requires named approver (EX-006) |
| MC-044-D02 | partial | see EX-001 |
| MC-044-D03 | partial | open exception EX-001 |
| MC-044-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-045-33 | open-approval | EX-006 |
| MC-045-36 | open-approval | EX-006 |
| MC-045-E01 | open-approval | requires named approver (EX-006) |
| MC-045-E03 | open-approval | requires named approver (EX-006) |
| MC-045-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-046-01 | partial | protocol-level versions only |
| MC-046-02 | blocked-external | adjacent layers not supplied |
| MC-046-03 | blocked-external | blocked (EX-004) |
| MC-046-04 | partial | backend-unavailable path tested; INV-04/INV-07/PLN-03 not available |
| MC-046-05 | blocked-external | no N-1 builds of neighbours |
| MC-046-06 | blocked-external | blocked (EX-004) |
| MC-046-07 | blocked-external | blocked (EX-004) |
| MC-046-12 | blocked-external | EX-004 |
| MC-046-13 | blocked-external | EX-004 |
| MC-046-14 | blocked-external | EX-004 |
| MC-046-15 | blocked-external | EX-004 |
| MC-046-17 | blocked-external | EX-004 |
| MC-046-18 | blocked-external | EX-004 |
| MC-046-20 | blocked-external | EX-004 |
| MC-046-21 | blocked-external | EX-004 |
| MC-046-22 | blocked-external | EX-004 |
| MC-046-23 | blocked-external | EX-004 |
| MC-046-24 | blocked-external | EX-004 |
| MC-046-25 | blocked-external | EX-004 |
| MC-046-26 | blocked-external | EX-004 |
| MC-046-27 | blocked-external | EX-004 |
| MC-046-28 | blocked-external | EX-004 |
| MC-046-29 | blocked-external | EX-004 |
| MC-046-33 | open-approval | EX-006 |
| MC-046-34 | blocked-external | EX-004 |
| MC-046-36 | open-approval | EX-006 |
| MC-046-E01 | open-approval | requires named approver (EX-006) |
| MC-046-E02 | blocked-external | no executable target |
| MC-046-E03 | open-approval | requires named approver (EX-006) |
| MC-046-E04 | partial | boundary only |
| MC-046-D01 | blocked-external | see component status |
| MC-046-D02 | blocked-external | see EX-004 |
| MC-046-D03 | partial | open exception EX-004 |
| MC-046-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-047-05 | partial | vectors run in-process and via the reference client; no independent implementation available |
| MC-047-33 | open-approval | EX-006 |
| MC-047-36 | open-approval | EX-006 |
| MC-047-E01 | open-approval | requires named approver (EX-006) |
| MC-047-E03 | open-approval | requires named approver (EX-006) |
| MC-047-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-048-03 | partial | hash lock pending EX-009 |
| MC-048-06 | partial | HMAC signing when key configured; no Sigstore/KMS identity |
| MC-048-34 | open-approval | EX-006 |
| MC-048-37 | open-approval | EX-006 |
| MC-048-E01 | open-approval | requires named approver (EX-006) |
| MC-048-E03 | open-approval | requires named approver (EX-006) |
| MC-048-D01 | partial | see component status |
| MC-048-D02 | partial | see EX-008 |
| MC-048-D03 | partial | open exception EX-008 |
| MC-048-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-049-01 | partial | exact versions; hashes pending |
| MC-049-04 | partial | pip-audit in CI; no malware/licence-policy scanner |
| MC-049-06 | partial | HMAC-signed digests; see EX-008 |
| MC-049-34 | open-approval | EX-006 |
| MC-049-37 | open-approval | EX-006 |
| MC-049-E01 | open-approval | requires named approver (EX-006) |
| MC-049-E03 | open-approval | requires named approver (EX-006) |
| MC-049-D01 | partial | see component status |
| MC-049-D02 | partial | see EX-009 |
| MC-049-D03 | partial | open exception EX-009 |
| MC-049-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-050-34 | open-approval | EX-006 |
| MC-050-37 | open-approval | EX-006 |
| MC-050-E01 | open-approval | requires named approver (EX-006) |
| MC-050-E03 | open-approval | requires named approver (EX-006) |
| MC-050-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-051-34 | open-approval | EX-006 |
| MC-051-37 | open-approval | EX-006 |
| MC-051-E01 | open-approval | requires named approver (EX-006) |
| MC-051-E03 | open-approval | requires named approver (EX-006) |
| MC-051-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
| MC-052-01 | open-approval | role holders proposed |
| MC-052-02 | open-approval | ADRs drafted, status Proposed |
| MC-052-03 | open-approval | implemented + tested |
| MC-052-04 | open-approval | implemented + tested |
| MC-052-05 | open-approval | outbound licence not selected (EX-007) |
| MC-052-06 | open-approval | implemented + tested |
| MC-052-07 | open-approval | implemented + tested |
| MC-052-08 | open-approval | implemented + tested |
| MC-052-34 | open-approval | EX-006 |
| MC-052-37 | open-approval | EX-006 |
| MC-052-E01 | open-approval | requires named approver (EX-006) |
| MC-052-E03 | open-approval | requires named approver (EX-006) |
| MC-052-D01 | open-approval | see component status |
| MC-052-D02 | partial | see EX-006 |
| MC-052-D03 | partial | open exception EX-006 |
| MC-052-D04 | partial | evidence HMAC-signed only when key configured (EX-008) |
