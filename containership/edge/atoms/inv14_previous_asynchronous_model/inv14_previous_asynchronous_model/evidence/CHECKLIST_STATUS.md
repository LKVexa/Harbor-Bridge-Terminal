# INV-14 v4.3.0 — checklist status

Controls: **1593** — BLOCKED 226, EVIDENCE_READY 1239, IN_PROGRESS 128. VERIFIED: 0 (no independent reviewer).
Release gate: **BLOCKED** (exit 2). Clean-room from archive: exit 2, local gates all pass: True.

| Component | EVIDENCE_READY | IN_PROGRESS | BLOCKED |
|---|---|---|---|
| 01 Pinned pk_core runtime/dependency package | 33 | 3 | 9 |
| 02 WASI 0.2 / wasi:io integration adapter | 33 | 4 | 8 |
| 03 Versioned WIT/JSON schema contracts | 40 | 0 | 5 |
| 04 INV-14 -> INV-15 migration bridge | 31 | 7 | 7 |
| 05 Cancellation contract | 38 | 2 | 5 |
| 06 Admission / backpressure | 37 | 4 | 4 |
| 07 Authenticated identity / capability | 35 | 5 | 5 |
| 08 Tamper-evident audit sink | 34 | 5 | 6 |
| 09 Telemetry exporter | 38 | 3 | 4 |
| 10 Structured logging | 39 | 2 | 4 |
| 11 Trace-context propagation | 36 | 2 | 7 |
| 12 Emergency disable / policy hook | 35 | 3 | 7 |
| 13 Per-component migration registry | 33 | 5 | 7 |
| 14 Lifecycle/state model | 37 | 4 | 4 |
| 15 Restart/replay semantics | 36 | 5 | 4 |
| 16 Clock/tick authority | 39 | 2 | 4 |
| 17 Owner/escalation metadata | 33 | 3 | 9 |
| 18 Architecture Decision Record | 36 | 4 | 5 |
| 19 Compatibility matrix | 33 | 5 | 7 |
| 20 Adjacent-layer integration tests | 31 | 1 | 13 |
| 21 WIT/protocol contract tests | 40 | 0 | 5 |
| 22 Fuzz harness | 35 | 5 | 5 |
| 23 Concurrency model checking | 37 | 3 | 5 |
| 24 Benchmarks + thresholds | 32 | 7 | 6 |
| 25 Soak/burst harness | 34 | 5 | 6 |
| 26 Fault-injection harness | 36 | 4 | 5 |
| 27 CI release pipeline | 34 | 4 | 7 |
| 28 SBOM / provenance | 34 | 5 | 6 |
| 29 Artifact signing + verification | 35 | 3 | 7 |
| 30 Configuration schema + provenance | 36 | 4 | 5 |
| 31 Secret handling / redaction | 35 | 4 | 6 |
| 32 Dashboards + alerts | 35 | 3 | 7 |
| 33 Incident runbook | 35 | 4 | 6 |
| 34 Waiver registry | 33 | 3 | 9 |
| 35 Formal end-of-life policy | 35 | 1 | 9 |

## Global and final gates

