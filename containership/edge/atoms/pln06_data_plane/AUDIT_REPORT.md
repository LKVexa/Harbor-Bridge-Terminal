# PLN-06 Data plane — implementation report for the v4.2.0 missing-components checklist

**Input version:** 4.2.0 (`pln06_data_plane_v4.2.0_hardened.zip`)  
**Output version:** 4.3.0  
**Workflow executed:** `PLN06_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v4.2.0.md` — 64 work packages, dependency waves 0–7  
**Date:** 2026-09-23  
**Prior report:** `docs/history/AUDIT_REPORT_v4.2.0.md`

## Executive result

| Measure | 4.2.0 | 4.3.0 |
|---|---|---|
| Traceability (100 items) | 21 Implemented / 38 Partial / 41 Missing | **72 Implemented / 28 Partial / 0 Missing** |
| Executing tests | 13 (+3 pk_core skips) | **89 passing** (+3 pk_core skips tied to waiver W-008), normal and `python -O` |
| Static analysis | none configured | ruff (incl. flake8-bandit S rules, complexity) **clean**; mypy **clean** |
| Runtime third-party dependencies | 0 | 0 |
| Work packages | — | 36 closed in-repo, 19 implemented with a waived residual, 9 blocked on owner/external input |
| Production gate | not present | **implemented; FAILS closed** (by design) |

Every Partial item carries a waiver in `WAIVERS.json` with owner, risk, compensating control, remediation and expiry. No item is marked Implemented on the strength of design intent, reference fixtures, or unsigned approvals.

## Why the production gate still fails

`tools/release_gate.py` fails closed on items that cannot honestly be closed from inside the repository:

1. **Ownership** — technical lead, security contact, SRE/on-call, backup owner are vacant; service/repository owner is *proposed* (David Paul Russell) pending confirmation; CODEOWNERS contains `@OWNER-TBD-*` placeholders (W-001).
2. **ADR approval** — ADR-0001/0002 are Proposed; no approver signatures (W-002).
3. **License** — no LICENSE chosen; this was deliberately not assumed (W-010).
4. **Waiver approvals** — all 19 waivers (plus 3 technical-debt and 1 deprecation entries) are `proposed`; the gate requires an approver other than the owner.
5. **Ownership review** — never performed (`last_reviewed: null`).
6. **Dossier signature** — the evidence dossier is SHA-256 checksummed but not HMAC-signed, because no signing key (`PK06_EVIDENCE_KEY`) was provided; a key was not invented for this run.

The other 13 checks pass: traceability consistent with no Missing items, every Partial waived, no expired or self-approved waivers, SHA256SUMS verified, no runtime asserts, tests green in both modes, ruff/mypy clean, perf gate PASS, SBOM recorded, dossier bound to the wheel SHA-256 (see `evidence/gate.json`).

## Defects found and fixed during this pass

1. `_StructuredError` did not inherit from `Exception`, so generic `except _StructuredError` handlers were impossible (`TypeError` at catch time). Fixed; existing subclass relationships unchanged.
2. Capacity leak in the governed path: when no adapter could be selected (e.g. transport quarantined), the transfer kept its reservation and stayed `admitted`. Found by `test_operator_controls` (drain never completed). Now journaled `failed`, audited, and released.
3. The vsock control route was unreachable because `same_host_vm` has locality floor 1 (never inline). Introduced the explicit inline-only `vm_control` locality; bulk sizes on that locality have no route, which is the structural INV-36 proof.
4. Connect-time `ConnectionRefusedError` escaped the network adapter unstructured. Now `PK_TRANSPORT_FAILED` (retryable) / `PK_DEADLINE_EXCEEDED`.

## Measured findings

- **Capacity (TD-001):** single-thread admission ≈ 89k/s; 2–32 threads ≈ 24–29k/s. The single `RLock` plus the GIL make admission contention-bound; the capacity model reports saturation at concurrency 1 and recommends sharding planes per node/tenant group.
- Runtime admission p50 ≈ 6 µs / p99 ≈ 18 µs; governed inline submit (auth + label + audit fsync + journal fsync) p99 ≈ 2.7 ms; shared-memory ≈ 222 MB/s; loopback `pk06-rpc` ≈ 203 MB/s (sandbox, x86_64, Python 3.11). Baseline: `bench/baseline.json`.
- Power/thermal counters are not exposed in the build sandbox (W-013).

## Work-package status (all 64)

