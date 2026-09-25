# PLN-04 Execution Plane — REPLACEMENT master specification

Status: PROPOSED (replacement, not the original)
Spec version: 1.0.0-proposed · Package version: 4.3.0 · Date: 2026-09-23

## Provenance

| Field | Value |
|---|---|
| Original artifact | `MASTER.md` referenced by PLN-04 4.1.0 README |
| Original recovered? | **No.** It is absent from the 4.1.0 and 4.2.0 archives and from the 4.2.0 missing-components checklist. It has not been reconstructed from memory. |
| Series | Post-Kubernetes Master Prompt & Workflow Series v4.0.0, group 02_Synthesis_Planes |
| Source function quoted by the checklist | "Wasm → process sandbox → unikernel → Firecracker microVM → full VM, selected according to workload needs." (PLN-04-C010, PLN-04-C011) |
| Written from | `CHECKLIST.json` (100 controls), the 4.2.0 `AUDIT_REPORT.md`, and `PLN04_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` |
| Author | chop-shop overhaul, work order PLN04-20260923-missing-components |
| Change control | Minor version for any SHALL added or tightened; major for any SHALL removed or loosened. Owner approval (ops/OWNERS.json) is required. Normative-section hash is recorded in release evidence by `tools/build_info.py` (tree digest). |

If the original `MASTER.md` is found, it supersedes this file. Diff it against the MR list below, and record every divergence in `docs/TRACEABILITY.md`.

## Normative requirements