- **GLOBAL-1** BLOCKED — no owner/milestone assigned for any component (OWNERS UNASSIGNED)
- **GLOBAL-2** EVIDENCE_READY — schemas/*.json + WIT, generated and drift-checked
- **GLOBAL-3** EVIDENCE_READY — every refusal has a stable code, is audited, tenant-safe (C07/C08/C31), negative tests pass
- **GLOBAL-4** EVIDENCE_READY — ceilings per component spec; leak/cleanup tests pass
- **GLOBAL-5** BLOCKED — pk_core unpinned
- **GLOBAL-6** EVIDENCE_READY — verify_release exit 2 with blockers listed; clean-room exit 2
- **GLOBAL-7** EVIDENCE_READY — no item is marked N/A; proposed N/A boundaries are recorded as BLOCKED pending a reviewer
- **GLOBAL-8** IN_PROGRESS — every ID maps to source/test/artifact here; reviewer approval column empty
- **FINAL-01** BLOCKED — pk_core absent, WASI Python-only, INV-15 protocol-only
- **FINAL-02** IN_PROGRESS — authenticated ownership, cancellation, admission, lifecycle, restart/time implemented; attestation, admin auth, tested matrix missing
- **FINAL-03** IN_PROGRESS — harnesses implemented and passing; adjacent integration, trusted signing, approvals missing
- **FINAL-04** EVIDENCE_READY — 12/12 v4.2.0 tests pass normal and -O, supplemented by the v4.3.0 suites
- **FINAL-05** BLOCKED — pk_core not supplied
- **FINAL-06** BLOCKED — no real WASI runtime
- **FINAL-07** BLOCKED — manifest/hashes/lock/schemas verify clean-room; signature is UNTRUSTED_DEV
- **FINAL-08** BLOCKED — consumer inventory NOT_STARTED
- **FINAL-09** IN_PROGRESS — disable/rollback/restart/migration-rollback exercised in tests and fault harness; not exercised operationally
- **FINAL-10** BLOCKED — no approval records

## Every control

| ID | State | Note |
|---|---|---|
| 01.01 | IN_PROGRESS | declaration exists (name, interpreter range, policy); version/source/digest UNRESOLVED: real pk_core not supplied; lock UNRESOLVED |
| 01.02 | IN_PROGRESS | rejection of floating/mutable pins implemented; the pin itself awaits the core |
| 01.03 | BLOCKED | transitive lock cannot be produced: real pk_core not supplied; lock UNRESOLVED |
| 01.04 | EVIDENCE_READY | production path (vendored, tree-digest pinned) and offline path declared in the lock |
| 01.05 | EVIDENCE_READY | probe checks symbols/version/digest against a fixture core; real schema/behavioural capability checks need the real core |
| 01.06 | EVIDENCE_READY | stable PK_CORE_* codes; gate exits 2 (BLOCKED) with the code |
| 01.07 | BLOCKED | clean-room venv bootstrap of pk_core impossible: real pk_core not supplied; lock UNRESOLVED (INV-14 itself is clean-room tested from the zip) |
| 01.08 | BLOCKED | resolver-conflict test needs pk_core's dependency graph: real pk_core not supplied; lock UNRESOLVED |
| 01.09 | IN_PROGRESS | version/hash in diagnostics and release report; audit/certification-report inclusion pending a real pin |
| 01.10 | BLOCKED | 100-item assessment cannot run: real pk_core not supplied; lock UNRESOLVED |
| 01.11 | EVIDENCE_READY | upgrade/downgrade policy recorded in lock |
| 01.12 | BLOCKED | scan of pk_core INDETERMINATE until pinned |
| 01.13 | EVIDENCE_READY | 4 MUST requirements R01-xx, each with evidence refs |
| 01.14 | EVIDENCE_READY | boundary: Owns the declaration and verification of pk_core. Does not own pk_core itself, its build or its index. |
| 01.15 | EVIDENCE_READY | ceilings: Lock file read once; tree digest bounded by the core's file count. |
| 01.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 01.17 | EVIDENCE_READY | {"constant": "REQUIRED_SYMBOLS", "external_policy": "deps/pk_core.lock.json", "runtime": "installed pk_core tree"} |
| 01.18 | EVIDENCE_READY | threats: substituted or tampered core, silent skip when core absent |
| 01.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 01.20 | EVIDENCE_READY | fail closed on every dependency condition; no degraded mode |
| 01.21 | EVIDENCE_READY | codes: PK_CORE_* |
| 01.22 | EVIDENCE_READY | core_probe.probe() -> {ok, code, core} |
| 01.23 | EVIDENCE_READY | stateless |
| 01.24 | EVIDENCE_READY | leak/cleanup tests |
| 01.25 | EVIDENCE_READY | core version/hash in diagnostics |
| 01.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 01.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 01.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 01.29 | EVIDENCE_READY |  |
| 01.30 | EVIDENCE_READY |  |
| 01.31 | EVIDENCE_READY | diagnostics.pk_core |
| 01.32 | EVIDENCE_READY |  |
| 01.33 | EVIDENCE_READY | runbook R0 |
| 01.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 01.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 01.36 | EVIDENCE_READY |  |
| 01.37 | EVIDENCE_READY |  |
| 01.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 01.39 | BLOCKED | needs independent review + owner; component blockers: The exact compatible pk_core was not supplied; lock is UNRESOLVED |
| 01.40 | EVIDENCE_READY |  |
| 01.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 01.42 | EVIDENCE_READY |  |
| 01.43 | BLOCKED | no security review record: needs an independent reviewer |
| 01.44 | EVIDENCE_READY |  |
| 01.45 | BLOCKED | no trusted signature, no reviewer approval |
| 02.01 | EVIDENCE_READY | world inv14-legacy-host imports wasi:io/poll@0.2.0 and wasi:clocks/monotonic-clock@0.2.0 |
| 02.02 | IN_PROGRESS | authoritative WIT present; not validated by a WIT parser: no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 02.03 | BLOCKED | bindings generation needs wit-bindgen/jco: no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 02.04 | EVIDENCE_READY | translation layer over integer handles (no Python identity crosses the boundary); proven on the reference host |
| 02.05 | IN_PROGRESS | timer drop on all paths; member-handle double-drop/use-after-drop is the runtime's resource table: no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 02.06 | EVIDENCE_READY | adapter errors map to PK_POLL_ERROR/1; runtime traps unmapped until a runtime exists |
| 02.07 | EVIDENCE_READY | ticks*tick_ns -> subscribe-duration |
| 02.08 | IN_PROGRESS | zero/immediate/delayed/multiple/timeout/foreign/empty fixtures on reference host; invalid-resource and resource-drop fixtures need a real runtime |
| 02.09 | BLOCKED | no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 02.10 | IN_PROGRESS | return/timeout cleanup proven on reference host; trap/termination/shutdown need a runtime |
| 02.11 | BLOCKED | interop traces need a real runtime: no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 02.12 | BLOCKED | gate exists and is BLOCKED: no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 02.13 | EVIDENCE_READY | 5 MUST requirements R02-xx, each with evidence refs |
| 02.14 | EVIDENCE_READY | boundary: Owns the translation PK_POLL/1 <-> wasi:io/poll. Does not own the runtime, handles' underlying resources or component compilation. |
| 02.15 | EVIDENCE_READY | ceilings: Set <= max_pollables; timeout <= max_timeout_ticks and 60 s. |
| 02.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 02.17 | EVIDENCE_READY | {"constant": "WASI_IO/WASI_CLOCK ids", "config": "PK_CLOCK_CONFIG/1", "runtime": "host handles"} |
| 02.18 | EVIDENCE_READY | threats: foreign handle smuggled into poll |
| 02.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 02.20 | EVIDENCE_READY | fail closed on invalid input; real-runtime gate BLOCKED |
| 02.21 | EVIDENCE_READY | codes: PK_POLL_* |
| 02.22 | EVIDENCE_READY | WasiHost protocol (subscribe_duration, poll, drop, owner_of) |
| 02.23 | EVIDENCE_READY | host-provided; reference host uses one condition variable |
| 02.24 | EVIDENCE_READY | leak/cleanup tests |
| 02.25 | EVIDENCE_READY | result carries owner/set_size |
| 02.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 02.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 02.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 02.29 | EVIDENCE_READY |  |
| 02.30 | EVIDENCE_READY |  |
| 02.31 | EVIDENCE_READY | same PK_POLL/1 result |
| 02.32 | EVIDENCE_READY |  |
| 02.33 | EVIDENCE_READY | runbook R8 |
| 02.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 02.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 02.36 | EVIDENCE_READY |  |
| 02.37 | EVIDENCE_READY |  |
| 02.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 02.39 | BLOCKED | needs independent review + owner; component blockers: No WASI 0.2 runtime (wasmtime/jco) or compiled component fixture in this environment; No WIT parser/toolchain (wasm-tools) available to validate the WIT in CI |
| 02.40 | EVIDENCE_READY |  |
| 02.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 02.42 | EVIDENCE_READY |  |
| 02.43 | BLOCKED | no security review record: needs an independent reviewer |
| 02.44 | EVIDENCE_READY |  |
| 02.45 | BLOCKED | no trusted signature, no reviewer approval |
| 03.01 | EVIDENCE_READY |  |
| 03.02 | EVIDENCE_READY | widths/bounds/ordering/uniqueness/max sizes in policy + schema |
| 03.03 | EVIDENCE_READY |  |
| 03.04 | EVIDENCE_READY | string ids + WIT enum + retry class + caller action + details policy |
| 03.05 | EVIDENCE_READY | ordering/duplicates/removal semantics defined |
| 03.06 | EVIDENCE_READY |  |
| 03.07 | EVIDENCE_READY |  |
| 03.08 | EVIDENCE_READY | 8 golden + 27 negative fixtures incl. unknown-field and version cases |
| 03.09 | EVIDENCE_READY | error enum generated into registry, WIT and schema |
| 03.10 | EVIDENCE_READY | field-level golden comparison |
| 03.11 | EVIDENCE_READY | ids + digests in diagnostics; manifest hashes |
| 03.12 | BLOCKED | review gate defined; approval requires a named reviewer: needs an independent reviewer/approver record |
| 03.13 | EVIDENCE_READY | 4 MUST requirements R03-xx, each with evidence refs |
| 03.14 | EVIDENCE_READY | boundary: Owns the serialized contract. Does not own transport encodings beyond JSON and the component model. |
| 03.15 | EVIDENCE_READY | ceilings: set_size <= 65536, strings <= 256, message <= 1024 (schema maxima). |
| 03.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 03.17 | EVIDENCE_READY | {"constant": "schema files", "generated": "error_codes.json, WIT enum, error schema enum"} |
| 03.18 | EVIDENCE_READY | threats: contract drift between code and schema |
| 03.19 | EVIDENCE_READY | no runtime operation |
| 03.20 | EVIDENCE_READY | gate fails on drift |
| 03.21 | EVIDENCE_READY | codes: (defines all) |
| 03.22 | EVIDENCE_READY | schemas/*.json, wit/*.wit |
| 03.23 | EVIDENCE_READY | static artifacts |
| 03.24 | EVIDENCE_READY | leak/cleanup tests |
| 03.25 | EVIDENCE_READY | schema ids in every payload |
| 03.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 03.27 | EVIDENCE_READY | regressions for D-05 |
| 03.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 03.29 | EVIDENCE_READY |  |
| 03.30 | EVIDENCE_READY |  |
| 03.31 | EVIDENCE_READY | n/a (static) |
| 03.32 | EVIDENCE_READY |  |
| 03.33 | EVIDENCE_READY | runbook R1 |
| 03.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 03.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 03.36 | EVIDENCE_READY |  |
| 03.37 | EVIDENCE_READY |  |
| 03.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 03.39 | BLOCKED | needs independent review + owner |
| 03.40 | EVIDENCE_READY |  |
| 03.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 03.42 | EVIDENCE_READY |  |
| 03.43 | BLOCKED | no security review record: needs an independent reviewer |
| 03.44 | EVIDENCE_READY |  |
| 03.45 | BLOCKED | no trusted signature, no reviewer approval |
| 04.01 | IN_PROGRESS | readiness/timeout/cancel mapping documented in module; field-by-field mapping to real INV-15 awaits its ABI |
| 04.02 | EVIDENCE_READY | versioned forward/reverse shims (protocol-level) |
| 04.03 | IN_PROGRESS | type mismatches refused with PK_MIGRATION_*; full unsupported-difference list needs INV-15 |
| 04.04 | EVIDENCE_READY | dual-path parity harness |
| 04.05 | IN_PROGRESS | LEGACY/DUAL_STACK/CANARY/MIGRATED/ROLLED_BACK; inventory/eligible/exception/blocked stages live in the registry, not the machine |
| 04.06 | EVIDENCE_READY | per-consumer machine + registry gate |
| 04.07 | IN_PROGRESS | correlation/trace carried by the service; not yet threaded through the shims |
| 04.08 | EVIDENCE_READY | rollback legal from DUAL_STACK/CANARY; no readiness state is owned by the bridge |
| 04.09 | IN_PROGRESS | immediate/delayed/timeout parity; cancellation/ownership/restart/overload parity pending INV-15 |
| 04.10 | BLOCKED | bridge overhead budget needs real INV-15 to compare: real INV-15 not supplied; proven against protocol only |
| 04.11 | IN_PROGRESS | stage history exists; no exported migration metric series yet |
| 04.12 | EVIDENCE_READY | MIGRATED regression refused; bridge removed with EOL REMOVED |
| 04.13 | EVIDENCE_READY | 5 MUST requirements R04-xx, each with evidence refs |
| 04.14 | EVIDENCE_READY | boundary: Owns shims and per-consumer stage machine. Does not own INV-15 or consumer code. |
| 04.15 | EVIDENCE_READY | ceilings: One PollSet per forward shim; stage history bounded by transitions. |
| 04.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 04.17 | EVIDENCE_READY | {"runtime": "per-consumer MigrationStateMachine", "external_policy": "governance/MIGRATION_REGISTRY.json"} |
| 04.18 | EVIDENCE_READY | threats: cutover without parity |
| 04.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 04.20 | EVIDENCE_READY | refuse advancement on missing/failed parity |
| 04.21 | EVIDENCE_READY | codes: PK_MIGRATION_* |
| 04.22 | EVIDENCE_READY | PollableFuture, FuturePollable, MigrationStateMachine, parity_check |
| 04.23 | EVIDENCE_READY | state machine guarded by a lock |
| 04.24 | EVIDENCE_READY | leak/cleanup tests |
| 04.25 | EVIDENCE_READY | consumer id + stage history |
| 04.26 | BLOCKED | required tests not passing/skipped: T:C20Adjacent.test_c20_inv15_future_satisfies_bridge_protocol |
| 04.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 04.28 | BLOCKED | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 04.29 | EVIDENCE_READY |  |
| 04.30 | EVIDENCE_READY |  |
| 04.31 | EVIDENCE_READY | migration stage per consumer |
| 04.32 | EVIDENCE_READY |  |
| 04.33 | EVIDENCE_READY | runbook R7 |
| 04.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 04.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 04.36 | EVIDENCE_READY |  |
| 04.37 | EVIDENCE_READY |  |
| 04.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 04.39 | BLOCKED | needs independent review + owner; component blockers: INV-15 real ABI not supplied; shims proven against the protocol only |
| 04.40 | EVIDENCE_READY |  |
| 04.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 04.42 | IN_PROGRESS |  |
| 04.43 | BLOCKED | no security review record: needs an independent reviewer |
| 04.44 | EVIDENCE_READY |  |
| 04.45 | BLOCKED | no trusted signature, no reviewer approval |
| 05.01 | EVIDENCE_READY | states active -> cancelled (latched, terminal) |
| 05.02 | EVIDENCE_READY | ready > cancel > timeout; disable refuses before wait |
| 05.03 | EVIDENCE_READY | PK_POLL_CANCELLED retry_class=caller |
| 05.04 | EVIDENCE_READY |  |
| 05.05 | EVIDENCE_READY |  |
| 05.06 | EVIDENCE_READY | ready result wins and does not consume readiness (level-triggered); cancel after completion is a no-op |
| 05.07 | BLOCKED | WASI/INV-15 cancellation propagation: no WASI 0.2 runtime / compiled component / WIT toolchain available; real INV-15 not supplied; proven against protocol only |
| 05.08 | IN_PROGRESS | polls_cancelled counter + outcome=cancelled; late-cancel and cancellation-latency series not yet |
| 05.09 | EVIDENCE_READY | pre-cancel, during-wait, after-ready, races |
| 05.10 | EVIDENCE_READY |  |
| 05.11 | EVIDENCE_READY | tokens are unaddressable caller-held objects; no API cancels by id |
| 05.12 | IN_PROGRESS | in error schema/WIT enum; bridge + runbook coverage partial |
| 05.13 | EVIDENCE_READY | 4 MUST requirements R05-xx, each with evidence refs |
| 05.14 | EVIDENCE_READY | boundary: Owns caller-driven cancellation of one poll. Does not own INV-15 cancellation semantics. |
| 05.15 | EVIDENCE_READY | ceilings: Reason truncated to 64 chars; one waiter per poll per token. |
| 05.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 05.17 | EVIDENCE_READY | {"constant": "precedence ready > cancel > timeout"} |
| 05.18 | EVIDENCE_READY | threats: cross-principal cancellation |
| 05.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 05.20 | EVIDENCE_READY | n/a |
| 05.21 | EVIDENCE_READY | codes: PK_POLL_CANCELLED, PK_POLL_INVALID_CANCEL_TOKEN |
| 05.22 | EVIDENCE_READY | PollSet.poll(..., cancel=CancelToken) |
| 05.23 | EVIDENCE_READY | lock + durable Event registration |
| 05.24 | EVIDENCE_READY | leak/cleanup tests |
| 05.25 | EVIDENCE_READY | correlation_id added to error details by the service |
| 05.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 05.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 05.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 05.29 | EVIDENCE_READY |  |
| 05.30 | EVIDENCE_READY |  |
| 05.31 | EVIDENCE_READY | polls_cancelled, outcome=cancelled |
| 05.32 | EVIDENCE_READY |  |
| 05.33 | EVIDENCE_READY | runbook R8 |
| 05.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 05.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 05.36 | EVIDENCE_READY |  |
| 05.37 | EVIDENCE_READY |  |
| 05.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 05.39 | BLOCKED | needs independent review + owner |
| 05.40 | EVIDENCE_READY |  |
| 05.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 05.42 | EVIDENCE_READY |  |
| 05.43 | BLOCKED | no security review record: needs an independent reviewer |
| 05.44 | EVIDENCE_READY |  |
| 05.45 | BLOCKED | no trusted signature, no reviewer approval |
| 06.01 | IN_PROGRESS | global + per-tenant + per-process poll-set registry cap; per-component ceiling not separate |
| 06.02 | EVIDENCE_READY | queue_depth=0 default; bounded FIFO when enabled |
| 06.03 | EVIDENCE_READY | strict per-tenant quota (ADM-5) |
| 06.04 | EVIDENCE_READY | quota vs transient distinguished |
| 06.05 | EVIDENCE_READY | jittered exponential backoff guidance on PK_POLL_OVERLOADED |
| 06.06 | EVIDENCE_READY | admission precedes PollSet/waiter allocation |
| 06.07 | IN_PROGRESS | DRAINING sheds all new legacy polls; no privileged class exists in INV-14 to starve others |
| 06.08 | IN_PROGRESS | active/queued/peak/shed in snapshot; queue age and fairness deviation not exported |
| 06.09 | EVIDENCE_READY | burst beyond limits, deterministic shed, recovery |
| 06.10 | IN_PROGRESS | 300-tenant mixed load; no dedicated adversarial-vs-latency-sensitive assertion |
| 06.11 | EVIDENCE_READY | limits in PK_POLL_CONFIG/1 with provenance + atomic update |
| 06.12 | EVIDENCE_READY | defaults 1024 global / 64 tenant / no queue; v4.2.0 small workloads unaffected (12 tests pass) |
| 06.13 | EVIDENCE_READY | 4 MUST requirements R06-xx, each with evidence refs |
| 06.14 | EVIDENCE_READY | boundary: Owns in-process admission. Does not own fleet-wide quotas. |
| 06.15 | EVIDENCE_READY | ceilings: max_concurrent<=100000, tenant_max<=max_concurrent, queue_depth<=100000. |
| 06.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 06.17 | EVIDENCE_READY | {"config": "PK_POLL_CONFIG/1 limits"} |
| 06.18 | EVIDENCE_READY | threats: tenant monopolises wait capacity |
| 06.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 06.20 | EVIDENCE_READY | shed (fail closed) on overload |
| 06.21 | EVIDENCE_READY | codes: PK_POLL_OVERLOADED, PK_POLL_TENANT_QUOTA |
| 06.22 | EVIDENCE_READY | AdmissionController.acquire/release/slot/snapshot |
| 06.23 | EVIDENCE_READY | Condition variable |
| 06.24 | EVIDENCE_READY | leak/cleanup tests |
| 06.25 | EVIDENCE_READY | refusal audited with correlation id |
| 06.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 06.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 06.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 06.29 | EVIDENCE_READY |  |
| 06.30 | EVIDENCE_READY |  |
| 06.31 | EVIDENCE_READY | reason=admission, snapshot.shed/peak |
| 06.32 | EVIDENCE_READY |  |
| 06.33 | EVIDENCE_READY | runbook R4 |
| 06.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 06.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 06.36 | EVIDENCE_READY |  |
| 06.37 | EVIDENCE_READY |  |
| 06.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 06.39 | BLOCKED | needs independent review + owner |
| 06.40 | EVIDENCE_READY |  |
| 06.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 06.42 | EVIDENCE_READY |  |
| 06.43 | BLOCKED | no security review record: needs an independent reviewer |
| 06.44 | EVIDENCE_READY |  |
| 06.45 | BLOCKED | no trusted signature, no reviewer approval |
| 07.01 | EVIDENCE_READY | HMAC capability token from a trusted issuer key |
| 07.02 | IN_PROGRESS | tenant/component/instance subject, issuer kid, rights, expiry signed; audience claim not implemented |
| 07.03 | EVIDENCE_READY | lower-case ASCII segments |
| 07.04 | IN_PROGRESS | issuer/kid/signature/exp/nbf/right checked before ownership; no audience |
| 07.05 | BLOCKED | no nonce/session store; short TTL bearer tokens only -- replay window = TTL |
| 07.06 | IN_PROGRESS | multi-key rotation; no revocation list |
| 07.07 | EVIDENCE_READY | verify() before any PollSet touch |
| 07.08 | EVIDENCE_READY |  |
| 07.09 | EVIDENCE_READY | poll.refused.identity / foreign_owner audited |
| 07.10 | IN_PROGRESS | tamper, cross-tenant, stale kid, Unicode segments; no audience/revocation cases |
| 07.11 | EVIDENCE_READY | no trust root => PK_POLL_NO_TRUST_ROOT (fail closed) |
| 07.12 | IN_PROGRESS | codes in contracts, runbook R3; WIT carries no token field yet |
| 07.13 | EVIDENCE_READY | 5 MUST requirements R07-xx, each with evidence refs |
| 07.14 | EVIDENCE_READY | boundary: Owns token format and verification. Does not own key distribution or attestation. |
| 07.15 | EVIDENCE_READY | ceilings: token <= 2048 bytes, ttl <= 3600 s, key >= 32 bytes. |
| 07.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 07.17 | EVIDENCE_READY | {"external_policy": "trusted issuer keys", "constant": "TOKEN_SCHEMA"} |
| 07.18 | EVIDENCE_READY | threats: owner-string spoofing |
| 07.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 07.20 | EVIDENCE_READY | fail closed (no trust root => refuse) |
| 07.21 | EVIDENCE_READY | codes: PK_POLL_TOKEN_* |
| 07.22 | EVIDENCE_READY | Issuer.mint / Verifier.verify |
| 07.23 | EVIDENCE_READY | stateless |
| 07.24 | EVIDENCE_READY | leak/cleanup tests |
| 07.25 | EVIDENCE_READY | refusal audited |
| 07.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 07.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 07.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 07.29 | EVIDENCE_READY |  |
| 07.30 | EVIDENCE_READY |  |
| 07.31 | EVIDENCE_READY | reason=identity |
| 07.32 | EVIDENCE_READY |  |
| 07.33 | EVIDENCE_READY | runbook R3 |
| 07.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 07.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 07.36 | EVIDENCE_READY |  |
| 07.37 | EVIDENCE_READY |  |
| 07.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 07.39 | BLOCKED | needs independent review + owner; component blockers: No runtime attestation service; no replay-nonce store (tokens are short-lived bearer capabilities) |
| 07.40 | EVIDENCE_READY |  |
| 07.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 07.42 | EVIDENCE_READY |  |
| 07.43 | BLOCKED | no security review record: needs an independent reviewer |
| 07.44 | EVIDENCE_READY |  |
| 07.45 | BLOCKED | no trusted signature, no reviewer approval |
| 08.01 | IN_PROGRESS | seq, ts, event, correlation, details, prev, mac; no separate principal/policy-version fields |
| 08.02 | EVIDENCE_READY | closed EVENT_TYPES incl. refusals, deprecated use, lifecycle, config, migration, cancel |
| 08.03 | BLOCKED | append-only local file only; approved durable sink not available |
| 08.04 | EVIDENCE_READY | hash chain + HMAC + external head |
| 08.05 | EVIDENCE_READY | seq continues across restart; ts is recorded, ordering by seq |
| 08.06 | IN_PROGRESS | at-most-once per append; seq is the dedup id; no retry layer |
| 08.07 | IN_PROGRESS | synchronous append, fail-closed; bounded async buffer not implemented |
| 08.08 | EVIDENCE_READY |  |
| 08.09 | BLOCKED | retention/legal hold/access needs an owner: owners UNASSIGNED |
| 08.10 | EVIDENCE_READY | verify_chain + runbook verify-audit |
| 08.11 | IN_PROGRESS | outage, corrupt chain, restart, key mismatch; partial write/duplicate/full buffer not covered |
| 08.12 | IN_PROGRESS | audit_head in diagnostics; no backlog metric/alert |
| 08.13 | EVIDENCE_READY | 4 MUST requirements R08-xx, each with evidence refs |
| 08.14 | EVIDENCE_READY | boundary: Owns record format, chaining and local append. Does not own durable/WORM storage, retention or export. |
| 08.15 | EVIDENCE_READY | ceilings: record <= 4096 bytes; closed event vocabulary. |
| 08.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 08.17 | EVIDENCE_READY | {"external_policy": "audit key", "runtime": "sink path"} |
| 08.18 | EVIDENCE_READY | threats: log tampering |
| 08.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 08.20 | EVIDENCE_READY | fail closed |
| 08.21 | EVIDENCE_READY | codes: PK_AUDIT_* |
| 08.22 | EVIDENCE_READY | AuditSink.append / verify_chain |
| 08.23 | EVIDENCE_READY | lock around append |
| 08.24 | EVIDENCE_READY | leak/cleanup tests |
| 08.25 | EVIDENCE_READY | correlation_id per record |
| 08.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 08.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 08.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 08.29 | EVIDENCE_READY |  |
| 08.30 | EVIDENCE_READY |  |
| 08.31 | EVIDENCE_READY | audit_head in diagnostics |
| 08.32 | EVIDENCE_READY |  |
| 08.33 | EVIDENCE_READY | runbook R3 |
| 08.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 08.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 08.36 | EVIDENCE_READY |  |
| 08.37 | EVIDENCE_READY |  |
| 08.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 08.39 | BLOCKED | needs independent review + owner; component blockers: No approved durable/WORM sink, retention owner or key custody |
| 08.40 | EVIDENCE_READY |  |
| 08.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 08.42 | EVIDENCE_READY |  |
| 08.43 | BLOCKED | no security review record: needs an independent reviewer |
| 08.44 | EVIDENCE_READY |  |
| 08.45 | BLOCKED | no trusted signature, no reviewer approval |
| 09.01 | EVIDENCE_READY |  |
| 09.02 | EVIDENCE_READY | counter/histogram, ms units, process-local reset |
| 09.03 | EVIDENCE_READY | Prometheus text + OTLP/JSON body |
| 09.04 | EVIDENCE_READY |  |
| 09.05 | EVIDENCE_READY |  |
| 09.06 | EVIDENCE_READY | pull-based; record() is O(1) under a lock and cannot block on I/O |
| 09.07 | IN_PROGRESS | samples_dropped exposed; exporter health/last-success belong to the collector |
| 09.08 | IN_PROGRESS | buckets 1..60000 ms informed by bench; set-size histogram not exported |
| 09.09 | EVIDENCE_READY | process-local, process_epoch marks resets |
| 09.10 | IN_PROGRESS | high rate, cardinality attack, sampling; endpoint failure N/A without a collector |
| 09.11 | EVIDENCE_READY |  |
| 09.12 | EVIDENCE_READY |  |
| 09.13 | EVIDENCE_READY | 4 MUST requirements R09-xx, each with evidence refs |
| 09.14 | EVIDENCE_READY | boundary: Owns metric catalog and exposition bodies. Does not own push transport or collectors. |
| 09.15 | EVIDENCE_READY | ceilings: <= 64 tenant series + 16 buckets; closed outcome/reason sets. |
| 09.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 09.17 | EVIDENCE_READY | {"constant": "OUTCOMES, REASONS, LATENCY_BUCKETS_MS", "config": "sample_rate"} |
| 09.18 | EVIDENCE_READY | threats: cardinality attack |
| 09.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 09.20 | EVIDENCE_READY | pull-based; cannot block poll |
| 09.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 09.22 | EVIDENCE_READY | Telemetry.record / prometheus_text / otlp_json |
| 09.23 | EVIDENCE_READY | lock |
| 09.24 | EVIDENCE_READY | leak/cleanup tests |
| 09.25 | EVIDENCE_READY | no ids as labels (TEL-2) |
| 09.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 09.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 09.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 09.29 | EVIDENCE_READY |  |
| 09.30 | EVIDENCE_READY |  |
| 09.31 | EVIDENCE_READY | inv14_polls_total, inv14_poll_latency_ms |
| 09.32 | EVIDENCE_READY |  |
| 09.33 | EVIDENCE_READY | runbook R4 |
| 09.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 09.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 09.36 | EVIDENCE_READY |  |
| 09.37 | EVIDENCE_READY |  |
| 09.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 09.39 | BLOCKED | needs independent review + owner; component blockers: No collector endpoint for remote export |
| 09.40 | EVIDENCE_READY |  |
| 09.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 09.42 | EVIDENCE_READY |  |
| 09.43 | BLOCKED | no security review record: needs an independent reviewer |
| 09.44 | EVIDENCE_READY |  |
| 09.45 | BLOCKED | no trusted signature, no reviewer approval |
| 10.01 | EVIDENCE_READY |  |
| 10.02 | IN_PROGRESS | operation vocabulary closed; event names follow <op>.<outcome> but are not a closed enum |
| 10.03 | EVIDENCE_READY | code= field in refusal logs |
| 10.04 | EVIDENCE_READY |  |
| 10.05 | EVIDENCE_READY |  |
| 10.06 | IN_PROGRESS | security refusals always WARN and audited; no configurable sampling yet |
| 10.07 | EVIDENCE_READY | 4 KiB bound, _truncated marker |
| 10.08 | EVIDENCE_READY | correlation id propagated or created; never a metric label |
| 10.09 | EVIDENCE_READY |  |
| 10.10 | EVIDENCE_READY |  |
| 10.11 | EVIDENCE_READY | backend failure -> dropped counter; transport is integration-owned |
| 10.12 | EVIDENCE_READY |  |
| 10.13 | EVIDENCE_READY | 3 MUST requirements R10-xx, each with evidence refs |
| 10.14 | EVIDENCE_READY | boundary: Owns log schema and emission. Does not own transport/retention. |
| 10.15 | EVIDENCE_READY | ceilings: line <= 4096 bytes. |
| 10.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 10.17 | EVIDENCE_READY | {"constant": "LEVELS, OPERATIONS"} |
| 10.18 | EVIDENCE_READY | threats: log injection / secret leakage |
| 10.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 10.20 | EVIDENCE_READY | fail open (drop + count) -- logging never blocks polls; audit is the fail-closed record |
| 10.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 10.22 | EVIDENCE_READY | StructLogger.log |
| 10.23 | EVIDENCE_READY | lock |
| 10.24 | EVIDENCE_READY | leak/cleanup tests |
| 10.25 | EVIDENCE_READY | correlation_id, trace_id |
| 10.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 10.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 10.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 10.29 | EVIDENCE_READY |  |
| 10.30 | EVIDENCE_READY |  |
| 10.31 | EVIDENCE_READY | dropped counter |
| 10.32 | EVIDENCE_READY |  |
| 10.33 | EVIDENCE_READY | runbook R8 |
| 10.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 10.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 10.36 | EVIDENCE_READY |  |
| 10.37 | EVIDENCE_READY |  |
| 10.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 10.39 | BLOCKED | needs independent review + owner |
| 10.40 | EVIDENCE_READY |  |
| 10.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 10.42 | EVIDENCE_READY |  |
| 10.43 | BLOCKED | no security review record: needs an independent reviewer |
| 10.44 | EVIDENCE_READY |  |
| 10.45 | BLOCKED | no trusted signature, no reviewer approval |
| 11.01 | EVIDENCE_READY | W3C Trace Context level 1 |
| 11.02 | EVIDENCE_READY | traceparent/tracestate kwargs |
| 11.03 | IN_PROGRESS | child span id created; no span object/attributes exported |
| 11.04 | EVIDENCE_READY | only ids and bounded tracestate carried |
| 11.05 | BLOCKED | no WASI 0.2 runtime / compiled component / WIT toolchain available; real INV-15 not supplied; proven against protocol only |
| 11.06 | BLOCKED | span links need a span exporter |
| 11.07 | EVIDENCE_READY |  |
| 11.08 | EVIDENCE_READY | tracestate <= 512 / 32 members |
| 11.09 | EVIDENCE_READY | audit written regardless of trace flags |
| 11.10 | IN_PROGRESS | sampled/missing/malformed; adapter hops pending |
| 11.11 | BLOCKED | no tracing backend |
| 11.12 | EVIDENCE_READY | trace_id + correlation_id in every log; correlation_id in audit |
| 11.13 | EVIDENCE_READY | 3 MUST requirements R11-xx, each with evidence refs |
| 11.14 | EVIDENCE_READY | boundary: Owns context parsing/propagation. Does not own span export. |
| 11.15 | EVIDENCE_READY | ceilings: tracestate <= 512 chars / 32 members. |
| 11.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 11.17 | EVIDENCE_READY | {"constant": "W3C version 00"} |
| 11.18 | EVIDENCE_READY | threats: baggage as data channel |
| 11.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 11.20 | EVIDENCE_READY | fail open (new root) |
| 11.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 11.22 | EVIDENCE_READY | child_context() |
| 11.23 | EVIDENCE_READY | stateless |
| 11.24 | EVIDENCE_READY | leak/cleanup tests |
| 11.25 | EVIDENCE_READY | trace_id in logs |
| 11.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 11.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 11.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 11.29 | EVIDENCE_READY |  |
| 11.30 | EVIDENCE_READY |  |
| 11.31 | EVIDENCE_READY | inbound_valid flag |
| 11.32 | EVIDENCE_READY |  |
| 11.33 | EVIDENCE_READY | runbook R8 |
| 11.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 11.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 11.36 | EVIDENCE_READY |  |
| 11.37 | EVIDENCE_READY |  |
| 11.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 11.39 | BLOCKED | needs independent review + owner; component blockers: No span exporter/tracing backend |
| 11.40 | EVIDENCE_READY |  |
| 11.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 11.42 | EVIDENCE_READY |  |
| 11.43 | BLOCKED | no security review record: needs an independent reviewer |
| 11.44 | EVIDENCE_READY |  |
| 11.45 | BLOCKED | no trusted signature, no reviewer approval |
| 12.01 | IN_PROGRESS | enabled/deprecated/draining/disabled/quarantined; warn-only and deny-new modes not separate |
| 12.02 | EVIDENCE_READY | lifecycle.enter() is the first check |
| 12.03 | EVIDENCE_READY | in-flight allowed to finish |
| 12.04 | EVIDENCE_READY | single condition variable |
| 12.05 | BLOCKED | actor recorded but not authenticated: no admin identity provider |
| 12.06 | IN_PROGRESS | runbook transitions audited with actor; previous value not stored in the record |
| 12.07 | BLOCKED | break-glass needs time-limited admin authorisation |
| 12.08 | BLOCKED | no fleet deployment exists |
| 12.09 | EVIDENCE_READY | rollback under active load tested |
| 12.10 | IN_PROGRESS | disable vs in-flight, repeated toggles; unauthorised change/stale policy not testable yet |
| 12.11 | EVIDENCE_READY | lifecycle state + model version |
| 12.12 | EVIDENCE_READY | every alert links a runbook anchor |
| 12.13 | EVIDENCE_READY | 4 MUST requirements R12-xx, each with evidence refs |
| 12.14 | EVIDENCE_READY | boundary: Owns process-local switch. Does not own fleet propagation. |
| 12.15 | EVIDENCE_READY | ceilings: drain <= 60 s. |
| 12.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 12.17 | EVIDENCE_READY | {"runtime": "lifecycle state", "external": "operator"} |
| 12.18 | EVIDENCE_READY | threats: abuse continues during incident |
| 12.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 12.20 | EVIDENCE_READY | fail closed |
| 12.21 | EVIDENCE_READY | codes: PK_POLL_DRAINING, PK_POLL_DISABLED |
| 12.22 | EVIDENCE_READY | Lifecycle.emergency_disable / transition |
| 12.23 | EVIDENCE_READY | Condition variable; admission atomic with state |
| 12.24 | EVIDENCE_READY | leak/cleanup tests |
| 12.25 | EVIDENCE_READY | transition audited |
| 12.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 12.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 12.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 12.29 | EVIDENCE_READY |  |
| 12.30 | EVIDENCE_READY |  |
| 12.31 | EVIDENCE_READY | reason=policy |
| 12.32 | EVIDENCE_READY |  |
| 12.33 | EVIDENCE_READY | runbook R2 |
| 12.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 12.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 12.36 | EVIDENCE_READY |  |
| 12.37 | EVIDENCE_READY |  |
| 12.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 12.39 | BLOCKED | needs independent review + owner; component blockers: Actor is recorded but not authenticated (no admin identity provider); No fleet policy distribution |
| 12.40 | EVIDENCE_READY |  |
| 12.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 12.42 | EVIDENCE_READY |  |
| 12.43 | BLOCKED | no security review record: needs an independent reviewer |
| 12.44 | EVIDENCE_READY |  |
| 12.45 | BLOCKED | no trusted signature, no reviewer approval |
| 13.01 | IN_PROGRESS | id/owner/stage/dates; tenant/environment/API versions fields not yet |
| 13.02 | EVIDENCE_READY | waivers carry owner/approver/expiry/commitment |
| 13.03 | BLOCKED | no production telemetry to reconcile against |
| 13.04 | EVIDENCE_READY |  |
| 13.05 | IN_PROGRESS | ConsumerGate API; no report CLI |
| 13.06 | BLOCKED | needs usage telemetry |
| 13.07 | EVIDENCE_READY | PK_POLL_MIGRATION_REGRESSION + Inv14MigrationRegression |
| 13.08 | IN_PROGRESS | refusal alerts exist; pre-deadline alerts need a scheduler |
| 13.09 | IN_PROGRESS | parity record gates advancement; canary windows are operational |
| 13.10 | IN_PROGRESS | registry versioned with the package; no separate history store |
| 13.11 | EVIDENCE_READY | consumer_gate evaluated in the poll path |
| 13.12 | BLOCKED | closure workflow needs governance owner |
| 13.13 | EVIDENCE_READY | 4 MUST requirements R13-xx, each with evidence refs |
| 13.14 | EVIDENCE_READY | boundary: Owns schema + enforcement. Does not own the inventory data. |
| 13.15 | EVIDENCE_READY | ceilings: component_id <= 128 chars. |
| 13.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 13.17 | EVIDENCE_READY | {"external_policy": "governance/*.json"} |
| 13.18 | EVIDENCE_READY | threats: shadow consumers |
| 13.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 13.20 | EVIDENCE_READY | fail closed |
| 13.21 | EVIDENCE_READY | codes: PK_POLL_UNREGISTERED_CONSUMER, PK_POLL_MIGRATION_* |
| 13.22 | EVIDENCE_READY | ConsumerGate.check/register |
| 13.23 | EVIDENCE_READY | read-mostly |
| 13.24 | EVIDENCE_READY | leak/cleanup tests |
| 13.25 | EVIDENCE_READY | consumer id |
| 13.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 13.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 13.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 13.29 | EVIDENCE_READY |  |
| 13.30 | EVIDENCE_READY |  |
| 13.31 | EVIDENCE_READY | reason=policy |
| 13.32 | EVIDENCE_READY |  |
| 13.33 | EVIDENCE_READY | runbook R7 |
| 13.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 13.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 13.36 | EVIDENCE_READY |  |
| 13.37 | EVIDENCE_READY |  |
| 13.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 13.39 | BLOCKED | needs independent review + owner; component blockers: No consumer inventory supplied (inventory_status NOT_STARTED) |
| 13.40 | EVIDENCE_READY |  |
| 13.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 13.42 | EVIDENCE_READY |  |
| 13.43 | BLOCKED | no security review record: needs an independent reviewer |
| 13.44 | EVIDENCE_READY |  |
| 13.45 | BLOCKED | no trusted signature, no reviewer approval |
| 14.01 | IN_PROGRESS | 7 states; RETIRED represented by EOL REMOVED |
| 14.02 | IN_PROGRESS | table + actor/reason; per-edge authorisation not implemented |
| 14.03 | EVIDENCE_READY |  |
| 14.04 | EVIDENCE_READY |  |
| 14.05 | IN_PROGRESS | single process: checkpoint is source of truth; distributed N/A |
| 14.06 | EVIDENCE_READY | PK_POLL_LIFECYCLE/1 in diagnostics |
| 14.07 | EVIDENCE_READY | enter() and transition() share one lock |
| 14.08 | IN_PROGRESS | transitions audited; no lifecycle metric |
| 14.09 | EVIDENCE_READY | table checked against machine model |
| 14.10 | EVIDENCE_READY | all 42 ordered pairs |
| 14.11 | EVIDENCE_READY |  |
| 14.12 | EVIDENCE_READY |  |
| 14.13 | EVIDENCE_READY | 3 MUST requirements R14-xx, each with evidence refs |
| 14.14 | EVIDENCE_READY | boundary: Process-local state machine. |
| 14.15 | EVIDENCE_READY | ceilings: history <= 128. |
| 14.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 14.17 | EVIDENCE_READY | {"constant": "TRANSITIONS", "artifact": "schemas/pk_poll_lifecycle.json"} |
| 14.18 | EVIDENCE_READY | threats: coerced state |
| 14.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 14.20 | EVIDENCE_READY | fail closed |
| 14.21 | EVIDENCE_READY | codes: PK_POLL_ILLEGAL_TRANSITION |
| 14.22 | EVIDENCE_READY | Lifecycle |
| 14.23 | EVIDENCE_READY | Condition variable |
| 14.24 | EVIDENCE_READY | leak/cleanup tests |
| 14.25 | EVIDENCE_READY | transition records |
| 14.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 14.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 14.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 14.29 | EVIDENCE_READY |  |
| 14.30 | EVIDENCE_READY |  |
| 14.31 | EVIDENCE_READY | diagnostics.lifecycle |
| 14.32 | EVIDENCE_READY |  |
| 14.33 | EVIDENCE_READY | runbook R2 |
| 14.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 14.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 14.36 | EVIDENCE_READY |  |
| 14.37 | EVIDENCE_READY |  |
| 14.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 14.39 | BLOCKED | needs independent review + owner; component blockers: No RETIRED state yet (EOL removal withdraws the package instead); replica reconciliation not applicable in-process |
| 14.40 | EVIDENCE_READY |  |
| 14.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 14.42 | EVIDENCE_READY |  |
| 14.43 | BLOCKED | no security review record: needs an independent reviewer |
| 14.44 | EVIDENCE_READY |  |
| 14.45 | BLOCKED | no trusted signature, no reviewer approval |
| 15.01 | EVIDENCE_READY | RST-1..4 classification |
| 15.02 | EVIDENCE_READY | RST-4: not replayed; caller retries |
| 15.03 | IN_PROGRESS | process_epoch exists; pollable handles are in-process objects and cannot outlive the process |
| 15.04 | EVIDENCE_READY | level-triggered, re-derived |
| 15.05 | EVIDENCE_READY |  |
| 15.06 | EVIDENCE_READY |  |
| 15.07 | EVIDENCE_READY | polls are idempotent readiness reads |
| 15.08 | IN_PROGRESS | status restores checkpoint; automatic reconcile-before-accept not wired |
| 15.09 | IN_PROGRESS | SIGKILL during blocking wait; other kill points not injected |
| 15.10 | IN_PROGRESS | repeated save bounded; no restart-loop harness |
| 15.11 | IN_PROGRESS | epoch in diagnostics and poll logs; not in audit records |
| 15.12 | EVIDENCE_READY |  |
| 15.13 | EVIDENCE_READY | 3 MUST requirements R15-xx, each with evidence refs |
| 15.14 | EVIDENCE_READY | boundary: Owns process-local checkpoint. Readiness reconstruction is the host's job (RST-1). |
| 15.15 | EVIDENCE_READY | ceilings: checkpoint <= 16 KiB. |
| 15.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 15.17 | EVIDENCE_READY | {"runtime": "checkpoint path"} |
| 15.18 | EVIDENCE_READY | threats: false wake from stale readiness |
| 15.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 15.20 | EVIDENCE_READY | fail closed to safe defaults |
| 15.21 | EVIDENCE_READY | codes: PK_CHECKPOINT_* |
| 15.22 | EVIDENCE_READY | checkpoint.save/load/restore_or_default |
| 15.23 | EVIDENCE_READY | atomic os.replace |
| 15.24 | EVIDENCE_READY | leak/cleanup tests |
| 15.25 | EVIDENCE_READY | process_epoch in diagnostics/logs |
| 15.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 15.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 15.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 15.29 | EVIDENCE_READY |  |
| 15.30 | EVIDENCE_READY |  |
| 15.31 | EVIDENCE_READY | checkpoint_error |
| 15.32 | EVIDENCE_READY |  |
| 15.33 | EVIDENCE_READY | runbook R10 |
| 15.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 15.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 15.36 | EVIDENCE_READY |  |
| 15.37 | EVIDENCE_READY |  |
| 15.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 15.39 | BLOCKED | needs independent review + owner |
| 15.40 | EVIDENCE_READY |  |
| 15.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 15.42 | EVIDENCE_READY |  |
| 15.43 | BLOCKED | no security review record: needs an independent reviewer |
| 15.44 | EVIDENCE_READY |  |
| 15.45 | BLOCKED | no trusted signature, no reviewer approval |
| 16.01 | EVIDENCE_READY |  |
| 16.02 | EVIDENCE_READY | monotonic only; wall source refused |
| 16.03 | EVIDENCE_READY | integer arithmetic, rejection at ceiling |
| 16.04 | EVIDENCE_READY | no rounding |
| 16.05 | EVIDENCE_READY | zero refused; tick*max <= 60 s |
| 16.06 | IN_PROGRESS | jumps/anomalies bounded; suspend/VM pause not simulated |
| 16.07 | EVIDENCE_READY | after validation, at registration |
| 16.08 | EVIDENCE_READY |  |
| 16.09 | EVIDENCE_READY |  |
| 16.10 | EVIDENCE_READY | injectable clock |
| 16.11 | IN_PROGRESS | Python vs reference adapter; real runtime pending |
| 16.12 | EVIDENCE_READY |  |
| 16.13 | EVIDENCE_READY | 4 MUST requirements R16-xx, each with evidence refs |
| 16.14 | EVIDENCE_READY | boundary: Owns tick semantics. |
| 16.15 | EVIDENCE_READY | ceilings: 1 us <= tick <= 1 s. |
| 16.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 16.17 | EVIDENCE_READY | {"config": "PK_CLOCK_CONFIG/1"} |
| 16.18 | EVIDENCE_READY | threats: clock manipulation extends blocking |
| 16.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 16.20 | EVIDENCE_READY | fail closed on bad config |
| 16.21 | EVIDENCE_READY | codes: PK_CLOCK_* |
| 16.22 | EVIDENCE_READY | validate_clock_config, ticks_to_ns |
| 16.23 | EVIDENCE_READY | stateless |
| 16.24 | EVIDENCE_READY | leak/cleanup tests |
| 16.25 | EVIDENCE_READY | tick in diagnostics |
| 16.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 16.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 16.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 16.29 | EVIDENCE_READY |  |
| 16.30 | EVIDENCE_READY |  |
| 16.31 | EVIDENCE_READY | diagnostics.tick_seconds |
| 16.32 | EVIDENCE_READY |  |
| 16.33 | EVIDENCE_READY | runbook R8 |
| 16.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 16.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 16.36 | EVIDENCE_READY |  |
| 16.37 | EVIDENCE_READY |  |
| 16.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 16.39 | BLOCKED | needs independent review + owner |
| 16.40 | EVIDENCE_READY |  |
| 16.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 16.42 | EVIDENCE_READY |  |
| 16.43 | BLOCKED | no security review record: needs an independent reviewer |
| 16.44 | EVIDENCE_READY |  |
| 16.45 | BLOCKED | no trusted signature, no reviewer approval |
| 17.01 | BLOCKED | owners UNASSIGNED |
| 17.02 | BLOCKED | paths mapped; team handles owners UNASSIGNED |
| 17.03 | BLOCKED | owners UNASSIGNED |
| 17.04 | BLOCKED | owners UNASSIGNED |
| 17.05 | IN_PROGRESS | support boundary written; hours/targets need owner |
| 17.06 | IN_PROGRESS | runbook/dashboard refs; service catalog/change system unknown |
| 17.07 | IN_PROGRESS | versioned with package |
| 17.08 | EVIDENCE_READY | validator + blocker |
| 17.09 | BLOCKED | needs an independent reviewer/approver record |
| 17.10 | EVIDENCE_READY | owner required per consumer |
| 17.11 | EVIDENCE_READY | unregistered/ownerless consumer refused |
| 17.12 | EVIDENCE_READY | roles, no personal names |
| 17.13 | EVIDENCE_READY | 2 MUST requirements R17-xx, each with evidence refs |
| 17.14 | EVIDENCE_READY | boundary: Metadata only. |
| 17.15 | EVIDENCE_READY | ceilings: n/a |
| 17.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 17.17 | EVIDENCE_READY | {"external_policy": "governance/OWNERS.json"} |
| 17.18 | EVIDENCE_READY | threats: orphaned component |
| 17.19 | EVIDENCE_READY | no runtime operation |
| 17.20 | EVIDENCE_READY | blocks certification |
| 17.21 | EVIDENCE_READY | codes: PK_GOVERNANCE_INVALID |
| 17.22 | EVIDENCE_READY | governance/OWNERS.json |
| 17.23 | EVIDENCE_READY | static |
| 17.24 | EVIDENCE_READY | leak/cleanup tests |
| 17.25 | EVIDENCE_READY | n/a |
| 17.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 17.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 17.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 17.29 | EVIDENCE_READY |  |
| 17.30 | EVIDENCE_READY |  |
| 17.31 | EVIDENCE_READY | verify_release governance gate |
| 17.32 | EVIDENCE_READY |  |
| 17.33 | EVIDENCE_READY | runbook R0 |
| 17.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 17.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 17.36 | EVIDENCE_READY |  |
| 17.37 | EVIDENCE_READY |  |
| 17.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 17.39 | BLOCKED | needs independent review + owner; component blockers: The build cannot name owners, on-call routes or escalation |
| 17.40 | EVIDENCE_READY |  |
| 17.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 17.42 | EVIDENCE_READY |  |
| 17.43 | BLOCKED | no security review record: needs an independent reviewer |
| 17.44 | EVIDENCE_READY |  |
| 17.45 | BLOCKED | no trusted signature, no reviewer approval |
| 18.01 | IN_PROGRESS | numbered, status PROPOSED; deciders absent |
| 18.02 | IN_PROGRESS | rationale stated; concrete consumers unknown |
| 18.03 | IN_PROGRESS | alternatives not yet enumerated in the ADR |
| 18.04 | EVIDENCE_READY |  |
| 18.05 | EVIDENCE_READY |  |
| 18.06 | EVIDENCE_READY | restart semantics in ADR limits + RST-1..4; blockers vs follow-on listed in CHANGELOG release verdict |
| 18.07 | EVIDENCE_READY |  |
| 18.08 | EVIDENCE_READY |  |
| 18.09 | EVIDENCE_READY |  |
| 18.10 | IN_PROGRESS | links to lifecycle/runbook implicit; add explicit links |
| 18.11 | BLOCKED | needs an independent reviewer/approver record |
| 18.12 | EVIDENCE_READY | first ADR; nothing superseded |
| 18.13 | EVIDENCE_READY | 2 MUST requirements R18-xx, each with evidence refs |
| 18.14 | EVIDENCE_READY | boundary: Documentation. |
| 18.15 | EVIDENCE_READY | ceilings: n/a |
| 18.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 18.17 | EVIDENCE_READY | {} |
| 18.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 18.19 | EVIDENCE_READY | no runtime operation |
| 18.20 | EVIDENCE_READY | n/a |
| 18.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 18.22 | EVIDENCE_READY | docs/adr/ |
| 18.23 | EVIDENCE_READY | n/a |
| 18.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 18.25 | EVIDENCE_READY | n/a |
| 18.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 18.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 18.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 18.29 | EVIDENCE_READY |  |
| 18.30 | EVIDENCE_READY |  |
| 18.31 | EVIDENCE_READY | n/a |
| 18.32 | EVIDENCE_READY |  |
| 18.33 | EVIDENCE_READY | runbook R0 |
| 18.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 18.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 18.36 | EVIDENCE_READY |  |
| 18.37 | EVIDENCE_READY |  |
| 18.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 18.39 | BLOCKED | needs independent review + owner; component blockers: ADR is PROPOSED; no deciders exist to approve it |
| 18.40 | EVIDENCE_READY |  |
| 18.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 18.42 | EVIDENCE_READY |  |
| 18.43 | BLOCKED | no security review record: needs an independent reviewer |
| 18.44 | EVIDENCE_READY |  |
| 18.45 | BLOCKED | no trusted signature, no reviewer approval |
| 19.01 | EVIDENCE_READY |  |
| 19.02 | EVIDENCE_READY | UNTESTED is never supported |
| 19.03 | IN_PROGRESS | python_requires >=3.10,<3.14; known-bad list empty |
| 19.04 | IN_PROGRESS | matrix defined; not executed on a CI service |
| 19.05 | IN_PROGRESS | arm64 runner declared; not executed |
| 19.06 | BLOCKED | no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 19.07 | IN_PROGRESS | exact interpreter/platform for the one executed cell |
| 19.08 | BLOCKED | no prior supported release to roll back to |
| 19.09 | EVIDENCE_READY |  |
| 19.10 | BLOCKED | needs an independent reviewer/approver record |
| 19.11 | IN_PROGRESS | interpreter range enforced by probe |
| 19.12 | EVIDENCE_READY | archived with release |
| 19.13 | EVIDENCE_READY | 2 MUST requirements R19-xx, each with evidence refs |
| 19.14 | EVIDENCE_READY | boundary: Documentation + CI matrix. |
| 19.15 | EVIDENCE_READY | ceilings: n/a |
| 19.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 19.17 | EVIDENCE_READY | {} |
| 19.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 19.19 | EVIDENCE_READY | no runtime operation |
| 19.20 | EVIDENCE_READY | untested = unsupported |
| 19.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 19.22 | EVIDENCE_READY | docs/COMPATIBILITY_MATRIX.json |
| 19.23 | EVIDENCE_READY | n/a |
| 19.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 19.25 | EVIDENCE_READY | n/a |
| 19.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 19.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 19.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 19.29 | EVIDENCE_READY |  |
| 19.30 | EVIDENCE_READY |  |
| 19.31 | EVIDENCE_READY | n/a |
| 19.32 | EVIDENCE_READY |  |
| 19.33 | EVIDENCE_READY | runbook R1 |
| 19.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 19.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 19.36 | EVIDENCE_READY |  |
| 19.37 | EVIDENCE_READY |  |
| 19.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 19.39 | BLOCKED | needs independent review + owner; component blockers: Only one cell (CPython 3.11 / linux / x86_64, simulated WASI) could be executed here |
| 19.40 | EVIDENCE_READY |  |
| 19.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 19.42 | EVIDENCE_READY |  |
| 19.43 | BLOCKED | no security review record: needs an independent reviewer |
| 19.44 | EVIDENCE_READY |  |
| 19.45 | BLOCKED | no trusted signature, no reviewer approval |
| 20.01 | BLOCKED | INV-13/INV-15/GAP-15 not supplied |
| 20.02 | BLOCKED | tests written against real modules; skipped: layers absent |
| 20.03 | BLOCKED | layers absent |
| 20.04 | BLOCKED | layers absent |
| 20.05 | BLOCKED | layers absent |
| 20.06 | BLOCKED | layers absent |
| 20.07 | EVIDENCE_READY | version mismatch fails closed |
| 20.08 | BLOCKED | layers absent |
| 20.09 | EVIDENCE_READY | stdlib-only, temp dirs, no network |
| 20.10 | EVIDENCE_READY |  |
| 20.11 | EVIDENCE_READY |  |
| 20.12 | EVIDENCE_READY | --skip-slow smoke vs full |
| 20.13 | EVIDENCE_READY | 2 MUST requirements R20-xx, each with evidence refs |
| 20.14 | EVIDENCE_READY | boundary: Tests only. |
| 20.15 | EVIDENCE_READY | ceilings: n/a |
| 20.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 20.17 | EVIDENCE_READY | {"env": "PK_ADJACENT_PATH, INV14_RELEASE"} |
| 20.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 20.19 | EVIDENCE_READY | no runtime operation |
| 20.20 | EVIDENCE_READY | fail in release |
| 20.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 20.22 | EVIDENCE_READY | unittest |
| 20.23 | EVIDENCE_READY | n/a |
| 20.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 20.25 | EVIDENCE_READY | n/a |
| 20.26 | BLOCKED | required tests not passing/skipped: T:C20Adjacent |
| 20.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 20.28 | BLOCKED | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 20.29 | EVIDENCE_READY |  |
| 20.30 | EVIDENCE_READY |  |
| 20.31 | EVIDENCE_READY | n/a |
| 20.32 | EVIDENCE_READY |  |
| 20.33 | EVIDENCE_READY | runbook R1 |
| 20.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 20.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 20.36 | EVIDENCE_READY |  |
| 20.37 | EVIDENCE_READY |  |
| 20.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 20.39 | BLOCKED | needs independent review + owner; component blockers: INV-13, INV-15 and GAP-15 packages were not supplied |
| 20.40 | EVIDENCE_READY |  |
| 20.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 20.42 | IN_PROGRESS |  |
| 20.43 | BLOCKED | no security review record: needs an independent reviewer |
| 20.44 | EVIDENCE_READY |  |
| 20.45 | BLOCKED | no trusted signature, no reviewer approval |
| 21.01 | EVIDENCE_READY |  |
| 21.02 | EVIDENCE_READY |  |
| 21.03 | EVIDENCE_READY |  |
| 21.04 | EVIDENCE_READY | extra_property negatives; policy in CONTRACT_POLICY |
| 21.05 | EVIDENCE_READY | wrong_schema_const (future major) rejected |
| 21.06 | EVIDENCE_READY |  |
| 21.07 | EVIDENCE_READY |  |
| 21.08 | EVIDENCE_READY |  |
| 21.09 | BLOCKED | no WASI 0.2 runtime / compiled component / WIT toolchain available |
| 21.10 | EVIDENCE_READY |  |
| 21.11 | EVIDENCE_READY | reference vs adapter |
| 21.12 | EVIDENCE_READY | python3 schema_check.py usable by downstream |
| 21.13 | EVIDENCE_READY | 2 MUST requirements R21-xx, each with evidence refs |
| 21.14 | EVIDENCE_READY | boundary: Tests only. |
| 21.15 | EVIDENCE_READY | ceilings: n/a |
| 21.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 21.17 | EVIDENCE_READY | {} |
| 21.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 21.19 | EVIDENCE_READY | no runtime operation |
| 21.20 | EVIDENCE_READY | fail on drift |
| 21.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 21.22 | EVIDENCE_READY | fixtures |
| 21.23 | EVIDENCE_READY | n/a |
| 21.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 21.25 | EVIDENCE_READY | n/a |
| 21.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 21.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 21.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 21.29 | EVIDENCE_READY |  |
| 21.30 | EVIDENCE_READY |  |
| 21.31 | EVIDENCE_READY | n/a |
| 21.32 | EVIDENCE_READY |  |
| 21.33 | EVIDENCE_READY | runbook R1 |
| 21.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 21.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 21.36 | EVIDENCE_READY |  |
| 21.37 | EVIDENCE_READY |  |
| 21.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 21.39 | BLOCKED | needs independent review + owner; component blockers: No WIT bindings in a second language to round-trip |
| 21.40 | EVIDENCE_READY |  |
| 21.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 21.42 | EVIDENCE_READY |  |
| 21.43 | BLOCKED | no security review record: needs an independent reviewer |
| 21.44 | EVIDENCE_READY |  |
| 21.45 | BLOCKED | no trusted signature, no reviewer approval |
| 22.01 | IN_PROGRESS | poll/token/config/trace targets; schema-decoding target separate not built |
| 22.02 | EVIDENCE_READY | structure-aware mutation of valid documents |
| 22.03 | IN_PROGRESS | seeded from valid config/token; golden corpus not loaded |
| 22.04 | EVIDENCE_READY | unicode, extremes, type confusion, duplicates |
| 22.05 | EVIDENCE_READY | structured-code oracle + schema-valid result + 2 s per input |
| 22.06 | IN_PROGRESS | time limit; no memory limit |
| 22.07 | EVIDENCE_READY | findings promoted to regression tests |
| 22.08 | EVIDENCE_READY | seed, iterations, per-target counts |
| 22.09 | IN_PROGRESS | 8,000-iteration release budget; no scheduled campaign |
| 22.10 | BLOCKED | no coverage tool in stdlib environment |
| 22.11 | IN_PROGRESS |  |
| 22.12 | EVIDENCE_READY | in-process, no network/files |
| 22.13 | EVIDENCE_READY | 2 MUST requirements R22-xx, each with evidence refs |
| 22.14 | EVIDENCE_READY | boundary: Tests only. |
| 22.15 | EVIDENCE_READY | ceilings: 2 s per input. |
| 22.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 22.17 | EVIDENCE_READY | {} |
| 22.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 22.19 | EVIDENCE_READY | no runtime operation |
| 22.20 | EVIDENCE_READY | n/a |
| 22.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 22.22 | EVIDENCE_READY | tools/fuzz.py |
| 22.23 | EVIDENCE_READY | n/a |
| 22.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 22.25 | EVIDENCE_READY | seed |
| 22.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 22.27 | EVIDENCE_READY | regressions for D-02, D-03 |
| 22.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 22.29 | EVIDENCE_READY |  |
| 22.30 | EVIDENCE_READY |  |
| 22.31 | EVIDENCE_READY | n/a |
| 22.32 | EVIDENCE_READY |  |
| 22.33 | EVIDENCE_READY | runbook R8 |
| 22.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 22.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 22.36 | EVIDENCE_READY |  |
| 22.37 | EVIDENCE_READY |  |
| 22.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 22.39 | BLOCKED | needs independent review + owner; component blockers: No coverage-guided engine (atheris) or coverage report |
| 22.40 | EVIDENCE_READY |  |
| 22.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 22.42 | EVIDENCE_READY |  |
| 22.43 | BLOCKED | no security review record: needs an independent reviewer |
| 22.44 | EVIDENCE_READY |  |
| 22.45 | BLOCKED | no trusted signature, no reviewer approval |
| 23.01 | EVIDENCE_READY |  |
| 23.02 | EVIDENCE_READY | S1 (latch under lock) and REG are the linearisation points |
| 23.03 | EVIDENCE_READY | exhaustive state exploration |
| 23.04 | IN_PROGRESS | signal before/during/after register, clear-vs-signal, cancel-vs-ready; disable-vs-register covered by C12 |
| 23.05 | EVIDENCE_READY |  |
| 23.06 | EVIDENCE_READY |  |
| 23.07 | IN_PROGRESS | randomised threads; no process-level repetition |
| 23.08 | BLOCKED | no native bindings exist yet |
| 23.09 | EVIDENCE_READY | counterexample states returned |
| 23.10 | EVIDENCE_READY |  |
| 23.11 | IN_PROGRESS | policy transitions under load; restart not in campaigns |
| 23.12 | EVIDENCE_READY | release gate requires zero violations |
| 23.13 | EVIDENCE_READY | 2 MUST requirements R23-xx, each with evidence refs |
| 23.14 | EVIDENCE_READY | boundary: Tests only; the model is of the protocol, not the bytecode. |
| 23.15 | EVIDENCE_READY | ceilings: n/a |
| 23.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 23.17 | EVIDENCE_READY | {} |
| 23.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 23.19 | EVIDENCE_READY | no runtime operation |
| 23.20 | EVIDENCE_READY | n/a |
| 23.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 23.22 | EVIDENCE_READY | tools/interleave.py |
| 23.23 | EVIDENCE_READY | n/a |
| 23.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 23.25 | EVIDENCE_READY | n/a |
| 23.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 23.27 | EVIDENCE_READY | regressions for D-01 |
| 23.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 23.29 | EVIDENCE_READY |  |
| 23.30 | EVIDENCE_READY |  |
| 23.31 | EVIDENCE_READY | n/a |
| 23.32 | EVIDENCE_READY |  |
| 23.33 | EVIDENCE_READY | runbook R8 |
| 23.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 23.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 23.36 | EVIDENCE_READY |  |
| 23.37 | EVIDENCE_READY |  |
| 23.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 23.39 | BLOCKED | needs independent review + owner; component blockers: No TSAN-equivalent: no native bindings exist yet |
| 23.40 | EVIDENCE_READY |  |
| 23.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 23.42 | EVIDENCE_READY |  |
| 23.43 | BLOCKED | no security review record: needs an independent reviewer |
| 23.44 | EVIDENCE_READY |  |
| 23.45 | BLOCKED | no trusted signature, no reviewer approval |
| 24.01 | IN_PROGRESS | ready/wake/timeout/fan-out/import separated; per-phase split not instrumented |
| 24.02 | IN_PROGRESS | p50/p95/p99/max; no p90/p99.9/variance |
| 24.03 | EVIDENCE_READY | 1, 64, 1024, 4096 |
| 24.04 | EVIDENCE_READY | timeout_overshoot separate |
| 24.05 | IN_PROGRESS | saturation via soak; not a stepped concurrency sweep |
| 24.06 | IN_PROGRESS | wall time, alloc peak; CPU/RSS/threads not |
| 24.07 | BLOCKED | no WASI 0.2 runtime / compiled component / WIT toolchain available; real INV-15 not supplied; proven against protocol only |
| 24.08 | IN_PROGRESS | host metadata; no affinity/power control |
| 24.09 | BLOCKED | PROPOSED thresholds: needs an independent reviewer/approver record |
| 24.10 | IN_PROGRESS | repeated samples; no statistical comparison |
| 24.11 | IN_PROGRESS | summaries archived; raw samples not |
| 24.12 | EVIDENCE_READY | gate compares against thresholds (PROPOSED) |
| 24.13 | EVIDENCE_READY | 2 MUST requirements R24-xx, each with evidence refs |
| 24.14 | EVIDENCE_READY | boundary: Tests only. |
| 24.15 | EVIDENCE_READY | ceilings: n/a |
| 24.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 24.17 | EVIDENCE_READY | {"external_policy": "ops/perf_thresholds.json"} |
| 24.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 24.19 | EVIDENCE_READY | no runtime operation |
| 24.20 | EVIDENCE_READY | n/a |
| 24.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 24.22 | EVIDENCE_READY | tools/bench.py |
| 24.23 | EVIDENCE_READY | n/a |
| 24.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 24.25 | EVIDENCE_READY | n/a |
| 24.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 24.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 24.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 24.29 | EVIDENCE_READY |  |
| 24.30 | EVIDENCE_READY |  |
| 24.31 | EVIDENCE_READY | n/a |
| 24.32 | EVIDENCE_READY |  |
| 24.33 | EVIDENCE_READY | runbook R8 |
| 24.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 24.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 24.36 | EVIDENCE_READY |  |
| 24.37 | EVIDENCE_READY |  |
| 24.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 24.39 | BLOCKED | needs independent review + owner; component blockers: Thresholds are PROPOSED; power/thermal not measurable |
| 24.40 | EVIDENCE_READY |  |
| 24.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 24.42 | EVIDENCE_READY |  |
| 24.43 | BLOCKED | no security review record: needs an independent reviewer |
| 24.44 | EVIDENCE_READY |  |
| 24.45 | BLOCKED | no trusted signature, no reviewer approval |
| 25.01 | IN_PROGRESS | one profile (200-300 tenants, mixed ready/timeout) |
| 25.02 | BLOCKED | long-duration soak not run in this environment |
| 25.03 | EVIDENCE_READY | 4x burst |
| 25.04 | EVIDENCE_READY | 300 tenants, telemetry bounded |
| 25.05 | IN_PROGRESS | counts/shed/waiters/audit; memory/GC not |
| 25.06 | EVIDENCE_READY | zero active/in-flight/waiters after |
| 25.07 | BLOCKED | no rolling-restart harness |
| 25.08 | IN_PROGRESS | mixed tenants; abusive class not separated |
| 25.09 | IN_PROGRESS | audit loss (F3) outside soak |
| 25.10 | EVIDENCE_READY | numeric invariants |
| 25.11 | IN_PROGRESS | summary archived |
| 25.12 | EVIDENCE_READY | short burst per release |
| 25.13 | EVIDENCE_READY | 1 MUST requirements R25-xx, each with evidence refs |
| 25.14 | EVIDENCE_READY | boundary: Tests only; single process. |
| 25.15 | EVIDENCE_READY | ceilings: n/a |
| 25.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 25.17 | EVIDENCE_READY | {} |
| 25.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 25.19 | EVIDENCE_READY | no runtime operation |
| 25.20 | EVIDENCE_READY | n/a |
| 25.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 25.22 | EVIDENCE_READY | tools/soak.py |
| 25.23 | EVIDENCE_READY | n/a |
| 25.24 | EVIDENCE_READY | leak/cleanup tests |
| 25.25 | EVIDENCE_READY | n/a |
| 25.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 25.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 25.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 25.29 | EVIDENCE_READY |  |
| 25.30 | EVIDENCE_READY |  |
| 25.31 | EVIDENCE_READY | n/a |
| 25.32 | EVIDENCE_READY |  |
| 25.33 | EVIDENCE_READY | runbook R4 |
| 25.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 25.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 25.36 | EVIDENCE_READY |  |
| 25.37 | EVIDENCE_READY |  |
| 25.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 25.39 | BLOCKED | needs independent review + owner; component blockers: Long-duration and fleet-scale runs not performed here |
| 25.40 | EVIDENCE_READY |  |
| 25.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 25.42 | EVIDENCE_READY |  |
| 25.43 | BLOCKED | no security review record: needs an independent reviewer |
| 25.44 | EVIDENCE_READY |  |
| 25.45 | BLOCKED | no trusted signature, no reviewer approval |
| 26.01 | EVIDENCE_READY |  |
| 26.02 | IN_PROGRESS | jumps via fake clock; suspend/resume not |
| 26.03 | IN_PROGRESS | admission exhaustion (soak), dropped timer; waiter-registration failure not injected |
| 26.04 | EVIDENCE_READY | boundary recorded: no networked layer inside INV-14 (proposed N/A needs reviewer) |
| 26.05 | EVIDENCE_READY |  |
| 26.06 | EVIDENCE_READY |  |
| 26.07 | EVIDENCE_READY | deterministic triggers |
| 26.08 | IN_PROGRESS | before admission, during wait; not every boundary |
| 26.09 | EVIDENCE_READY | runbook disable works with no telemetry/pk_core |
| 26.10 | IN_PROGRESS | consistency asserted; recovery time not measured |
| 26.11 | BLOCKED | no production incidents yet |
| 26.12 | EVIDENCE_READY | temp dirs, child processes, no credentials |
| 26.13 | EVIDENCE_READY | 1 MUST requirements R26-xx, each with evidence refs |
| 26.14 | EVIDENCE_READY | boundary: Tests only. Network partition not applicable (no network I/O). |
| 26.15 | EVIDENCE_READY | ceilings: n/a |
| 26.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 26.17 | EVIDENCE_READY | {} |
| 26.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 26.19 | EVIDENCE_READY | no runtime operation |
| 26.20 | EVIDENCE_READY | n/a |
| 26.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 26.22 | EVIDENCE_READY | tools/faults.py |
| 26.23 | EVIDENCE_READY | n/a |
| 26.24 | EVIDENCE_READY | leak/cleanup tests |
| 26.25 | EVIDENCE_READY | n/a |
| 26.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 26.27 | EVIDENCE_READY | regressions for D-04 |
| 26.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 26.29 | EVIDENCE_READY |  |
| 26.30 | EVIDENCE_READY |  |
| 26.31 | EVIDENCE_READY | n/a |
| 26.32 | EVIDENCE_READY |  |
| 26.33 | EVIDENCE_READY | runbook R10 |
| 26.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 26.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 26.36 | EVIDENCE_READY |  |
| 26.37 | EVIDENCE_READY |  |
| 26.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 26.39 | BLOCKED | needs independent review + owner |
| 26.40 | EVIDENCE_READY |  |
| 26.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 26.42 | EVIDENCE_READY |  |
| 26.43 | BLOCKED | no security review record: needs an independent reviewer |
| 26.44 | EVIDENCE_READY |  |
| 26.45 | BLOCKED | no trusted signature, no reviewer approval |
| 27.01 | IN_PROGRESS | actions pinned by major tag, not digest |
| 27.02 | EVIDENCE_READY |  |
| 27.03 | EVIDENCE_READY |  |
| 27.04 | BLOCKED | real pk_core not supplied; lock UNRESOLVED |
| 27.05 | IN_PROGRESS | schema/golden in gate; WIT parser and real runtime absent |
| 27.06 | IN_PROGRESS | dependency scan; no static analysis/secret scanner |
| 27.07 | EVIDENCE_READY |  |
| 27.08 | EVIDENCE_READY |  |
| 27.09 | BLOCKED | no protected release signing context |
| 27.10 | BLOCKED | branch protection is a repository setting |
| 27.11 | IN_PROGRESS | upload-artifact step |
| 27.12 | EVIDENCE_READY | clean-room run from the zip |
| 27.13 | EVIDENCE_READY | 2 MUST requirements R27-xx, each with evidence refs |
| 27.14 | EVIDENCE_READY | boundary: Pipeline definition. |
| 27.15 | EVIDENCE_READY | ceilings: n/a |
| 27.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 27.17 | EVIDENCE_READY | {"env": "INV14_RELEASE"} |
| 27.18 | EVIDENCE_READY | threats: assumed-pass path |
| 27.19 | EVIDENCE_READY | no runtime operation |
| 27.20 | EVIDENCE_READY | fail closed |
| 27.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 27.22 | EVIDENCE_READY | verify_release.py |
| 27.23 | EVIDENCE_READY | n/a |
| 27.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 27.25 | EVIDENCE_READY | report JSON |
| 27.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 27.27 | EVIDENCE_READY | regressions for D-04 |
| 27.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 27.29 | EVIDENCE_READY |  |
| 27.30 | EVIDENCE_READY |  |
| 27.31 | EVIDENCE_READY | n/a |
| 27.32 | EVIDENCE_READY |  |
| 27.33 | EVIDENCE_READY | runbook R0 |
| 27.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 27.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 27.36 | EVIDENCE_READY |  |
| 27.37 | EVIDENCE_READY |  |
| 27.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 27.39 | BLOCKED | needs independent review + owner; component blockers: The workflow has not executed on a CI service; branch protection is a repository setting |
| 27.40 | EVIDENCE_READY |  |
| 27.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 27.42 | EVIDENCE_READY |  |
| 27.43 | BLOCKED | no security review record: needs an independent reviewer |
| 27.44 | EVIDENCE_READY |  |
| 27.45 | BLOCKED | no trusted signature, no reviewer approval |
| 28.01 | IN_PROGRESS | INV-14 has zero runtime deps; pk_core unresolved |
| 28.02 | EVIDENCE_READY |  |
| 28.03 | IN_PROGRESS | files + pk_core + optional cryptography; build container N/A |
| 28.04 | IN_PROGRESS | unsigned; builder identity absent |
| 28.05 | IN_PROGRESS | subject digest over file set; archive checksum recorded in evidence |
| 28.06 | BLOCKED | pk_core INDETERMINATE; no vulnerability DB in environment |
| 28.07 | IN_PROGRESS | no third-party runtime code to attribute |
| 28.08 | BLOCKED | owners UNASSIGNED |
| 28.09 | EVIDENCE_READY | stdlib only: nothing to mirror (pk_core pending) |
| 28.10 | EVIDENCE_READY | two builds compared |
| 28.11 | EVIDENCE_READY |  |
| 28.12 | EVIDENCE_READY |  |
| 28.13 | EVIDENCE_READY | 2 MUST requirements R28-xx, each with evidence refs |
| 28.14 | EVIDENCE_READY | boundary: Supply-chain metadata. |
| 28.15 | EVIDENCE_READY | ceilings: n/a |
| 28.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 28.17 | EVIDENCE_READY | {} |
| 28.18 | EVIDENCE_READY | threats: undeclared dependency |
| 28.19 | EVIDENCE_READY | no runtime operation |
| 28.20 | EVIDENCE_READY | INDETERMINATE is not a pass |
| 28.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 28.22 | EVIDENCE_READY | sbom/* |
| 28.23 | EVIDENCE_READY | n/a |
| 28.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 28.25 | EVIDENCE_READY | digest |
| 28.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 28.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 28.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 28.29 | EVIDENCE_READY |  |
| 28.30 | EVIDENCE_READY |  |
| 28.31 | EVIDENCE_READY | n/a |
| 28.32 | EVIDENCE_READY |  |
| 28.33 | EVIDENCE_READY | runbook R0 |
| 28.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 28.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 28.36 | EVIDENCE_READY |  |
| 28.37 | EVIDENCE_READY |  |
| 28.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 28.39 | BLOCKED | needs independent review + owner; component blockers: pk_core cannot be scanned until pinned; provenance unsigned |
| 28.40 | EVIDENCE_READY |  |
| 28.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 28.42 | EVIDENCE_READY |  |
| 28.43 | BLOCKED | no security review record: needs an independent reviewer |
| 28.44 | EVIDENCE_READY |  |
| 28.45 | BLOCKED | no trusted signature, no reviewer approval |
| 29.01 | EVIDENCE_READY | Ed25519 detached over manifest |
| 29.02 | IN_PROGRESS | manifest covers SBOM/provenance/schemas; archive signed via its manifest |
| 29.03 | BLOCKED | no HSM/KMS or protected release credential |
| 29.04 | BLOCKED | only UNTRUSTED_DEV key; trust root owners UNASSIGNED |
| 29.05 | EVIDENCE_READY | one command: tools/sign.py verify --require-trusted |
| 29.06 | EVIDENCE_READY |  |
| 29.07 | IN_PROGRESS | REVOKED status honoured; rotation procedure not exercised with overlap |
| 29.08 | BLOCKED | no timestamp/transparency service |
| 29.09 | EVIDENCE_READY | altered manifest, wrong/untrusted/revoked signer |
| 29.10 | EVIDENCE_READY | key id + manifest digest, no private material |
| 29.11 | EVIDENCE_READY | trusted_signature is a required external gate in verify_release (currently BLOCKED: UNTRUSTED_DEV) |
| 29.12 | IN_PROGRESS | public keys ship in-package |
| 29.13 | EVIDENCE_READY | 3 MUST requirements R29-xx, each with evidence refs |
| 29.14 | EVIDENCE_READY | boundary: Signing tooling; key custody is external. |
| 29.15 | EVIDENCE_READY | ceilings: n/a |
| 29.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 29.17 | EVIDENCE_READY | {"external_policy": "governance/TRUSTED_KEYS.json"} |
| 29.18 | EVIDENCE_READY | threats: tampered release |
| 29.19 | EVIDENCE_READY | no runtime operation |
| 29.20 | EVIDENCE_READY | fail closed |
| 29.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 29.22 | EVIDENCE_READY | tools/sign.py |
| 29.23 | EVIDENCE_READY | n/a |
| 29.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 29.25 | EVIDENCE_READY | key_id |
| 29.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 29.27 | EVIDENCE_READY | regressions for D-06 |
| 29.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 29.29 | EVIDENCE_READY |  |
| 29.30 | EVIDENCE_READY |  |
| 29.31 | EVIDENCE_READY | n/a |
| 29.32 | EVIDENCE_READY |  |
| 29.33 | EVIDENCE_READY | runbook R0 |
| 29.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 29.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 29.36 | EVIDENCE_READY |  |
| 29.37 | EVIDENCE_READY |  |
| 29.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 29.39 | BLOCKED | needs independent review + owner; component blockers: Only an UNTRUSTED_DEV key exists; no HSM/KMS, trust root or transparency log |
| 29.40 | EVIDENCE_READY |  |
| 29.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 29.42 | EVIDENCE_READY |  |
| 29.43 | BLOCKED | no security review record: needs an independent reviewer |
| 29.44 | EVIDENCE_READY |  |
| 29.45 | BLOCKED | no trusted signature, no reviewer approval |
| 30.01 | EVIDENCE_READY |  |
| 30.02 | EVIDENCE_READY |  |
| 30.03 | EVIDENCE_READY | base -> environment -> site |
| 30.04 | EVIDENCE_READY |  |
| 30.05 | EVIDENCE_READY |  |
| 30.06 | EVIDENCE_READY |  |
| 30.07 | IN_PROGRESS | all fields dynamic via store; restart-only fields not classified |
| 30.08 | IN_PROGRESS | history of versions/digests; rollback = re-apply previous doc |
| 30.09 | BLOCKED | no admin identity |
| 30.10 | EVIDENCE_READY | no secret fields in schema |
| 30.11 | IN_PROGRESS | schema/bounds/precedence/atomicity/corruption; concurrent updates not tested |
| 30.12 | IN_PROGRESS | diagnostics expose schema digests; active config version not yet |
| 30.13 | EVIDENCE_READY | 3 MUST requirements R30-xx, each with evidence refs |
| 30.14 | EVIDENCE_READY | boundary: Owns validation and activation. |
| 30.15 | EVIDENCE_READY | ceilings: doc <= 64 KiB, history <= 64. |
| 30.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 30.17 | EVIDENCE_READY | {"config": "PK_POLL_CONFIG/1"} |
| 30.18 | EVIDENCE_READY | threats: unsafe live change |
| 30.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 30.20 | EVIDENCE_READY | fail closed (active config kept) |
| 30.21 | EVIDENCE_READY | codes: PK_CONFIG_* |
| 30.22 | EVIDENCE_READY | ConfigStore.update |
| 30.23 | EVIDENCE_READY | lock |
| 30.24 | EVIDENCE_READY | leak/cleanup tests |
| 30.25 | EVIDENCE_READY | config version + digest |
| 30.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 30.27 | EVIDENCE_READY | regressions for D-02, D-03 |
| 30.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 30.29 | EVIDENCE_READY |  |
| 30.30 | EVIDENCE_READY |  |
| 30.31 | EVIDENCE_READY | history |
| 30.32 | EVIDENCE_READY |  |
| 30.33 | EVIDENCE_READY | runbook R4 |
| 30.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 30.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 30.36 | EVIDENCE_READY |  |
| 30.37 | EVIDENCE_READY |  |
| 30.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 30.39 | BLOCKED | needs independent review + owner; component blockers: Update authorization not authenticated (no admin identity) |
| 30.40 | EVIDENCE_READY |  |
| 30.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 30.42 | EVIDENCE_READY |  |
| 30.43 | BLOCKED | no security review record: needs an independent reviewer |
| 30.44 | EVIDENCE_READY |  |
| 30.45 | BLOCKED | no trusted signature, no reviewer approval |
| 31.01 | IN_PROGRESS | classification implicit in redaction policy; no table |
| 31.02 | EVIDENCE_READY |  |
| 31.03 | IN_PROGRESS | fixed top-level fields; free-form fields rely on pattern redaction |
| 31.04 | EVIDENCE_READY |  |
| 31.05 | EVIDENCE_READY |  |
| 31.06 | EVIDENCE_READY | tenant bucketed in metrics; foreign names never disclosed |
| 31.07 | EVIDENCE_READY |  |
| 31.08 | EVIDENCE_READY | canary token and key |
| 31.09 | IN_PROGRESS | nested/oversized/unicode; base64-only secrets not detected |
| 31.10 | BLOCKED | owners UNASSIGNED |
| 31.11 | BLOCKED | needs an independent reviewer/approver record |
| 31.12 | IN_PROGRESS | R3 covers key rotation; full exposure procedure pending |
| 31.13 | EVIDENCE_READY | 2 MUST requirements R31-xx, each with evidence refs |
| 31.14 | EVIDENCE_READY | boundary: Owns redaction function. |
| 31.15 | EVIDENCE_READY | ceilings: 256 chars, depth 4, 32 items. |
| 31.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 31.17 | EVIDENCE_READY | {"constant": "patterns"} |
| 31.18 | EVIDENCE_READY | threats: credential leak |
| 31.19 | EVIDENCE_READY | service order: lifecycle -> identity -> governance -> admission -> poll |
| 31.20 | EVIDENCE_READY | redact on doubt |
| 31.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 31.22 | EVIDENCE_READY | redact() |
| 31.23 | EVIDENCE_READY | pure |
| 31.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 31.25 | EVIDENCE_READY | n/a |
| 31.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 31.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 31.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 31.29 | EVIDENCE_READY |  |
| 31.30 | EVIDENCE_READY |  |
| 31.31 | EVIDENCE_READY | n/a |
| 31.32 | EVIDENCE_READY |  |
| 31.33 | EVIDENCE_READY | runbook R3 |
| 31.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 31.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 31.36 | EVIDENCE_READY |  |
| 31.37 | EVIDENCE_READY |  |
| 31.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 31.39 | BLOCKED | needs independent review + owner |
| 31.40 | EVIDENCE_READY |  |
| 31.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 31.42 | EVIDENCE_READY |  |
| 31.43 | BLOCKED | no security review record: needs an independent reviewer |
| 31.44 | EVIDENCE_READY |  |
| 31.45 | BLOCKED | no trusted signature, no reviewer approval |
| 32.01 | EVIDENCE_READY |  |
| 32.02 | EVIDENCE_READY |  |
| 32.03 | IN_PROGRESS | legacy use + policy refusals; bridge ratio needs migration metrics |
| 32.04 | EVIDENCE_READY |  |
| 32.05 | IN_PROGRESS | no pk_core/exporter/audit health series |
| 32.06 | BLOCKED | thresholds not SLO-derived: needs an independent reviewer/approver record |
| 32.07 | EVIDENCE_READY | class labels + severity |
| 32.08 | IN_PROGRESS | no absent()/freshness alert yet |
| 32.09 | EVIDENCE_READY |  |
| 32.10 | EVIDENCE_READY |  |
| 32.11 | BLOCKED | no live alerting stack |
| 32.12 | BLOCKED | owners UNASSIGNED |
| 32.13 | EVIDENCE_READY | 1 MUST requirements R32-xx, each with evidence refs |
| 32.14 | EVIDENCE_READY | boundary: Ops as code. |
| 32.15 | EVIDENCE_READY | ceilings: n/a |
| 32.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 32.17 | EVIDENCE_READY | {} |
| 32.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 32.19 | EVIDENCE_READY | no runtime operation |
| 32.20 | EVIDENCE_READY | n/a |
| 32.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 32.22 | EVIDENCE_READY | ops/* |
| 32.23 | EVIDENCE_READY | n/a |
| 32.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 32.25 | EVIDENCE_READY | n/a |
| 32.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 32.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 32.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 32.29 | EVIDENCE_READY |  |
| 32.30 | EVIDENCE_READY |  |
| 32.31 | EVIDENCE_READY | n/a |
| 32.32 | EVIDENCE_READY |  |
| 32.33 | EVIDENCE_READY | runbook R3 |
| 32.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 32.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 32.36 | EVIDENCE_READY |  |
| 32.37 | EVIDENCE_READY |  |
| 32.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 32.39 | BLOCKED | needs independent review + owner; component blockers: Not loaded into a live Prometheus/Grafana; thresholds not SLO-approved; no data-freshness alert source |
| 32.40 | EVIDENCE_READY |  |
| 32.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 32.42 | EVIDENCE_READY |  |
| 32.43 | BLOCKED | no security review record: needs an independent reviewer |
| 32.44 | EVIDENCE_READY |  |
| 32.45 | BLOCKED | no trusted signature, no reviewer approval |
| 33.01 | IN_PROGRESS | entry conditions via alerts; severity map pending owner |
| 33.02 | EVIDENCE_READY | status command gives versions/state |
| 33.03 | EVIDENCE_READY |  |
| 33.04 | EVIDENCE_READY |  |
| 33.05 | IN_PROGRESS | config/release/lifecycle rollback; signing trust rollback not |
| 33.06 | EVIDENCE_READY |  |
| 33.07 | EVIDENCE_READY |  |
| 33.08 | BLOCKED | owners UNASSIGNED |
| 33.09 | IN_PROGRESS | no communication templates |
| 33.10 | IN_PROGRESS | drain bounded; retry stop conditions via retry_class |
| 33.11 | BLOCKED | technical drill via tests; game day needs a team |
| 33.12 | EVIDENCE_READY |  |
| 33.13 | EVIDENCE_READY | 1 MUST requirements R33-xx, each with evidence refs |
| 33.14 | EVIDENCE_READY | boundary: Ops procedure. |
| 33.15 | EVIDENCE_READY | ceilings: n/a |
| 33.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 33.17 | EVIDENCE_READY | {"env": "INV14_AUDIT_KEY_HEX"} |
| 33.18 | EVIDENCE_READY | threats: no runtime trust boundary introduced |
| 33.19 | EVIDENCE_READY | no runtime operation |
| 33.20 | EVIDENCE_READY | refuse without audit key |
| 33.21 | EVIDENCE_READY | codes: none raised (never fails a poll) |
| 33.22 | EVIDENCE_READY | tools/runbook.py |
| 33.23 | EVIDENCE_READY | n/a |
| 33.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 33.25 | EVIDENCE_READY | audit records |
| 33.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 33.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 33.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 33.29 | EVIDENCE_READY |  |
| 33.30 | EVIDENCE_READY |  |
| 33.31 | EVIDENCE_READY | n/a |
| 33.32 | EVIDENCE_READY |  |
| 33.33 | EVIDENCE_READY | runbook R0-R10 |
| 33.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 33.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 33.36 | EVIDENCE_READY |  |
| 33.37 | EVIDENCE_READY |  |
| 33.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 33.39 | BLOCKED | needs independent review + owner; component blockers: No game-day/tabletop with a real on-call team; paging targets UNASSIGNED |
| 33.40 | EVIDENCE_READY |  |
| 33.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 33.42 | EVIDENCE_READY |  |
| 33.43 | BLOCKED | no security review record: needs an independent reviewer |
| 33.44 | EVIDENCE_READY |  |
| 33.45 | BLOCKED | no trusted signature, no reviewer approval |
| 34.01 | IN_PROGRESS | id/consumer/owner/approver/dates/commitment; risk/requirement fields not |
| 34.02 | IN_PROGRESS | scoped to one component_id; env/tenant scope not |
| 34.03 | BLOCKED | compensating-control evidence needs owners |
| 34.04 | EVIDENCE_READY | <= 180 days |
| 34.05 | EVIDENCE_READY | approver != owner |
| 34.06 | EVIDENCE_READY |  |
| 34.07 | BLOCKED | needs scheduler/owner |
| 34.08 | BLOCKED | needs an independent reviewer/approver record |
| 34.09 | IN_PROGRESS | versioned in package |
| 34.10 | EVIDENCE_READY |  |
| 34.11 | BLOCKED | no waivers exist yet |
| 34.12 | BLOCKED | needs an independent reviewer/approver record |
| 34.13 | EVIDENCE_READY | 1 MUST requirements R34-xx, each with evidence refs |
| 34.14 | EVIDENCE_READY | boundary: Schema + enforcement; data is organisational. |
| 34.15 | EVIDENCE_READY | ceilings: 180 days. |
| 34.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 34.17 | EVIDENCE_READY | {"external_policy": "governance/WAIVERS.json"} |
| 34.18 | EVIDENCE_READY | threats: self-approved waiver |
| 34.19 | EVIDENCE_READY | no runtime operation |
| 34.20 | EVIDENCE_READY | fail closed |
| 34.21 | EVIDENCE_READY | codes: PK_GOVERNANCE_* |
| 34.22 | EVIDENCE_READY | validate_waivers, ConsumerGate |
| 34.23 | EVIDENCE_READY | static |
| 34.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 34.25 | EVIDENCE_READY | waiver_id |
| 34.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 34.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 34.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 34.29 | EVIDENCE_READY |  |
| 34.30 | EVIDENCE_READY |  |
| 34.31 | EVIDENCE_READY | basis in gate result |
| 34.32 | EVIDENCE_READY |  |
| 34.33 | EVIDENCE_READY | runbook R7 |
| 34.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 34.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 34.36 | EVIDENCE_READY |  |
| 34.37 | EVIDENCE_READY |  |
| 34.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 34.39 | BLOCKED | needs independent review + owner |
| 34.40 | EVIDENCE_READY |  |
| 34.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 34.42 | EVIDENCE_READY |  |
| 34.43 | BLOCKED | no security review record: needs an independent reviewer |
| 34.44 | EVIDENCE_READY |  |
| 34.45 | BLOCKED | no trusted signature, no reviewer approval |
| 35.01 | EVIDENCE_READY |  |
| 35.02 | EVIDENCE_READY | DEPRECATED, NEW_CONSUMERS_REFUSED, WAIVER_ONLY, REMOVED |
| 35.03 | BLOCKED | dates PROPOSED; approving authority owners UNASSIGNED |
| 35.04 | EVIDENCE_READY | registry closes |
| 35.05 | EVIDENCE_READY | support_window |
| 35.06 | BLOCKED | needs production telemetry |
| 35.07 | EVIDENCE_READY | waivers cannot pass REMOVED |
| 35.08 | IN_PROGRESS | guidance in ADR; consumer validation steps pending INV-15 |
| 35.09 | BLOCKED | owners UNASSIGNED |
| 35.10 | EVIDENCE_READY |  |
| 35.11 | BLOCKED | tombstone written at removal |
| 35.12 | BLOCKED | needs an independent reviewer/approver record |
| 35.13 | EVIDENCE_READY | 3 MUST requirements R35-xx, each with evidence refs |
| 35.14 | EVIDENCE_READY | boundary: Policy + enforcement. |
| 35.15 | EVIDENCE_READY | ceilings: n/a |
| 35.16 | EVIDENCE_READY | v4.2.0 12-test suite unchanged and passing |
| 35.17 | EVIDENCE_READY | {"external_policy": "governance/EOL_POLICY.json"} |
| 35.18 | EVIDENCE_READY | threats: silent support extension |
| 35.19 | EVIDENCE_READY | no runtime operation |
| 35.20 | EVIDENCE_READY | fail closed after REMOVED |
| 35.21 | EVIDENCE_READY | codes: PK_POLL_EOL_REMOVED, PK_POLL_REGISTRY_CLOSED |
| 35.22 | EVIDENCE_READY | eol_phase, ConsumerGate |
| 35.23 | EVIDENCE_READY | static |
| 35.24 | EVIDENCE_READY | owns no waiters/handles/buffers |
| 35.25 | EVIDENCE_READY | n/a |
| 35.26 | EVIDENCE_READY | positive/negative/boundary tests pass |
| 35.27 | EVIDENCE_READY | no defect found in this component during implementation |
| 35.28 | EVIDENCE_READY | normal and -O on the single executed cell (CPython 3.11.15 linux x86_64); other matrix cells UNTESTED |
| 35.29 | EVIDENCE_READY |  |
| 35.30 | EVIDENCE_READY |  |
| 35.31 | EVIDENCE_READY | eol_phase |
| 35.32 | EVIDENCE_READY |  |
| 35.33 | EVIDENCE_READY | runbook R7 |
| 35.34 | BLOCKED | owners UNASSIGNED; review cadence 90 d defined |
| 35.35 | EVIDENCE_READY | component tests run in verify_release (normal + -O); no assumed-pass path |
| 35.36 | EVIDENCE_READY |  |
| 35.37 | EVIDENCE_READY |  |
| 35.38 | EVIDENCE_READY | fresh venv, no site-packages, run from the built archive |
| 35.39 | BLOCKED | needs independent review + owner; component blockers: Dates are PROPOSED; no approving authority |
| 35.40 | EVIDENCE_READY |  |
| 35.41 | EVIDENCE_READY | revision = MANIFEST sha256; deterministic build via tools/build_zip.py |
| 35.42 | EVIDENCE_READY |  |
| 35.43 | BLOCKED | no security review record: needs an independent reviewer |
| 35.44 | EVIDENCE_READY |  |
| 35.45 | BLOCKED | no trusted signature, no reviewer approval |
