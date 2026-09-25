# INV-14 v4.3.0 component specifications

Generated from `tools/component_specs.py` (machine form: `docs/COMPONENTS.json`). Owner for every component: **UNASSIGNED**.

<a id="c01"></a>
## 01 — Pinned pk_core runtime/dependency package

- **Kind:** runtime; **modules:** core_probe.py; **artifacts:** deps/pk_core.lock.json
- **Boundary / non-goals:** Owns the declaration and verification of pk_core. Does not own pk_core itself, its build or its index.
- **Ceilings:** Lock file read once; tree digest bounded by the core's file count.
- **Sources of truth:** `{"constant": "REQUIRED_SYMBOLS", "external_policy": "deps/pk_core.lock.json", "runtime": "installed pk_core tree"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed on every dependency condition; no degraded mode
- **Interface:** core_probe.probe() -> {ok, code, core}
- **Concurrency/idempotency:** stateless
- **Signals:** diagnostics.pk_core; **correlation:** core version/hash in diagnostics; **runbook:** R0
- **Stable codes:** PK_CORE_*

| ID | Requirement | Evidence |
|---|---|---|
| R01-01 | The lock MUST name pk_core with an exact X.Y.Z version, immutable source and tree sha256; floating/mutable pins MUST be rejected. | T:C01PkCorePin.test_c01_floating_and_mutable_pins_rejected |
| R01-02 | The probe MUST fail closed with a stable code for unpinned, absent, wrong-version, hash-mismatched, API-incompatible or wrong-interpreter cores. | T:C01PkCorePin |
| R01-03 | Diagnostics MUST NOT disclose local filesystem paths. | T:C01PkCorePin.test_c01_probe_absent_version_hash_api_ok_paths |
| R01-04 | Release MUST be BLOCKED while the lock is UNRESOLVED. | T:C27ReleasePipeline.test_c27_missing_pk_core_blocks_release_exit_2 |

Threats: **substituted or tampered core** → tree sha256 + version equality (T:C01PkCorePin.test_c01_probe_absent_version_hash_api_ok_paths); **silent skip when core absent** → gate exits 2 (T:C27ReleasePipeline)

Blocked by: The exact compatible pk_core was not supplied; lock is UNRESOLVED

<a id="c02"></a>
## 02 — WASI 0.2 / wasi:io integration adapter

- **Kind:** runtime; **modules:** wasi_adapter.py, clock.py; **artifacts:** wit/inv14-legacy-poll.wit
- **Boundary / non-goals:** Owns the translation PK_POLL/1 <-> wasi:io/poll. Does not own the runtime, handles' underlying resources or component compilation.
- **Ceilings:** Set <= max_pollables; timeout <= max_timeout_ticks and 60 s.
- **Sources of truth:** `{"constant": "WASI_IO/WASI_CLOCK ids", "config": "PK_CLOCK_CONFIG/1", "runtime": "host handles"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed on invalid input; real-runtime gate BLOCKED
- **Interface:** WasiHost protocol (subscribe_duration, poll, drop, owner_of)
- **Concurrency/idempotency:** host-provided; reference host uses one condition variable
- **Signals:** same PK_POLL/1 result; **correlation:** result carries owner/set_size; **runbook:** R8
- **Stable codes:** PK_POLL_*

| ID | Requirement | Evidence |
|---|---|---|
| R02-01 | The adapter MUST append a monotonic-clock timer pollable and map a timer-only result to timed_out. | T:C02WasiAdapter.test_c02_timeout_maps_timer_index_to_timed_out |
| R02-02 | ready_indexes MUST exclude the timer and match the Python reference semantics. | T:C02WasiAdapter.test_c02_ready_indexes_exclude_timer_and_match_python_semantics |
| R02-03 | Empty sets MUST be refused before wasi:io/poll can trap; the timer handle MUST be dropped on every path. | T:C02WasiAdapter.test_c02_empty_set_refused_before_trap_and_timer_dropped |
| R02-04 | Foreign/duplicate/over-limit requests MUST map to the canonical PK_POLL_ERROR/1 codes. | T:C02WasiAdapter.test_c02_foreign_duplicate_and_limit_refusals |
| R02-05 | Interop MUST be proven on a real WASI 0.2 runtime before release. | G:wasi_0_2_interop |

Threats: **foreign handle smuggled into poll** → owner_of check before subscribe (T:C02WasiAdapter.test_c02_foreign_duplicate_and_limit_refusals)

Blocked by: No WASI 0.2 runtime (wasmtime/jco) or compiled component fixture in this environment; No WIT parser/toolchain (wasm-tools) available to validate the WIT in CI

<a id="c03"></a>
## 03 — Versioned WIT/JSON schema contracts

- **Kind:** artifact; **modules:** schema_check.py, tools/gen_contracts.py; **artifacts:** wit/inv14-legacy-poll.wit, schemas/pk_poll.schema.json, schemas/pk_pollable.schema.json, schemas/pk_poll_error.schema.json, schemas/pk_poll_metrics.schema.json, schemas/error_codes.json, docs/CONTRACT_POLICY.md
- **Boundary / non-goals:** Owns the serialized contract. Does not own transport encodings beyond JSON and the component model.
- **Ceilings:** set_size <= 65536, strings <= 256, message <= 1024 (schema maxima).
- **Sources of truth:** `{"constant": "schema files", "generated": "error_codes.json, WIT enum, error schema enum"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** gate fails on drift
- **Interface:** schemas/*.json, wit/*.wit
- **Concurrency/idempotency:** static artifacts
- **Signals:** n/a (static); **correlation:** schema ids in every payload; **runbook:** R1
- **Stable codes:** (defines all)

| ID | Requirement | Evidence |
|---|---|---|
| R03-01 | Every PK_POLL/1, PK_POLLABLE/1, PK_POLL_ERROR/1, PK_POLL_METRICS/1 field MUST be defined in both WIT and JSON Schema and the two MUST agree. | T:C03Contracts.test_c03_wit_records_match_json_schemas |
| R03-02 | The error-code enumeration MUST be generated from source and the committed artifacts MUST be current. | T:C03Contracts.test_c03_generated_contracts_are_current<br>T:C03Contracts.test_c03_error_schema_enum_equals_code_registry |
| R03-03 | Every schema MUST carry an immutable version id; digests MUST appear in diagnostics. | T:C03Contracts.test_c03_every_schema_is_versioned<br>T:C00Diagnostics |
| R03-04 | The validator MUST fail closed on unsupported schema keywords. | T:C03Contracts.test_c03_validator_fails_closed_on_unknown_keyword |

Threats: **contract drift between code and schema** → generated artifacts + --check gate (T:C03Contracts)

<a id="c04"></a>
## 04 — INV-14 -> INV-15 migration bridge

- **Kind:** runtime; **modules:** migration.py; **artifacts:** —
- **Boundary / non-goals:** Owns shims and per-consumer stage machine. Does not own INV-15 or consumer code.
- **Ceilings:** One PollSet per forward shim; stage history bounded by transitions.
- **Sources of truth:** `{"runtime": "per-consumer MigrationStateMachine", "external_policy": "governance/MIGRATION_REGISTRY.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** refuse advancement on missing/failed parity
- **Interface:** PollableFuture, FuturePollable, MigrationStateMachine, parity_check
- **Concurrency/idempotency:** state machine guarded by a lock
- **Signals:** migration stage per consumer; **correlation:** consumer id + stage history; **runbook:** R7
- **Stable codes:** PK_MIGRATION_*

| ID | Requirement | Evidence |
|---|---|---|
| R04-01 | Forward and reverse shims MUST give the same ready/timeout outcomes as the legacy path (parity). | T:C04Migration.test_c04_parity_between_legacy_and_shim<br>T:C04Migration.test_c04_reverse_shim_signals_once_from_inv15_future |
| R04-02 | A consumer MUST NOT advance past DUAL_STACK/CANARY without a passing parity record; rollback MUST be legal from those stages only. | T:C04Migration.test_c04_state_machine_requires_parity_and_allows_rollback |
| R04-03 | Cancel on the forward shim MUST be idempotent. | T:C04Migration.test_c04_forward_shim_cancel_is_idempotent |
| R04-04 | A MIGRATED consumer MUST NOT silently regress to INV-14. | T:C13MigrationRegistry.test_c13_overdue_needs_live_waiver_and_migrated_regression_refused |
| R04-05 | The bridge MUST be proven against the real INV-15. | T:C20Adjacent.test_c20_inv15_future_satisfies_bridge_protocol |

Threats: **cutover without parity** → PK_MIGRATION_PARITY_REQUIRED (T:C04Migration.test_c04_state_machine_requires_parity_and_allows_rollback)

Blocked by: INV-15 real ABI not supplied; shims proven against the protocol only

<a id="c05"></a>
## 05 — Cancellation contract

- **Kind:** runtime; **modules:** polling.py; **artifacts:** —
- **Boundary / non-goals:** Owns caller-driven cancellation of one poll. Does not own INV-15 cancellation semantics.
- **Ceilings:** Reason truncated to 64 chars; one waiter per poll per token.
- **Sources of truth:** `{"constant": "precedence ready > cancel > timeout"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** PollSet.poll(..., cancel=CancelToken)
- **Concurrency/idempotency:** lock + durable Event registration
- **Signals:** polls_cancelled, outcome=cancelled; **correlation:** correlation_id added to error details by the service; **runbook:** R8
- **Stable codes:** PK_POLL_CANCELLED, PK_POLL_INVALID_CANCEL_TOKEN

| ID | Requirement | Evidence |
|---|---|---|
| R05-01 | A CancelToken MUST wake a blocked poll and raise PK_POLL_CANCELLED distinct from timeout. | T:C05Cancellation.test_c05_cancel_wakes_blocked_poll_with_structured_error |
| R05-02 | Readiness MUST win a tie with cancellation; a pre-cancelled token MUST refuse before waiting. | T:C05Cancellation.test_c05_precancelled_token_and_readiness_wins_tie |
| R05-03 | cancel() MUST be idempotent and latched. | T:C05Cancellation.test_c05_cancel_is_idempotent_and_token_type_checked |
| R05-04 | Cancellation races MUST NOT leak waiters or hang. | T:C05Cancellation.test_c05_cancel_race_stress_no_leak_no_hang<br>X:interleave |

Threats: **cross-principal cancellation** → token is a caller-held object, never addressable by id (T:C05Cancellation)

<a id="c06"></a>
## 06 — Admission / backpressure

- **Kind:** runtime; **modules:** admission.py; **artifacts:** —
- **Boundary / non-goals:** Owns in-process admission. Does not own fleet-wide quotas.
- **Ceilings:** max_concurrent<=100000, tenant_max<=max_concurrent, queue_depth<=100000.
- **Sources of truth:** `{"config": "PK_POLL_CONFIG/1 limits"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** shed (fail closed) on overload
- **Interface:** AdmissionController.acquire/release/slot/snapshot
- **Concurrency/idempotency:** Condition variable
- **Signals:** reason=admission, snapshot.shed/peak; **correlation:** refusal audited with correlation id; **runbook:** R4
- **Stable codes:** PK_POLL_OVERLOADED, PK_POLL_TENANT_QUOTA

| ID | Requirement | Evidence |
|---|---|---|
| R06-01 | Global and per-tenant concurrent-poll ceilings MUST shed deterministically with PK_POLL_OVERLOADED / PK_POLL_TENANT_QUOTA. | T:C06Admission.test_c06_global_and_tenant_ceilings_shed_deterministically |
| R06-02 | Queueing, when enabled, MUST be bounded FIFO with a bounded wait. | T:C06Admission.test_c06_bounded_fifo_queue_and_timeout |
| R06-03 | Slots MUST be released on every path. | T:C06Admission.test_c06_slot_releases_on_exception<br>X:soak |
| R06-04 | Admission MUST run before waiter allocation. | T:C12EmergencyDisable.test_c12_disable_refuses_new_polls_drains_inflight_then_rolls_back |

Threats: **tenant monopolises wait capacity** → per-tenant quota (T:C25Soak, T:C06Admission)

<a id="c07"></a>
## 07 — Authenticated identity / capability

- **Kind:** runtime; **modules:** identity.py; **artifacts:** —
- **Boundary / non-goals:** Owns token format and verification. Does not own key distribution or attestation.
- **Ceilings:** token <= 2048 bytes, ttl <= 3600 s, key >= 32 bytes.
- **Sources of truth:** `{"external_policy": "trusted issuer keys", "constant": "TOKEN_SCHEMA"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed (no trust root => refuse)
- **Interface:** Issuer.mint / Verifier.verify
- **Concurrency/idempotency:** stateless
- **Signals:** reason=identity; **correlation:** refusal audited; **runbook:** R3
- **Stable codes:** PK_POLL_TOKEN_*

| ID | Requirement | Evidence |
|---|---|---|
| R07-01 | A poll MUST present an HMAC-signed capability whose subject equals the PollSet owner principal tenant/component/instance. | T:C07Identity.test_c07_valid_token_binds_owner |
| R07-02 | Forged, untrusted, expired, cross-tenant and wrong-right tokens MUST be refused with distinct stable codes. | T:C07Identity.test_c07_cross_tenant_expired_forged_untrusted_refused<br>T:C07Identity.test_c07_right_and_key_rotation |
| R07-03 | Refusals MUST NOT disclose another principal. | T:C07Identity.test_c07_refusal_does_not_disclose_other_principal |
| R07-04 | Principal segments MUST be canonical lower-case ASCII (no Unicode look-alikes). | T:C07Identity.test_c07_malformed_tokens_and_principals |
| R07-05 | Identity MUST be bound to runtime attestation. | G:independent_review |

Threats: **owner-string spoofing** → signed subject (T:C07Identity)

Blocked by: No runtime attestation service; no replay-nonce store (tokens are short-lived bearer capabilities)

<a id="c08"></a>
## 08 — Tamper-evident audit sink

- **Kind:** runtime; **modules:** audit.py; **artifacts:** schemas/pk_poll_audit.schema.json
- **Boundary / non-goals:** Owns record format, chaining and local append. Does not own durable/WORM storage, retention or export.
- **Ceilings:** record <= 4096 bytes; closed event vocabulary.
- **Sources of truth:** `{"external_policy": "audit key", "runtime": "sink path"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** AuditSink.append / verify_chain
- **Concurrency/idempotency:** lock around append
- **Signals:** audit_head in diagnostics; **correlation:** correlation_id per record; **runbook:** R3
- **Stable codes:** PK_AUDIT_*

| ID | Requirement | Evidence |
|---|---|---|
| R08-01 | Records MUST be hash-chained and HMAC'd; verify MUST detect edit, delete, reorder and (with external head) truncation. | T:C08Audit.test_c08_chain_verifies_and_detects_edit_delete_reorder_truncate |
| R08-02 | An unwritable sink MUST fail the operation closed with PK_AUDIT_UNAVAILABLE. | T:C08Audit.test_c08_unwritable_sink_fails_closed_and_secrets_redacted<br>X:faults |
| R08-03 | A corrupt existing log MUST be refused on open; a valid one MUST resume its sequence. | T:C08Audit.test_c08_reopen_resumes_and_corrupt_log_refused |
| R08-04 | Records MUST be redacted and schema-valid. | T:C08Audit.test_c08_unwritable_sink_fails_closed_and_secrets_redacted |

Threats: **log tampering** → chain + MAC + external head (T:C08Audit)

Blocked by: No approved durable/WORM sink, retention owner or key custody

<a id="c09"></a>
## 09 — Telemetry exporter

- **Kind:** runtime; **modules:** telemetry.py; **artifacts:** ops/dashboard.json
- **Boundary / non-goals:** Owns metric catalog and exposition bodies. Does not own push transport or collectors.
- **Ceilings:** <= 64 tenant series + 16 buckets; closed outcome/reason sets.
- **Sources of truth:** `{"constant": "OUTCOMES, REASONS, LATENCY_BUCKETS_MS", "config": "sample_rate"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** pull-based; cannot block poll
- **Interface:** Telemetry.record / prometheus_text / otlp_json
- **Concurrency/idempotency:** lock
- **Signals:** inv14_polls_total, inv14_poll_latency_ms; **correlation:** no ids as labels (TEL-2); **runbook:** R4
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R09-01 | Prometheus exposition MUST parse and carry only allow-listed labels. | T:C09Telemetry.test_c09_prometheus_exposition_parses_with_stable_labels |
| R09-02 | Tenant label cardinality MUST be bounded. | T:C09Telemetry.test_c09_tenant_cardinality_is_bounded |
| R09-03 | Sampling MUST apply to latency only; counters are never sampled. | T:C09Telemetry.test_c09_sampling_applies_to_latency_only |
| R09-04 | An OTLP/JSON body MUST be produced. | T:C09Telemetry.test_c09_otlp_json_shape |

Threats: **cardinality attack** → bucketing (T:C09Telemetry.test_c09_tenant_cardinality_is_bounded)

Blocked by: No collector endpoint for remote export

<a id="c10"></a>
## 10 — Structured logging

- **Kind:** runtime; **modules:** pollog.py; **artifacts:** schemas/pk_poll_log.schema.json
- **Boundary / non-goals:** Owns log schema and emission. Does not own transport/retention.
- **Ceilings:** line <= 4096 bytes.
- **Sources of truth:** `{"constant": "LEVELS, OPERATIONS"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail open (drop + count) -- logging never blocks polls; audit is the fail-closed record
- **Interface:** StructLogger.log
- **Concurrency/idempotency:** lock
- **Signals:** dropped counter; **correlation:** correlation_id, trace_id; **runbook:** R8
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R10-01 | Every record MUST match PK_POLL_LOG/1 with tenant, workload, component, operation, correlation and trace ids. | T:C10Logging.test_c10_records_match_schema_with_stable_ids_and_redaction |
| R10-02 | Records MUST be single-line JSON (injection safe) and include monotonic duration for polls. | T:C10LoggingService.test_c10_injection_safe_single_line_with_monotonic_duration |
| R10-03 | Emission MUST be concurrency-safe and backend failure MUST NOT change poll semantics. | T:C10LoggingService.test_c10_concurrent_emission_produces_whole_records<br>T:C10Logging.test_c10_unknown_level_and_operation_are_normalised_and_stream_failure_counted |

Threats: **log injection / secret leakage** → JSON encoding + redaction (T:C10LoggingService, T:C31Redaction)

<a id="c11"></a>
## 11 — Trace-context propagation

- **Kind:** runtime; **modules:** tracing.py; **artifacts:** —
- **Boundary / non-goals:** Owns context parsing/propagation. Does not own span export.
- **Ceilings:** tracestate <= 512 chars / 32 members.
- **Sources of truth:** `{"constant": "W3C version 00"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail open (new root)
- **Interface:** child_context()
- **Concurrency/idempotency:** stateless
- **Signals:** inbound_valid flag; **correlation:** trace_id in logs; **runbook:** R8
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R11-01 | A valid W3C traceparent MUST be propagated as the parent of a new child span. | T:C11Tracing.test_c11_valid_parent_propagates_trace_id |
| R11-02 | Invalid context MUST start a new root without failing the poll. | T:C11Tracing.test_c11_invalid_parent_starts_new_root_and_is_flagged |
| R11-03 | The service MUST return the child traceparent. | T:C11Tracing.test_c11_service_returns_child_traceparent |

Threats: **baggage as data channel** → bounded tracestate (T:C11Tracing)

Blocked by: No span exporter/tracing backend

<a id="c12"></a>
## 12 — Emergency disable / policy hook

- **Kind:** runtime; **modules:** lifecycle.py, service.py; **artifacts:** docs/RUNBOOK.md
- **Boundary / non-goals:** Owns process-local switch. Does not own fleet propagation.
- **Ceilings:** drain <= 60 s.
- **Sources of truth:** `{"runtime": "lifecycle state", "external": "operator"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** Lifecycle.emergency_disable / transition
- **Concurrency/idempotency:** Condition variable; admission atomic with state
- **Signals:** reason=policy; **correlation:** transition audited; **runbook:** R2
- **Stable codes:** PK_POLL_DRAINING, PK_POLL_DISABLED

| ID | Requirement | Evidence |
|---|---|---|
| R12-01 | Disable MUST refuse new polls at once, let in-flight polls finish, then reach DISABLED. | T:C12EmergencyDisable.test_c12_disable_refuses_new_polls_drains_inflight_then_rolls_back |
| R12-02 | A drain that does not complete in time MUST stay DRAINING, never force DISABLED. | T:C12EmergencyDisable.test_c12_drain_timeout_leaves_draining_not_disabled |
| R12-03 | Rollback DISABLED -> DEPRECATED MUST be available and attributed. | T:C12EmergencyDisable<br>T:C33Runbook |
| R12-04 | Policy changes MUST be authenticated separately from poll callers. | G:independent_review |

Threats: **abuse continues during incident** → DRAINING refuses immediately (T:C12EmergencyDisable)

Blocked by: Actor is recorded but not authenticated (no admin identity provider); No fleet policy distribution

<a id="c13"></a>
## 13 — Per-component migration registry

- **Kind:** runtime; **modules:** governance.py; **artifacts:** governance/MIGRATION_REGISTRY.json
- **Boundary / non-goals:** Owns schema + enforcement. Does not own the inventory data.
- **Ceilings:** component_id <= 128 chars.
- **Sources of truth:** `{"external_policy": "governance/*.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** ConsumerGate.check/register
- **Concurrency/idempotency:** read-mostly
- **Signals:** reason=policy; **correlation:** consumer id; **runbook:** R7
- **Stable codes:** PK_POLL_UNREGISTERED_CONSUMER, PK_POLL_MIGRATION_*

| ID | Requirement | Evidence |
|---|---|---|
| R13-01 | Unregistered consumers MUST be refused. | T:C13MigrationRegistry.test_c13_unregistered_consumer_refused_registered_admitted |
| R13-02 | Overdue consumers MUST need a live waiver; MIGRATED consumers MUST NOT regress. | T:C13MigrationRegistry.test_c13_overdue_needs_live_waiver_and_migrated_regression_refused |
| R13-03 | Registry entries MUST validate (ids, stages, dates). | T:C13MigrationRegistry.test_c13_registry_validation |
| R13-04 | The registry MUST contain the real deployed consumer inventory. | G:governance |

Threats: **shadow consumers** → ConsumerGate (T:C13MigrationRegistry)

Blocked by: No consumer inventory supplied (inventory_status NOT_STARTED)

<a id="c14"></a>
## 14 — Lifecycle/state model

- **Kind:** runtime; **modules:** lifecycle.py; **artifacts:** schemas/pk_poll_lifecycle.json
- **Boundary / non-goals:** Process-local state machine.
- **Ceilings:** history <= 128.
- **Sources of truth:** `{"constant": "TRANSITIONS", "artifact": "schemas/pk_poll_lifecycle.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** Lifecycle
- **Concurrency/idempotency:** Condition variable
- **Signals:** diagnostics.lifecycle; **correlation:** transition records; **runbook:** R2
- **Stable codes:** PK_POLL_ILLEGAL_TRANSITION

| ID | Requirement | Evidence |
|---|---|---|
| R14-01 | Every illegal transition MUST be refused leaving state unchanged; every legal one MUST apply. | T:C14Lifecycle.test_c14_every_illegal_transition_refused_and_state_unchanged |
| R14-02 | Admission per state MUST match the machine-readable model. | T:C14Lifecycle.test_c14_admission_by_state_and_artifact_matches_code |
| R14-03 | Transitions MUST be attributed; repeats idempotent. | T:C14Lifecycle.test_c14_unattributed_and_idempotent_transitions |

Threats: **coerced state** → explicit table (T:C14Lifecycle)

Blocked by: No RETIRED state yet (EOL removal withdraws the package instead); replica reconciliation not applicable in-process

<a id="c15"></a>
## 15 — Restart/replay semantics

- **Kind:** runtime; **modules:** checkpoint.py; **artifacts:** —
- **Boundary / non-goals:** Owns process-local checkpoint. Readiness reconstruction is the host's job (RST-1).
- **Ceilings:** checkpoint <= 16 KiB.
- **Sources of truth:** `{"runtime": "checkpoint path"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed to safe defaults
- **Interface:** checkpoint.save/load/restore_or_default
- **Concurrency/idempotency:** atomic os.replace
- **Signals:** checkpoint_error; **correlation:** process_epoch in diagnostics/logs; **runbook:** R10
- **Stable codes:** PK_CHECKPOINT_*

| ID | Requirement | Evidence |
|---|---|---|
| R15-01 | Readiness MUST NOT be persisted; counters/lifecycle/config version MUST be checkpointed atomically with a digest. | T:C15Restart.test_c15_checkpoint_roundtrip_never_persists_readiness<br>T:C15Restart.test_c15_atomic_save_leaves_no_temp_files |
| R15-02 | Corrupt/tampered/oversized checkpoints MUST be refused. | T:C15Restart.test_c15_corrupt_truncated_tampered_checkpoints_refused |
| R15-03 | A killed process MUST restart from its checkpoint and re-observe live resources. | X:faults |

Threats: **false wake from stale readiness** → readiness_persisted=false (T:C15Restart)

<a id="c16"></a>
## 16 — Clock/tick authority

- **Kind:** runtime; **modules:** clock.py, polling.py; **artifacts:** schemas/pk_clock_config.schema.json
- **Boundary / non-goals:** Owns tick semantics.
- **Ceilings:** 1 us <= tick <= 1 s.
- **Sources of truth:** `{"config": "PK_CLOCK_CONFIG/1"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed on bad config
- **Interface:** validate_clock_config, ticks_to_ns
- **Concurrency/idempotency:** stateless
- **Signals:** diagnostics.tick_seconds; **correlation:** tick in diagnostics; **runbook:** R8
- **Stable codes:** PK_CLOCK_*

| ID | Requirement | Evidence |
|---|---|---|
| R16-01 | One tick MUST be an integer nanosecond count of the monotonic clock with tick*max <= 60 s. | T:C16Clock.test_c16_config_validation_bounds |
| R16-02 | PollSet MUST follow the configured tick and max. | T:C16Clock.test_c16_pollset_follows_clock_authority |
| R16-03 | A clock anomaly MUST NOT extend a wait past the real monotonic bound. | T:C16Clock.test_c16_backward_clock_cannot_extend_wait<br>X:faults |
| R16-04 | Tick->WASI duration MUST be exact integer arithmetic. | T:C02WasiAdapter.test_c02_tick_to_wasi_duration_is_exact_integer |

Threats: **clock manipulation extends blocking** → independent monotonic hard deadline (T:C16Clock)

<a id="c17"></a>
## 17 — Owner/escalation metadata

- **Kind:** governance; **modules:** governance.py; **artifacts:** governance/OWNERS.json, CODEOWNERS
- **Boundary / non-goals:** Metadata only.
- **Ceilings:** n/a
- **Sources of truth:** `{"external_policy": "governance/OWNERS.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** blocks certification
- **Interface:** governance/OWNERS.json
- **Concurrency/idempotency:** static
- **Signals:** verify_release governance gate; **correlation:** n/a; **runbook:** R0
- **Stable codes:** PK_GOVERNANCE_INVALID

| ID | Requirement | Evidence |
|---|---|---|
| R17-01 | An owners file MUST exist and validate. | T:C17Owners |
| R17-02 | UNASSIGNED ownership MUST block certification. | T:C17Owners<br>G:governance |

Threats: **orphaned component** → production_blockers (T:C17Owners)

Blocked by: The build cannot name owners, on-call routes or escalation

<a id="c18"></a>
## 18 — Architecture Decision Record

- **Kind:** governance; **modules:** —; **artifacts:** docs/adr/ADR-0001-retain-legacy-poll-model.md
- **Boundary / non-goals:** Documentation.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** docs/adr/
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R0
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R18-01 | ADR MUST state status, context, decision, limits, migration target, retirement criteria, consequences. | T:C18Adr |
| R18-02 | ADR MUST be approved by named deciders. | G:governance |

Blocked by: ADR is PROPOSED; no deciders exist to approve it

<a id="c19"></a>
## 19 — Compatibility matrix

- **Kind:** governance; **modules:** —; **artifacts:** docs/COMPATIBILITY_MATRIX.json
- **Boundary / non-goals:** Documentation + CI matrix.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** untested = unsupported
- **Interface:** docs/COMPATIBILITY_MATRIX.json
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R1
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R19-01 | The matrix MUST be machine-readable, never equate untested with supported, and tie TESTED_PASS to evidence. | T:C19CompatMatrix |
| R19-02 | Supported cells MUST be run in CI. | A:ci/release.yml |

Blocked by: Only one cell (CPython 3.11 / linux / x86_64, simulated WASI) could be executed here

<a id="c20"></a>
## 20 — Adjacent-layer integration tests

- **Kind:** verification; **modules:** —; **artifacts:** tests/test_integration_adjacent.py
- **Boundary / non-goals:** Tests only.
- **Ceilings:** n/a
- **Sources of truth:** `{"env": "PK_ADJACENT_PATH, INV14_RELEASE"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail in release
- **Interface:** unittest
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R1
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R20-01 | Integration tests MUST run against real INV-13/INV-15/GAP-15. | T:C20Adjacent |
| R20-02 | Absent layers MUST fail in release mode and be visible skips otherwise. | T:C27ReleasePipeline.test_c27_release_mode_turns_absent_layers_into_failures |

Blocked by: INV-13, INV-15 and GAP-15 packages were not supplied

<a id="c21"></a>
## 21 — WIT/protocol contract tests

- **Kind:** verification; **modules:** tools/gen_fixtures.py; **artifacts:** tests/fixtures/golden, tests/fixtures/negative
- **Boundary / non-goals:** Tests only.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail on drift
- **Interface:** fixtures
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R1
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R21-01 | Golden fixtures MUST validate and match current behaviour. | T:C21ContractFixtures.test_c21_golden_fixtures_validate<br>T:C21ContractFixtures.test_c21_golden_matches_current_behaviour |
| R21-02 | Negative fixtures MUST be rejected. | T:C21ContractFixtures.test_c21_negative_fixtures_are_rejected |

Blocked by: No WIT bindings in a second language to round-trip

<a id="c22"></a>
## 22 — Fuzz harness

- **Kind:** verification; **modules:** tools/fuzz.py; **artifacts:** —
- **Boundary / non-goals:** Tests only.
- **Ceilings:** 2 s per input.
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** tools/fuzz.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** seed; **runbook:** R8
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R22-01 | Seeded fuzzing of poll, token, config and trace targets MUST produce zero findings. | T:C22Fuzz.test_c22_seeded_fuzz_has_no_findings<br>G:fuzz |
| R22-02 | Every fuzz finding MUST become a regression test. | T:C22Fuzz.test_c22_regression_D02_non_json_config_is_structured<br>T:C22Fuzz.test_c22_regression_D03_unknown_provenance_key_refused |

Blocked by: No coverage-guided engine (atheris) or coverage report

<a id="c23"></a>
## 23 — Concurrency model checking

- **Kind:** verification; **modules:** tools/interleave.py; **artifacts:** —
- **Boundary / non-goals:** Tests only; the model is of the protocol, not the bytecode.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** tools/interleave.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R8
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R23-01 | Exhaustive interleavings of the wake protocol MUST have zero lost wakeups, and the known mutant MUST be caught. | T:C23Concurrency.test_c23_exhaustive_model_check_and_mutant_detected<br>G:interleave_model_check |
| R23-02 | Thread stress with clear-vs-signal over multiple poll sets MUST not leak or hang. | T:C23Concurrency.test_c23_thread_stress_clear_vs_signal_multi_set |

Blocked by: No TSAN-equivalent: no native bindings exist yet

<a id="c24"></a>
## 24 — Benchmarks + thresholds

- **Kind:** verification; **modules:** tools/bench.py; **artifacts:** ops/perf_thresholds.json
- **Boundary / non-goals:** Tests only.
- **Ceilings:** n/a
- **Sources of truth:** `{"external_policy": "ops/perf_thresholds.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** tools/bench.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R8
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R24-01 | p50/p95/p99/max latency, wake latency, overshoot, throughput, fan-out and allocation MUST be measured on the executing host. | T:C24Bench<br>G:bench_thresholds |
| R24-02 | Thresholds MUST be approved per cell. | G:governance |

Blocked by: Thresholds are PROPOSED; power/thermal not measurable

<a id="c25"></a>
## 25 — Soak/burst harness

- **Kind:** verification; **modules:** tools/soak.py; **artifacts:** —
- **Boundary / non-goals:** Tests only; single process.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** tools/soak.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R4
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R25-01 | Burst beyond admission limits MUST shed with registered codes and recover with >= 99% success and zero leaked slots/waiters. | T:C25Soak<br>G:soak_burst |

Blocked by: Long-duration and fleet-scale runs not performed here

<a id="c26"></a>
## 26 — Fault-injection harness

- **Kind:** verification; **modules:** tools/faults.py; **artifacts:** —
- **Boundary / non-goals:** Tests only. Network partition not applicable (no network I/O).
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** tools/faults.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R10
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R26-01 | Clock jumps, audit loss, stall, dependency loss, SIGKILL, torn checkpoint and control-plane degradation MUST each reach their defined outcome. | T:C26Faults<br>T:C27ReleasePipeline.test_c27_missing_pk_core_blocks_release_exit_2<br>G:fault_injection |

<a id="c27"></a>
## 27 — CI release pipeline

- **Kind:** verification; **modules:** verify_release.py, tools/manifest.py; **artifacts:** ci/release.yml
- **Boundary / non-goals:** Pipeline definition.
- **Ceilings:** n/a
- **Sources of truth:** `{"env": "INV14_RELEASE"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** verify_release.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** report JSON; **runbook:** R0
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R27-01 | The release verifier MUST run every local gate and exit 1 on failure, 2 on any unmet external gate, 0 only when all pass. | T:C27ReleasePipeline<br>G:manifest |
| R27-02 | The CI workflow MUST run the verifier in release mode across a version/OS matrix. | T:C27ReleasePipeline.test_c27_ci_workflow_runs_gate_in_release_mode_across_matrix |

Threats: **assumed-pass path** → no pass without all gates (T:C27ReleasePipeline)

Blocked by: The workflow has not executed on a CI service; branch protection is a repository setting

<a id="c28"></a>
## 28 — SBOM / provenance

- **Kind:** supply-chain; **modules:** tools/sbom.py; **artifacts:** sbom/inv14.cdx.json, sbom/provenance.intoto.json, sbom/dependency_scan.json
- **Boundary / non-goals:** Supply-chain metadata.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** INDETERMINATE is not a pass
- **Interface:** sbom/*
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** digest; **runbook:** R0
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R28-01 | A CycloneDX SBOM with per-file hashes and an import scan proving stdlib-only runtime MUST be generated. | T:C28Sbom<br>G:sbom_stdlib_only |
| R28-02 | Provenance MUST be signed by a trusted builder. | G:trusted_signature |

Threats: **undeclared dependency** → AST import scan (T:C28Sbom)

Blocked by: pk_core cannot be scanned until pinned; provenance unsigned

<a id="c29"></a>
## 29 — Artifact signing + verification

- **Kind:** supply-chain; **modules:** tools/sign.py; **artifacts:** governance/TRUSTED_KEYS.json, MANIFEST.sha256.sig.json
- **Boundary / non-goals:** Signing tooling; key custody is external.
- **Ceilings:** n/a
- **Sources of truth:** `{"external_policy": "governance/TRUSTED_KEYS.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** tools/sign.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** key_id; **runbook:** R0
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R29-01 | verify MUST fail closed on missing signature, unknown/revoked/untrusted signer, manifest change or bad signature. | T:C29Signing.test_c29_sign_verify_tamper_and_trust_policy |
| R29-02 | Two independent backends MUST agree. | T:C29Signing.test_c29_openssl_backend_agrees_when_present |
| R29-03 | Releases MUST be signed by a TRUSTED key. | G:trusted_signature |

Threats: **tampered release** → Ed25519 over manifest (T:C29Signing)

Blocked by: Only an UNTRUSTED_DEV key exists; no HSM/KMS, trust root or transparency log

<a id="c30"></a>
## 30 — Configuration schema + provenance

- **Kind:** runtime; **modules:** config.py; **artifacts:** schemas/pk_poll_config.schema.json
- **Boundary / non-goals:** Owns validation and activation.
- **Ceilings:** doc <= 64 KiB, history <= 64.
- **Sources of truth:** `{"config": "PK_POLL_CONFIG/1"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed (active config kept)
- **Interface:** ConfigStore.update
- **Concurrency/idempotency:** lock
- **Signals:** history; **correlation:** config version + digest; **runbook:** R4
- **Stable codes:** PK_CONFIG_*

| ID | Requirement | Evidence |
|---|---|---|
| R30-01 | Config MUST carry provenance and exactly the governed limit keys within bounds; unknown keys refused. | T:C30Config.test_c30_missing_provenance_and_unknown_keys_refused |
| R30-02 | Overlays MUST merge base->environment->site; updates MUST be atomic, keep history and refuse version reuse. | T:C30Config.test_c30_overlays_atomic_update_history |
| R30-03 | Code validation and the JSON schema MUST agree. | T:C22Fuzz.test_c22_regression_D03_unknown_provenance_key_refused<br>X:fuzz |

Threats: **unsafe live change** → validate-then-swap (T:C30Config)

Blocked by: Update authorization not authenticated (no admin identity)

<a id="c31"></a>
## 31 — Secret handling / redaction

- **Kind:** runtime; **modules:** redaction.py; **artifacts:** —
- **Boundary / non-goals:** Owns redaction function.
- **Ceilings:** 256 chars, depth 4, 32 items.
- **Sources of truth:** `{"constant": "patterns"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** redact on doubt
- **Interface:** redact()
- **Concurrency/idempotency:** pure
- **Signals:** n/a; **correlation:** n/a; **runbook:** R3
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R31-01 | Secret-named keys and credential-shaped values MUST be redacted; output bounded in size/depth/items. | T:C31Redaction.test_c31_secret_keys_and_shapes_redacted<br>T:C31Redaction.test_c31_bounds_and_totality |
| R31-02 | Tokens and keys MUST never appear in logs, audit or diagnostics. | T:C31Redaction.test_c31_error_details_and_diagnostics_carry_no_secrets |

Threats: **credential leak** → key + value patterns (T:C31Redaction)

<a id="c32"></a>
## 32 — Dashboards + alerts

- **Kind:** operations; **modules:** —; **artifacts:** ops/dashboard.json, ops/alerts.yml
- **Boundary / non-goals:** Ops as code.
- **Ceilings:** n/a
- **Sources of truth:** `{}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** n/a
- **Interface:** ops/*
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** n/a; **runbook:** R3
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R32-01 | Alerts MUST reference exported metrics, closed reasons, runbook anchors, and distinguish failure classes. | T:C32DashboardAlerts |

Blocked by: Not loaded into a live Prometheus/Grafana; thresholds not SLO-approved; no data-freshness alert source

<a id="c33"></a>
## 33 — Incident runbook

- **Kind:** operations; **modules:** tools/runbook.py; **artifacts:** docs/RUNBOOK.md
- **Boundary / non-goals:** Ops procedure.
- **Ceilings:** n/a
- **Sources of truth:** `{"env": "INV14_AUDIT_KEY_HEX"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** refuse without audit key
- **Interface:** tools/runbook.py
- **Concurrency/idempotency:** n/a
- **Signals:** n/a; **correlation:** audit records; **runbook:** R0-R10
- **Stable codes:** none

| ID | Requirement | Evidence |
|---|---|---|
| R33-01 | status, disable, rollback, transition, verify-audit MUST execute and refuse illegal actions. | T:C33Runbook |

Blocked by: No game-day/tabletop with a real on-call team; paging targets UNASSIGNED

<a id="c34"></a>
## 34 — Waiver registry

- **Kind:** governance; **modules:** governance.py; **artifacts:** governance/WAIVERS.json
- **Boundary / non-goals:** Schema + enforcement; data is organisational.
- **Ceilings:** 180 days.
- **Sources of truth:** `{"external_policy": "governance/WAIVERS.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed
- **Interface:** validate_waivers, ConsumerGate
- **Concurrency/idempotency:** static
- **Signals:** basis in gate result; **correlation:** waiver_id; **runbook:** R7
- **Stable codes:** PK_GOVERNANCE_*

| ID | Requirement | Evidence |
|---|---|---|
| R34-01 | Waivers MUST name owner and a different approver, be <= 180 days, and admit only their consumer while live. | T:C34Waivers<br>T:C13MigrationRegistry.test_c13_overdue_needs_live_waiver_and_migrated_regression_refused |

Threats: **self-approved waiver** → approver != owner (T:C34Waivers)

<a id="c35"></a>
## 35 — Formal end-of-life policy

- **Kind:** governance; **modules:** governance.py; **artifacts:** governance/EOL_POLICY.json
- **Boundary / non-goals:** Policy + enforcement.
- **Ceilings:** n/a
- **Sources of truth:** `{"external_policy": "governance/EOL_POLICY.json"}`
- **Compatibility:** Additive to v4.2.0: PK_POLL/1 result fields, ready/timeout/ownership semantics and the 12 v4.2.0 tests are unchanged (G:test_polling.py:normal, G:test_polling.py:optimized).
- **Fail mode:** fail closed after REMOVED
- **Interface:** eol_phase, ConsumerGate
- **Concurrency/idempotency:** static
- **Signals:** eol_phase; **correlation:** n/a; **runbook:** R7
- **Stable codes:** PK_POLL_EOL_REMOVED, PK_POLL_REGISTRY_CLOSED

| ID | Requirement | Evidence |
|---|---|---|
| R35-01 | EOL phases MUST be enforced: registry closure, waiver-only, removal. | T:C35Eol.test_c35_eol_phases_enforced |
| R35-02 | Milestones MUST be strictly increasing and end in REMOVED. | T:C35Eol.test_c35_eol_validation |
| R35-03 | The policy MUST be APPROVED by a named authority. | G:governance |

Threats: **silent support extension** → waivers cannot pass REMOVED (T:C35Eol)

Blocked by: Dates are PROPOSED; no approving authority

