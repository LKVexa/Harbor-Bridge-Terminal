# GAP-09 v5.1.0 missing-components overlay — status

**Candidate:** `gap09_unified_observability` v5.0.0 hardened (22 files, left byte-identical — `tests/test_overlay_integrity.py`).
**Workflow applied:** *Professional Missing-Components Engineering Checklist* — 60 components × 24 checks = 1,440 checks (copied verbatim into `checklist/`).
**Production certification:** **NOT CERTIFIED.** The engine gives no PASS: every PASS needs a named owner and an independent human reviewer, and there are none.

## How to verify

```text
python -B gap09_unified_observability/components/run_all.py     (Windows: components\VERIFY_COMPONENTS.cmd)
```

Exit 0 = all stages pass; **3 = INCOMPLETE** (the expected result today, because the doc check still fails on MASTER.md); 1 = a failure.

## Result (run 2026-09-22, CPython 3.11.15, Linux)

| Measure | Value |
|---|---|
| Overlay tests | 90 pass (84 in the engine run + 6 engine falsifiers), 0 skipped, 0 failed |
| Original v5.0.0 suite | 34 run, 31 pass, 3 skipped (`pk_core` absent — unchanged) |
| Declared test lanes that ran | jsonschema 4.26.0, Node.js 22.22.2, OpenSSL |
| Checks | **558 VERIFYING · 600 IN_PROGRESS · 282 BLOCKED · 0 PASS · 0 WAIVED · 0 NOT_STARTED** |
| Doc check (component 60) | FAIL — 4 v5.0.0 docs still reference a MASTER.md that isn't in the archive |
| Ed25519 verify p50 | ~26.5 ms (pure Python; waiver W-002) |
| Verified ingest, 1 sample + fsync, p50 | ~28.3 ms |

How to read `VERIFYING`: the check's component has bound code, every bound test class passed, the
check text shares at least 3 subject stems with that code and those tests, and nothing in the check
names an activity this pass didn't do (game-day, sign-off, CI, upgrade…). The stem test is a lower
bound. It can only turn a VERIFYING down, never produce one. It is still a machine claim, and a
reviewer should expect to downgrade some. The rule behind every one of the 1,440 decisions is in
`evidence/CHECKLIST_STATUS.json`, and the records are hash-chained in `evidence/GATE_LEDGER.jsonl` (head in `.head`).

## Per component

| # | Component | VERIFYING | IN_PROGRESS | BLOCKED | Blocking dependency |
|---|---|---|---|---|---|
| 01 | Real GAP-06 attestation adapter | 13 | 6 | 5 | real GAP-06 attestation service (TPM/TEE evidence) |
| 02 | Real GAP-07 signature/provenance adapter | 14 | 3 | 7 | real GAP-07 signature/provenance service and PKI |
| 03 | Durable replay protection | 18 | 3 | 3 | — |
| 04 | Key/certificate lifecycle | 10 | 11 | 3 | real GAP-07 signature/provenance service and PKI |
| 05 | mTLS/authenticated transport | 12 | 4 | 8 | real GAP-07 signature/provenance service and PKI |
| 06 | Secret/KMS and at-rest encryption integration | 6 | 9 | 9 | KMS / AEAD provider |
| 07 | Central authorization-policy integration | 6 | 14 | 4 | authoritative policy service |
| 08 | Authenticated query-principal binding | 14 | 7 | 3 | production query gateway / IdP |
| 09 | Time authority / clock-skew policy | 8 | 12 | 4 | trusted time source (NTS/PTP/roughtime) |
| 10 | Canonical cross-language signing profile | 17 | 5 | 2 | — |
| 11 | Durable local write-ahead buffer | 20 | 0 | 4 | — |
| 12 | Admission control and backpressure | 16 | 6 | 2 | — |
| 13 | Per-tenant cardinality quotas | 13 | 9 | 2 | — |
| 14 | Tamper-evident security audit ledger | 14 | 8 | 2 | — |
| 15 | Production configuration subsystem | 13 | 9 | 2 | — |
| 16 | pk_core dependency/package | 0 | 0 | 24 | pk_core package |
| 17 | Actual production gate evidence | 0 | 0 | 24 | pk_core package; sibling components GAP-01/06/07/08 and PLN-05 |
| 18 | Evidence-gate hardening | 0 | 22 | 2 | pk_core package |
| 19 | Network service / RPC handlers | 13 | 9 | 2 | — |
| 20 | Multi-signal event model | 14 | 8 | 2 | — |
| 21 | Trace-context propagation | 17 | 5 | 2 | Wasm runtime with component telemetry hooks; microVM hypervisor (e.g. Firecracker) |
| 22 | Causal-context graph | 11 | 11 | 2 | — |
| 23 | Signal catalogue service/registry | 15 | 7 | 2 | — |
| 24 | Wasm instrumentation/collector adapter | 10 | 6 | 8 | Wasm runtime with component telemetry hooks |
| 25 | microVM/hypervisor adapter | 11 | 6 | 7 | microVM hypervisor (e.g. Firecracker) |
| 26 | Host/node collectors | 12 | 10 | 2 | — |
| 27 | Network telemetry adapters | 12 | 7 | 5 | live network flow/DNS source (eBPF/IPFIX) |
| 28 | Log ingestion pipeline | 9 | 13 | 2 | — |
| 29 | Metrics pipeline | 8 | 14 | 2 | — |
| 30 | Trace pipeline | 10 | 12 | 2 | — |
| 31 | Continuous profiling pipeline | 8 | 14 | 2 | — |
| 32 | Export/sink adapters | 8 | 9 | 7 | external observability backend / OTLP collector |
| 33 | Query service beyond latest value | 11 | 11 | 2 | — |
| 34 | Retention/sampling/privacy policy engine | 10 | 12 | 2 | — |
| 35 | High-cardinality safety controls | 17 | 5 | 2 | — |
| 36 | Health/readiness/dependency endpoint | 16 | 6 | 2 | — |
| 37 | Decision/explain records | 14 | 8 | 2 | — |
| 38 | Persistent state backend or reconstruction contract | 11 | 10 | 3 | — |
| 39 | Replication/failover model | 1 | 11 | 12 | multi-node deployment for replication/failover |
| 40 | Partition/reconnect protocol | 9 | 13 | 2 | — |
| 41 | Quarantine/freeze controls | 11 | 11 | 2 | — |
| 42 | Dependency circuit breakers | 18 | 4 | 2 | — |
| 43 | Backup/restore/migration procedures | 6 | 13 | 5 | — |
| 44 | Adjacent-layer integration tests | 0 | 0 | 24 | sibling components GAP-01/06/07/08 and PLN-05 |
| 45 | Contract-schema conformance tests | 10 | 12 | 2 | — |
| 46 | Fuzz/property tests | 6 | 16 | 2 | — |
| 47 | Concurrency/race stress tests | 9 | 13 | 2 | — |
| 48 | Fault-injection tests | 10 | 12 | 2 | — |
| 49 | Soak/burst/fleet-scale tests | 2 | 17 | 5 | fleet-scale environment |
| 50 | Performance baselines | 2 | 20 | 2 | — |
| 51 | Edge power/thermal measurements | 0 | 0 | 24 | representative edge hardware with power/thermal instrumentation |
| 52 | Release regression gates | 3 | 19 | 2 | named owner and independent reviewer |
| 53 | Compatibility matrix | 2 | 20 | 2 | — |
| 54 | Packaging/dependency lock/SBOM | 4 | 18 | 2 | — |
| 55 | Vulnerability/EOL policy | 2 | 20 | 2 | advisory feed selection |
| 56 | Owner/escalation and incident runbooks | 9 | 12 | 3 | named owner and independent reviewer |
| 57 | Architecture decision record | 4 | 18 | 2 | named owner and independent reviewer |
| 58 | Exception/waiver/debt registry | 2 | 20 | 2 | named owner and independent reviewer |
| 59 | Dashboards and operational views | 10 | 11 | 3 | external observability backend / OTLP collector |
| 60 | MASTER.md | 7 | 9 | 8 | authoritative MASTER.md source |
Every component's checks 23 (owner/reviewer) and 24 (closure) are BLOCKED. That is 120 of the 282 BLOCKED checks.