| # | Work package | Status | Delivered | Residual / waiver |
|---:|---|---|---|---|
| 1 | Accountable ownership and escalation | Blocked on owner/external | OWNERSHIP.json, docs/OWNERSHIP.md, CODEOWNERS (2-maintainer paths), RACI, fail-closed gate check | W-001 names/pager/catalog |
| 2 | Approved architecture decision | Blocked on owner/external | ADR-0002 selects/pins technologies, rejected alternatives, supersession rules | W-002 approval signatures |
| 3 | Concrete source-architecture transport adapters | Implemented; residual waived | TransportAdapter SPI; in-process CM-style, shared-memory, vsock-control, pk06-rpc network (mTLS), RDMA probe; select_adapter negotiation | W-003 wRPC wire, W-004 RDMA, W-018 wasmtime |
| 4 | Deployment-context requirements | Closed in-repo | config.DEPLOYMENT_CONTEXTS + REQUIREMENTS §2 offline semantics | — |
| 5 | Complete non-functional requirement set | Implemented; residual waived | REQUIREMENTS §7 NFR/SLO/error budget with measured baseline | W-002 approval of thresholds |
| 6 | Complete outcome/degraded-state semantics | Closed in-repo | lifecycle.OUTCOMES, DEGRADED_MODES | — |
| 7 | Durable/distributed lifecycle state machine | Implemented; residual waived | WAL journal, replay, fencing epoch lease, restart reconciliation | TD-003 fleet lease |
| 8 | Formal version/compatibility policy | Closed in-repo | docs/VERSIONING.md, schema $id checks, version negotiation | — |
| 9 | Fairness/scheduling policy beyond quotas | Closed in-repo | FairScheduler DRR with bounds and starvation proof | — |
| 10 | Complete constraint-precedence model | Closed in-repo | precedence.py wired into submit | — |
| 11 | Boundary authentication | Closed in-repo | Authenticator (credentials, audience, expiry, replay), mutual peer auth, mTLS | — |
| 12 | Authorization/capability enforcement | Closed in-repo | Capability model, deny-by-default, tenant scoping, per-tier transport caps | — |
| 13 | Timeout and bounded retry subsystem | Closed in-repo | RetryPolicy/call_with_retry, CircuitBreaker, deadlines, cancellation | — |
| 14 | Concrete adjacent-layer integration suite | Implemented; residual waived | Adjacent-layer integration suite on reference fixtures | W-005/6/7 |
| 15 | Immutable artifact/release packaging model | Implemented; residual waived | pyproject package, mutable-state separation, SHA256SUMS, evidence binding | W-017 Sigstore |
| 16 | Declarative environment configuration | Closed in-repo | config.py + config/base.json + overlays + pk_config_v1 schema | — |
| 17 | Durable configuration history and rollback controller | Closed in-repo | ConfigController history/canary/rollback/emergency-disable | — |
| 18 | Full reviewed threat model | Blocked on owner/external | docs/THREAT_MODEL.md STRIDE matrix mapped to tests | independent review (W-002) |
| 19 | Enforced ambient-authority sandboxing | Implemented; residual waived | AuthorityGuard + per-adapter Grant | W-011 OS sandbox |
| 20 | Signed classification/provenance integration | Closed in-repo | LabelAuthority signed, digest/tenant-bound labels; trust-root rotation; outage fail-closed | — |
| 21 | End-to-end payload integrity implementation | Closed in-repo | integrity.py manifests, receiver verification, quarantine | — |
| 22 | Strong tenant/workload isolation | Implemented; residual waived | tenant-scoped auth, quotas, namespaced shm, cross-tenant refusal | W-011 process isolation |
| 23 | Encryption and managed key lifecycle | Implemented; residual waived | KeyRing rotate/verify-only/revoke/expiry/outage; mTLS in transit | W-012 KMS/HSM, at-rest |
| 24 | Tamper-evident security audit ledger | Closed in-repo | AuditLedger hash chain + MAC + fsync, verify on load | — |
| 25 | Full failure model and stall detection | Closed in-repo | FAILURE_MODEL catalog, StallDetector, reap_stalled | — |
| 26 | Residency-safe failover controller | Closed in-repo | FailoverController residency/isolation-safe, wired into submit | — |
| 27 | Quarantine/freeze/disable controls | Closed in-repo | freeze/quarantine/drain/emergency_disable, audited | — |
| 28 | Fault-injection recovery suite | Closed in-repo | FaultInjector + injected-failure recovery tests | — |
| 29 | Performance baseline harness | Closed in-repo | bench/perf.py + bench/baseline.json | — |
| 30 | Load/scale/recovery performance suite | Implemented; residual waived | burst/overload/concurrency sweep | W-015 multi-node |
| 31 | Data-path efficiency profiling | Implemented; residual waived | efficiency_profile per adapter | W-004 RDMA |
| 32 | Edge power/thermal evidence | Blocked on owner/external | RAPL/thermal collection in harness | W-013 hardware |
| 33 | Capacity model and performance release gate | Closed in-repo | USL capacity model + perf gate in CI | TD-001 lock contention finding |
| 34 | Dependency-aware health | Closed in-repo | health v2 with dependency status | — |
| 35 | Full metrics/export stack | Closed in-repo | MetricsRegistry + Prometheus exporter + resource metrics | — |
| 36 | Structured logging | Closed in-repo | StructuredLogger PK_LOG/1 | — |
| 37 | Distributed tracing | Closed in-repo | W3C trace-context propagation | — |
| 38 | Safe high-cardinality diagnostics | Closed in-repo | redacted explain view, cardinality cap | — |
| 39 | Release lineage/infrastructure graph correlation | Implemented; residual waived | lineage block on health/explain | W-016 live infra graph |
| 40 | Telemetry governance | Closed in-repo | TELEMETRY_POLICY + doc | — |
| 41 | Dashboards and alerting | Implemented; residual waived | alert rules (6 classes) + dashboard, validated against emitted series | W-016 deployment |
| 42 | Exhaustive public-interface contract tests | Closed in-repo | schema validation of all emitted objects, mutation tests, error-code uniqueness | — |
| 43 | Platform/protocol compatibility test matrix | Implemented; residual waived | CI matrix py3.10-3.13 x86_64/arm64 defined | W-014 execution |
| 44 | Fuzz/property-based testing | Closed in-repo | seeded fuzz of 6 input surfaces incl. frame parser | — |
| 45 | Benchmark/soak/burst/fleet tests | Implemented; residual waived | burst + bounded-state soak (configurable duration) | W-015 fleet/long soak |
| 46 | Disaster/partition/reconnect testing | Closed in-repo | partition failover, crash restart, stale policy, replay, backup/restore tests | — |
| 47 | Machine-readable production acceptance evidence | Blocked on owner/external | evidence.py dossier, release_gate.py, run_tests.py (no unexpected skips) | W-008 pk_core; gate fails on governance |
| 48 | Vulnerability/patch/EOL policy | Closed in-repo | docs/VULNERABILITY_POLICY.md | — |
| 49 | Durable-state backup/restore/reconstruction | Closed in-repo | journal backup/restore with checksum; reconstruction procedure | — |
| 50 | Production-complete runbooks | Closed in-repo | docs/RUNBOOKS.md day-0/1/2, dependency outages, incidents | — |
| 51 | Recurring control reviews | Blocked on owner/external | docs/REVIEWS.md cadence + template + staleness gate | first reviews not yet performed |
| 52 | Exception/waiver/technical-debt registry | Closed in-repo | WAIVERS.json registry + gate enforcement | — |
| 53 | `pk_core` certification framework availability | Blocked on owner/external | allowed-skip mapped to waiver; standalone gate substitute | W-008 |
| 54 | GAP-13 policy engine integration | Implemented; residual waived | PolicyClient: signed, versioned, anti-downgrade, max-age fail-closed | W-005 real GAP-13 |
| 55 | GAP-14 data-gravity manager integration | Implemented; residual waived | verified_locality: signed, request-bound, advisory only | W-006 real GAP-14 |
| 56 | PLN-03 distributed runtime integration | Implemented; residual waived | hand-off with bounded retry and failure propagation | W-007 real PLN-03 |
| 57 | INV-37 bulk data-plane integration | Implemented; residual waived | bulk network/shm adapters with digest generation/verification, chunking, reassembly, quarantine | W-003/W-004 |
| 58 | INV-36 control-transport isolation proof | Closed in-repo | vm_control locality; structural + runtime proof bulk never routes to vsock | — |
| 59 | Missing original `MASTER.md` source artifact | Blocked on owner/external | README claim removed; not synthesized | W-009 restore from source |
| 60 | Python distribution/build metadata | Closed in-repo | pyproject.toml (stdlib-only runtime, package data, py>=3.10) | — |
| 61 | CI pipeline | Closed in-repo | .github/workflows/ci.yml (lint, types, tests x2 modes, matrix, security, perf gate, release gate) | — |
| 62 | SBOM/dependency provenance/vulnerability scanning | Implemented; residual waived | tools/sbom.py CycloneDX 1.5; zero runtime deps | W-019 scanner, W-017 signing |
| 63 | License file | Blocked on owner/external | license check in gate; package marked private | W-010 owner selects license |
| 64 | Static analysis/type/lint configuration | Closed in-repo | ruff (incl. S security rules, C90), mypy strict-ish on core, bandit config; all clean | — |