| ID | Requirement | Controls | Implemented by |
|---|---|---|---|
| MR-001 | PLN-04 SHALL select, for every admitted workload, the weakest currently attested isolation tier that satisfies the workload's trust-class floor. | PLN-04-C001, PLN-04-C011 | `runtime.select_tier`, `plane.ExecutionPlane.admit` |
| MR-002 | PLN-04 SHALL NOT implement tier isolation itself; it SHALL drive providers through the `ExecutionProvider` contract. | PLN-04-C002, PLN-04-C021 | `providers.py` |
| MR-003 | The tier order and trust-class floors SHALL be fixed by an approved ADR. | PLN-04-C010 | `docs/ADR-0001-execution-tier-semantics.md` |
| MR-004 | No instance SHALL be recorded `active` before its provider confirms creation. | PLN-04-C015, PLN-04-C057 | `plane._admit_locked` |
| MR-005 | Every lifecycle transition SHALL follow `providers.LIFECYCLE`; illegal transitions SHALL fail with PLN04-STATE-004. | PLN-04-C015 | `providers.check_transition` |
| MR-006 | A failed start SHALL be compensated (stop → zeroize → terminated), and its reservations SHALL be released only after verified zeroization. | PLN-04-C014, PLN-04-C046 | `plane._compensate` |
| MR-007 | Loss or expiry of tier attestation SHALL make the tier ineligible and quarantine its residents. Restoring the tier SHALL NOT reactivate quarantined residents. | PLN-04-C048, PLN-04-C059 | `plane.fail_tier`, `plane.refresh_attestation` |
| MR-008 | Attestation evidence SHALL be signed, bound to node, tier and a single-use nonce, fresh within policy, and matched to reference measurements. | PLN-04-C044, PLN-04-C050 | `security.AttestationVerifier` |
| MR-009 | In the production profile, callers SHALL be authenticated and authorised by capability, and tenant-bound actors SHALL act only on their own tenant. | PLN-04-C023, PLN-04-C024, PLN-04-C042 | `security.Authenticator`, `security.authorize` |
| MR-010 | In the production profile, trust class SHALL come from a signed classification bound to the workload and tenant. | PLN-04-C041, PLN-04-C046 | `security.ClassificationVerifier` |
| MR-011 | In the production profile, executable artifacts SHALL be allowlisted by digest with signed provenance and approved per tier. | PLN-04-C045 | `security.ArtifactPolicy` |
| MR-012 | Resident, reservation, lease and idempotency state SHALL be durable and compare-and-swap versioned, and SHALL be reconciled with providers at startup, never resumed from memory. | PLN-04-C004, PLN-04-C057, PLN-04-C095 | `store.FileStateStore`, `plane.recover` |
| MR-013 | Execution ownership SHALL be fenced by globally monotonic epochs. Providers SHALL reject stale epochs. | PLN-04-C058 | `store.LeaseManager`, `providers._fence` |
| MR-014 | Only codes marked retryable SHALL be retried, with bounded full-jitter backoff. Failing providers SHALL be circuit-broken. | PLN-04-C053, PLN-04-C054 | `resilience.py` |
| MR-015 | Admission SHALL be bounded: node and tenant ceilings, weighted fair share with a reserved headroom, and a bounded per-tenant-fair queue that refuses rather than buffers. | PLN-04-C017, PLN-04-C028, PLN-04-C067 | `resilience.FairShare`, `resilience.AdmissionGate` |
| MR-016 | Configuration SHALL be declarative, schema-validated, and fail closed. Each configuration SHALL be identified by a content-hash generation. | PLN-04-C033, PLN-04-C034, PLN-04-C035, PLN-04-C036 | `policy.PlaneConfig` |
| MR-017 | Tenant residency rules SHALL be enforced against the node's authoritative site. | PLN-04-C006, PLN-04-C019 | `policy.check_residency` |
| MR-018 | Co-residency SHALL follow per-trust-class `shared`, `tenant-exclusive` or `dedicated` placement, in both directions. | PLN-04-C046, PLN-04-C050 | `policy.check_coresidency` |
| MR-019 | Every externally visible failure SHALL carry a stable `PLN04-*` code with defined retryability and transport mapping. | PLN-04-C026 | `errors.py`, `docs/ERRORS.md` |
| MR-020 | Every external contract SHALL be a versioned JSON Schema enforced at runtime, with bounded size and depth. | PLN-04-C022, PLN-04-C028 | `validation.py`, `schemas/` |
| MR-021 | Security-sensitive operations SHALL be written to a durable hash chain that can be anchored externally. An operation whose audit write fails SHALL NOT proceed. | PLN-04-C049 | `observability.DurableAuditSink` |
| MR-022 | PLN-04 SHALL expose health, readiness, metrics, structured logs, trace context and an explain view. Tenant identifiers SHALL be privacy-controlled. | PLN-04-C071, PLN-04-C072, PLN-04-C073, PLN-04-C074, PLN-04-C077, PLN-04-C079 | `observability.py`, `transport.py`, `plane.explain` |
| MR-023 | Admission latency SHALL be measured and evaluated against approved SLOs. | PLN-04-C062, PLN-04-C091 | `observability.LatencySlo`, `ops/SLO.json` |
| MR-024 | Operators SHALL be able to stage rollout (disabled, canary, full), emergency-disable, auto-roll-back and drain. Teardown SHALL remain possible while disabled. | PLN-04-C038, PLN-04-C059, PLN-04-C092 | `policy.RolloutControl`, `plane.auto_rollback`, `plane.drain` |
| MR-025 | Orphaned, failed or unknown provider instances SHALL be reaped. Unverified zeroization SHALL withhold resources from reuse. | PLN-04-C051, PLN-04-C052 | `plane.reap` |
| MR-026 | Lifecycle events SHALL be exported at least once, with stable event IDs and a bounded outbox. | PLN-04-C021, PLN-04-C078 | `observability.EventExporter` |
| MR-027 | A release SHALL be certified only by the fail-closed gate, with machine-readable evidence tied to the tree digest. | PLN-04-C090, PLN-04-C100 | `tools/release_gate.py` |
| MR-028 | State SHALL support verified backup, restore and forward migration. | PLN-04-C095 | `store.FileStateStore.backup/restore`, `store.migrate` |
| MR-029 | Secrets SHALL NOT appear in configuration, logs, audit or errors. | PLN-04-C039, PLN-04-C075 | `security.redact`, `errors._SAFE_DETAIL_KEYS` |
| MR-030 | Performance SHALL be baselined and regression-gated, and memory, queues and concurrency SHALL be bounded under soak. | PLN-04-C061, PLN-04-C067, PLN-04-C070 | `tools/perf.py` |

## Non-normative guidance

- Tier order: see ADR-0001. The source function lists Wasm before the process sandbox. PLN-04 4.2.0/4.3.0 orders `process` before `wasm`. This divergence is the first decision the ADR asks the owner to make.
- Edge contexts (PLN-04-C012, PLN-04-C018): a disconnected node keeps its local store and fails closed on attestation expiry. It never admits on stale trust.