## Defects this pass found in its own work (all fixed; each has a regression test)

- **F-01:** the Node.js reporter test found that Python and ECMAScript disagree on integers above 2^53 (`str(2**60)` isn't ES text). Fixed: CSP/1 renders them as the binary64 value ES sees.
- **F-02:** the schema-conformance lane found that the first `/v1/submit` wire shape (top-level `key_id`) broke `PK_SIGNAL_SUBMISSION/2`. Fixed: `key_id` and `profile` travel inside `attestation`, and the server accepts only the schema shape.
- **F-04:** the seeded round-trip property test found that canonical output could be refused when re-canonicalised (a large integer text that is the ES rendering of a double). Fixed.
- The profile/log secret detector missed `token=…` assignments (found by the profiling privacy test). Fixed.
- The audit-ledger loader raised a raw `JSONDecodeError` on a corrupt line instead of `Corrupted`. Fixed.
- The store's verifier slot was swapped per call without a lock, so concurrent submits could race. Fixed with `_commit_lock`, and the 8-thread exactly-once test covers it.
- The checklist engine's first classification gave 1,022 VERIFYING. Adding the subject-stem lower bound, the not-performed-activity rule and blocker keywords brought it down to 558.

## Findings against the v5.0.0 package (not fixed here — the owner decides)

- **F-03:** `PK_SIGNAL_CATALOGUE/1` has no kind for `event` records (W-001).
- MASTER.md is referenced by README, CHANGELOG, AUDIT_REPORT and MISSING_COMPONENTS but isn't in the archive (W-005, component 60).
- Legacy `submit(... signed=True)` is still in `runtime.py`. It's disabled by default, and the production config validator refuses `allow_legacy_trust=True`.

## Honest limits

- Trust roots for attestation, policy and query tokens are **test fixtures**. The mechanisms are real; the roots aren't.
- There is no AEAD in the stdlib. The replay log, WAL and audit ledger are plaintext files that hold identifiers, never secrets (W-003). `EnvelopeGuard` refuses sensitive persistence without a KMS provider.
- Ed25519 here is correct against RFC 8032 vectors and Node's native implementation, but it isn't constant-time and it's slow.
- Burst testing ran at local scale only (2,000 submissions). Fleet, soak, power/thermal and multi-node replication are BLOCKED.
- `tools/regression_gate.py` thresholds are proposals (W-004). All five waivers are PROPOSED with owner UNASSIGNED.

## Layout

`components/` → `ed25519.py canonical.py keys.py attestation.py audit_ledger.py durable.py controls.py config.py auth.py signals.py policy.py pipelines.py adapters.py query_service.py export.py ingest.py replication.py server.py errors.py`,
`reporters/node_reporter.mjs`, `vectors/`, `tests/` (9 modules), `tools/` (bench, regression_gate, sbom, doc_check, dashboard, runbooks),
`checklist/` (engine, bindings, the checklist), `docs/` (ADR-001, TRUST_BOUNDARY, RUNBOOKS, COMPATIBILITY, VULN_EOL_POLICY, WAIVERS.json),
`evidence/` (CHECKLIST_STATUS.json, EVIDENCE_INDEX.json, GATE_LEDGER.jsonl(+.head), perf_baseline.json, SBOM.cdx.json).
