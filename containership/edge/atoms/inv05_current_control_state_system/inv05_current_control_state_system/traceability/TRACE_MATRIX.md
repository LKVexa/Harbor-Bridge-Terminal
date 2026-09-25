# Requirements-to-evidence traceability matrix

Generated from `traceability/trace_matrix.json` for version 4.3.0. Do not edit by hand (`python tools/build_trace.py`).

| ID | Status | Implementation | Tests | Evidence | Exception |
|---|---|---|---|---|---|
| INV-05-C001 | verified | store.py::ControlStore<br>contract.py::build | 30 tests | docs/ARCHITECTURE.md |  |
| INV-05-C002 | verified | contract.py::build | 2 tests | docs/ARCHITECTURE.md |  |
| INV-05-C003 | verified | contract.py::build<br>backend.py::ExternalBackendContract<br>replication.py::ReplicationSource | 4 tests | docs/ARCHITECTURE.md |  |
| INV-05-C004 | verified | store.py::ControlStore.revision | 7 tests | docs/ARCHITECTURE.md |  |
| INV-05-C005 | verified | store.py::ControlStore | 2 tests | docs/ARCHITECTURE.md |  |
| INV-05-C006 | verified | security.py::Namespace<br>service.py::ControlStateService._map_key | 5 tests | docs/ARCHITECTURE.md |  |
| INV-05-C007 | verified | contract.py::build | 9 tests | docs/ARCHITECTURE.md |  |
| INV-05-C008 | verified | config.py::build | 1 tests | docs/ARCHITECTURE.md |  |
| INV-05-C009 | partial | docs/GOVERNANCE.md | 0 tests | docs/GOVERNANCE.md | EX-006 |
| INV-05-C010 | partial | docs/adr/ADR-001-scope-and-role.md | 0 tests | docs/adr/ADR-001-scope-and-role.md<br>docs/adr/ADR-002-backend-and-consensus.md | EX-006 |
| INV-05-C011 | verified | store.py::ControlStore.txn | 42 tests | docs/REQUIREMENTS.md |  |
| INV-05-C012 | verified | config.py::SCHEMA | 4 tests | docs/REQUIREMENTS.md |  |
| INV-05-C013 | verified-single-member | wal.py::DurableStore<br>bench.py::run | 18 tests | docs/REQUIREMENTS.md<br>evidence/bench_smoke.json | EX-001 |
| INV-05-C014 | verified | errors.py::ERROR_CATALOG | 3 tests | docs/REQUIREMENTS.md |  |
| INV-05-C015 | verified | service.py::ControlStateService.readiness<br>watch.py::Watcher | 17 tests | docs/ARCHITECTURE.md |  |
| INV-05-C016 | verified | schema.py::check_message | 3 tests | docs/COMPATIBILITY.md |  |
| INV-05-C017 | verified | limits.py::Limits<br>limits.py::TokenBucket | 2 tests | docs/REQUIREMENTS.md |  |
| INV-05-C018 | verified | client.py::Mirror | 3 tests | docs/ARCHITECTURE.md |  |
| INV-05-C019 | verified | store.py::ControlStore._commit | 1 tests | docs/ARCHITECTURE.md |  |
| INV-05-C020 | verified | tools_check.py::check_trace | 10 tests | traceability/trace_matrix.json<br>traceability/TRACE_MATRIX.md |  |
| INV-05-C021 | verified | server.py::_Handler | 14 tests | docs/INTERFACES.md |  |
| INV-05-C022 | verified | schema.py::MESSAGES | 3 tests | conformance/schema_lock.json<br>conformance/golden_messages_v1.json |  |
| INV-05-C023 | verified | security.py::MTLSAuthenticator<br>security.py::TokenAuthenticator | 5 tests | docs/INTERFACES.md |  |
| INV-05-C024 | verified | security.py::Authorizer | 4 tests | docs/INTERFACES.md |  |
| INV-05-C025 | verified | service.py::OP_CLASSES<br>client.py::Client.call<br>watch.py::Watcher | 4 tests | docs/INTERFACES.md |  |
| INV-05-C026 | verified | errors.py::StateError | 2 tests | conformance/error_catalog_lock.json |  |
| INV-05-C027 | verified | schema.py::negotiate | 3 tests | docs/COMPATIBILITY.md |  |
| INV-05-C028 | verified | limits.py::Limits | 2 tests | docs/INTERFACES.md |  |
| INV-05-C029 | verified | conformance/runner.py::main | 2 tests | conformance/vectors_v1.json<br>evidence/conformance.json |  |
| INV-05-C030 | partial | replication.py::ReplicaApplier<br>server.py::ControlStateHTTPServer | 18 tests | docs/COMPATIBILITY.md | EX-004 |
| INV-05-C031 | blocked-external | backend.py::ExternalBackendContract | 4 tests | deploy/backend_pin.json<br>docs/adr/ADR-002-backend-and-consensus.md | EX-001 |
| INV-05-C032 | verified | config.py::EffectiveConfig<br>wal.py::DurableStore | 4 tests | deploy/Dockerfile<br>docs/ROLLOUT.md |  |
| INV-05-C033 | verified | config.py::SCHEMA | 1 tests | deploy/config/base.json |  |
| INV-05-C034 | verified | config.py::build | 1 tests |  |  |
| INV-05-C035 | verified | config.py::load_layers | 1 tests | deploy/config/prod.json<br>deploy/config/site-a.json |  |
| INV-05-C036 | verified | config.py::EffectiveConfig<br>bootstrap.py::build_service | 2 tests |  |  |
| INV-05-C037 | verified | config.py::EffectiveConfig.restart_required_diff<br>security.py::Authorizer.rollout | 2 tests |  |  |
| INV-05-C038 | verified | security.py::Authorizer.rollback | 1 tests | docs/ROLLOUT.md |  |
| INV-05-C039 | verified | security.py::SecretProvider<br>security.py::redact | 4 tests | docs/adr/ADR-005-security.md |  |
| INV-05-C040 | verified | bootstrap.py::build_service | 2 tests | docs/operations/RUNBOOK_DAY0.md |  |
| INV-05-C041 | partial | docs/THREAT_MODEL.md | 15 tests | docs/THREAT_MODEL.md | EX-006 |
| INV-05-C042 | verified | security.py::DEFAULT_POLICY | 5 tests | deploy/inv05.service<br>deploy/k8s/statefulset.yaml |  |
| INV-05-C043 | verified | security.py::SecretProvider.get | 1 tests | deploy/inv05.service |  |
| INV-05-C044 | verified | security.py::MTLSAuthenticator.authenticate | 14 tests |  |  |
| INV-05-C045 | partial | backend.py::ExternalBackendContract.verify_artifact<br>tools_check.py::manifest | 1 tests | evidence/gate_report.json | EX-008 |
| INV-05-C046 | verified | service.py::ControlStateService._map_op | 6 tests |  |  |
| INV-05-C047 | verified | wal.py::Sealer<br>security.py::server_tls_context | 2 tests | docs/adr/ADR-005-security.md |  |
| INV-05-C048 | verified | bootstrap.py::build_service | 1 tests | docs/THREAT_MODEL.md |  |
| INV-05-C049 | verified | audit.py::AuditLog | 2 tests | docs/operations/AUDIT_RETENTION.md |  |
| INV-05-C050 | verified | security.py::TokenAuthenticator | 7 tests | docs/THREAT_MODEL.md |  |
| INV-05-C051 | verified | wal.py::DurableStore | 2 tests | docs/FAULT_CATALOG.md |  |
| INV-05-C052 | verified | service.py::ControlStateService.liveness | 3 tests | observability/alerts/inv05-rules.yml |  |
| INV-05-C053 | verified | client.py::Client.call | 1 tests |  |  |
| INV-05-C054 | verified | limits.py::ConcurrencyGate<br>limits.py::TokenBucket | 1 tests |  |  |
| INV-05-C055 | partial | replication.py::ReplicaApplier | 1 tests | docs/DR_PLAN.md | EX-001 |
| INV-05-C056 | verified | service.py::ControlStateService.readiness | 1 tests |  |  |
| INV-05-C057 | verified | wal.py::DurableStore.open | 12 tests | docs/adr/ADR-004-durability.md |  |
| INV-05-C058 | verified-single-member | store.py::ControlStore.lease_grant | 2 tests | docs/CONSENSUS_CONTRACT.md | EX-001 |
| INV-05-C059 | verified | service.py::ControlStateService.quarantine<br>service.py::ControlStateService.break_glass | 7 tests |  |  |
| INV-05-C060 | verified | wal.py::SimulatedCrash | 14 tests | docs/FAULT_CATALOG.md |  |
| INV-05-C061 | partial | bench.py::run | 0 tests | evidence/bench_smoke.json<br>docs/CAPACITY.md | EX-005 |
| INV-05-C062 | partial | bench.py::run | 0 tests | docs/CAPACITY.md | EX-005 |
| INV-05-C063 | partial | bench.py::run | 1 tests | docs/CAPACITY.md | EX-005 |
| INV-05-C064 | partial | limits.py::TokenBucket | 1 tests | docs/CAPACITY.md | EX-005 |
| INV-05-C065 | verified | store.py::ControlStore.range | 0 tests | docs/CAPACITY.md |  |
| INV-05-C066 | verified | store.py::ControlStore.txn | 1 tests | docs/CAPACITY.md |  |
| INV-05-C067 | verified | limits.py::Limits<br>watch.py::Watcher | 13 tests |  |  |
| INV-05-C068 | partial | bench.py::run | 0 tests | docs/CAPACITY.md | EX-005 |
| INV-05-C069 | partial | observability.py::METRIC_CATALOG | 0 tests | docs/CAPACITY.md | EX-005 |
| INV-05-C070 | verified | tools/ci_gate.py | 10 tests | evidence/gate_report.json |  |
| INV-05-C071 | verified | service.py::ControlStateService.version | 4 tests |  |  |
| INV-05-C072 | verified | observability.py::Metrics | 1 tests |  |  |
| INV-05-C073 | verified | observability.py::StructuredLogger | 1 tests |  |  |
| INV-05-C074 | verified | observability.py::Tracer | 1 tests |  |  |
| INV-05-C075 | verified | observability.py::Metrics._key | 1 tests | docs/TELEMETRY_POLICY.md |  |
| INV-05-C076 | verified | observability.py::ExplainStore | 1 tests |  |  |
| INV-05-C077 | verified | service.py::ControlStateService.get_explanation | 1 tests |  |  |
| INV-05-C078 | partial | service.py::BUILD_INFO | 1 tests |  | EX-004 |
| INV-05-C079 | verified | observability.py::METRIC_CATALOG | 0 tests | docs/TELEMETRY_POLICY.md |  |
| INV-05-C080 | partial | observability.py::Metrics | 0 tests | observability/dashboards/overview.json<br>observability/alerts/inv05-rules.yml | EX-005 |
| INV-05-C081 | verified | store.py::ControlStore | 36 tests |  |  |
| INV-05-C082 | verified | conformance/runner.py::run_file | 12 tests | conformance/vectors_v1.json |  |
| INV-05-C083 | partial | server.py::ControlStateHTTPServer | 14 tests |  | EX-004 |
| INV-05-C084 | partial | backend.py::runtime_self_test | 2 tests | .github/workflows/ci.yml | EX-004 |
| INV-05-C085 | verified | schema.py::loads | 6 tests |  |  |
| INV-05-C086 | verified | linearizability.py::check | 7 tests |  |  |
| INV-05-C087 | verified | security.py::Authorizer | 10 tests | docs/THREAT_MODEL.md |  |
| INV-05-C088 | partial | bench.py::run | 0 tests | evidence/bench_smoke.json | EX-005 |
| INV-05-C089 | partial | replication.py::sync_once<br>backup.py::restore_backup | 11 tests | docs/DR_PLAN.md | EX-001 |
| INV-05-C090 | verified | tools/ci_gate.py | 10 tests | evidence/gate_report.json |  |
| INV-05-C091 | verified | contract.py::build | 0 tests | docs/REQUIREMENTS.md<br>observability/alerts/inv05-rules.yml |  |
| INV-05-C092 | verified | service.py::ControlStateService.break_glass | 1 tests | docs/ROLLOUT.md |  |
| INV-05-C093 | partial | backend.py::SUPPORTED_PYTHON | 0 tests | docs/COMPATIBILITY.md | EX-001 |
| INV-05-C094 | verified | tools_check.py::sbom | 0 tests | docs/SECURITY_POLICY.md |  |
| INV-05-C095 | verified | backup.py::create_backup<br>backup.py::restore_backup | 4 tests | docs/DR_PLAN.md<br>evidence/restore_drill.json |  |
| INV-05-C096 | verified | bootstrap.py::main | 0 tests | docs/operations/RUNBOOK_DAY0.md<br>docs/operations/RUNBOOK_DAY1.md<br>docs/operations/RUNBOOK_DAY2.md |  |
| INV-05-C097 | verified | service.py::ControlStateService.quarantine | 0 tests | docs/operations/INCIDENTS.md |  |
| INV-05-C098 | partial | docs/GOVERNANCE.md | 0 tests | docs/GOVERNANCE.md | EX-006 |
| INV-05-C099 | verified | tools_check.py::check_exceptions | 10 tests | docs/EXCEPTIONS.json |  |
| INV-05-C100 | partial | tools/release_gate.py | 10 tests | evidence/gate_report.json | EX-001 |

Status totals: blocked-external: 1, partial: 21, verified: 76, verified-single-member: 2