## Verification performed

- `tools/run_tests.py`: 92 run, 89 pass, 3 skips (pk_core, W-008), 0 unexpected skips — normal and optimized mode.
- mTLS test with throwaway openssl certificates (fails, not skips, if openssl is missing).
- Seeded fuzz at 400 iterations/surface in CI mode and 6,000 iterations (seed 7) during this pass — no unstructured errors.
- `ruff check .` clean; `mypy` clean on 20 source files.
- Perf gate PASS against the retained baseline.
- Evidence dossier and gate result: `evidence/dossier.json`, `evidence/gate.json` (dossier SHA-256 recorded; unsigned because no `PK06_EVIDENCE_KEY` was provided).

## What the owner needs to do to reach production exit

1. Fill `OWNERSHIP.json` and `.github/CODEOWNERS` with real people/teams; register the service; record the first ownership review.
2. Choose a license and add `LICENSE`.
3. Review and approve ADR-0001/0002 and the NFR thresholds; have an independent security review of `docs/THREAT_MODEL.md`.
4. Approve (or reject and schedule) each waiver in `WAIVERS.json`.
5. Supply or pin `pk_core`, then bind the real GAP-13/GAP-14/PLN-03 endpoints in a staging suite.
6. Run the CI matrix, nightly soak/fuzz, and set `PK06_EVIDENCE_KEY` so the dossier is signed.
