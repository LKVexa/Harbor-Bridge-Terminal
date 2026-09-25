# PLN-03 4.3.0 — remediation report

Workflow applied: `PLN03_v4.2.0_MISSING_COMPONENT_REMEDIATION_CHECKLIST.md` (56 findings) to candidate `pln03_distributed_runtime_plane` 4.2.0.

## Outcome
| Status | Count | Meaning |
|---|---|---|
| IMPLEMENTED | 33 | code/artifact + linked automated tests in this archive |
| PARTIAL | 11 | in-archive part done; named remainder lives outside the archive |
| PENDING_APPROVAL | 6 | artifact written; needs a named human approval |
| BLOCKED | 6 | needs an owner decision or external input |

No finding is declared **complete**: the checklist's completion semantics require reviewer records, a resolved owner, and a release-evidence link that only the owner can supply. `audit_repository.py` reports `status: PASS` (structure) and `release_ready: false` with 27 named blockers.

## Evidence
- Gates: all passed (unit_contract_fault_governance, optimised_mode, structural_audit, bench_gate, sbom_check); source tree sha256 `95cd9bdfa966392ecc1396bb8d74e67419094a9ae5bb01c79c2e5955c5ed3bd1`; bundle **UNSEALED** (set `PK_EVIDENCE_KEY`).
- Latency (this sandbox, 20k iterations): core get p99 1.41 µs; governed get p99 150.51 µs; wire get p99 186.21 µs — far inside the 10 ms SLO. Governed-path overhead is ~65.3× the bare core (token HMAC + audit hashing dominate).

## Defects found while remediating
1. Rate-limit token burned by requests the concurrency quota rejected (fairness bug) — fixed.
2. Wire handler returned 500/PK_RUNTIME_ERROR for a non-string `interface` (fuzzer) — fixed.
3. Version hard-coded in `test_runtime.py` — fixed.

## What the owner must do to close the rest
1. Fill `OWNERS.yaml` principals from the real directory/on-call system; replace `@UNASSIGNED-*` in CODEOWNERS.
2. Approve or amend ADR-0001 (runtime tech) and ADR-0002 (actor/workflow = N/A); sign off threat model, compatibility policy, operations docs.
3. Choose a LICENSE.
4. Supply `pk_core` (source + version + digest) and the original `MASTER.md`.
5. Provide the adjacent planes (PLN-02/04/06/07, INV-49) or pinned builds so integration, isolation, identity/mTLS, encryption and wasmCloud/wRPC interop can be built and tested.

## Per-finding status
| ID | Component | Status | Tests | Open remainder |
|---|---|---|---|---|
| MC-001 | Accountable production owner and escalation path | PENDING_APPROVAL | 1 | Role slots, RACI, escalation, emergency authority and owner-in-health defined; no named principals exist - owner must fill OWNERS.yaml from the identity/on-call system (audit fails release while unresolved). |
| MC-002 | Approved architecture decision record (ADR) | PENDING_APPROVAL | 1 | ADR written as Proposed; needs Architecture Board approval record. |
| MC-003 | Normative SHALL-level requirements specification | IMPLEMENTED | 1 | 19 SHALL requirements with site classes, implementation and tests. |
| MC-004 | Complete NFR specification | PARTIAL | 1 | NFRs specified; power (NFR-PWR-01) and fleet availability need target hardware/fleet telemetry. |
| MC-005 | Success/degraded/retryable/terminal outcome model | IMPLEMENTED | 1 | — |
| MC-006 | Lifecycle state machine | IMPLEMENTED | 2 | — |
| MC-007 | Compatibility and deprecation policy | PENDING_APPROVAL | 1 | Policy written and enforced in negotiation; needs owner/board approval. |
| MC-008 | Quota and fairness model | IMPLEMENTED | 1 | Per-tenant state byte quota declared but not enforced (needs adapter accounting). |
| MC-009 | Disconnected/intermittent-network semantics | IMPLEMENTED | 1 | — |
| MC-010 | Constraint precedence policy | IMPLEMENTED | 1 | — |
| MC-011 | Requirements traceability matrix | IMPLEMENTED | 1 | Generated 100-item matrix; release revision field is filled by release_evidence. |
| MC-012 | Versioned typed external schemas/WIT contracts | IMPLEMENTED | 2 | WIT not compiled with wit-bindgen here (toolchain unpinned). |
| MC-013 | Authentication and capability-token enforcement | IMPLEMENTED | 4 | — |
| MC-014 | Timeout, cancellation, retry, and backpressure contract | IMPLEMENTED | 1 | — |
| MC-015 | Serializable machine-readable error envelope | IMPLEMENTED | 4 | — |
| MC-016 | Mixed-version peer negotiation | IMPLEMENTED | 2 | — |
| MC-017 | Complete interface resource-limit specification | IMPLEMENTED | 1 | — |
| MC-018 | Reference client/server examples and conformance fixtures | IMPLEMENTED | 1 | — |
| MC-019 | Adjacent-layer integration test suite | BLOCKED | 1 | Contracts documented; PLN-02/INV-49/PLN-04/PLN-06/PLN-07 are not packaged or pinned, so no end-to-end suite can run. |
| MC-020 | Pinned implementation/specification manifest | PARTIAL | 1 | Manifest exists; wasmCloud/wRPC/Wadm/adjacent planes have no versions to pin until ADR-0001 is approved. |
| MC-021 | Declarative runtime configuration system | IMPLEMENTED | 3 | — |
| MC-022 | Configuration provenance ledger | IMPLEMENTED | 1 | — |
| MC-023 | Atomic configuration update mechanism | IMPLEMENTED | 1 | — |
| MC-024 | Configuration rollback mechanism | IMPLEMENTED | 1 | — |
| MC-025 | Secret-safe configuration/diagnostic policy enforcement | IMPLEMENTED | 2 | — |
| MC-026 | Deterministic bootstrap/install path | IMPLEMENTED | 1 | — |
| MC-027 | Full threat model artifact | PENDING_APPROVAL | 1 | Needs security_contact review record. |
| MC-028 | Ambient-authority isolation implementation | BLOCKED | 1 | Adapter quarantine added; process/Wasm/microVM isolation belongs to PLN-04 which is not in the archive. |
| MC-029 | Node/peer/artifact/provider/control-plane authentication | BLOCKED | 1 | Workload tokens verified; node/peer/control-plane identity (mTLS/SPIFFE) needs PLN-07. |
| MC-030 | Artifact signature/digest/provenance verification | PARTIAL | 1 | Digest allowlist + provenance + seal done; public-key signature (Sigstore) and SBOM attestation verification not integrated. |
| MC-031 | Complete tenant/workload isolation | PARTIAL | 1 | Data-plane tenant isolation tested on every capability; execution/memory/network/device/side-channel isolation is PLN-04. |
| MC-032 | Encryption and managed key rotation | PARTIAL | 1 | Token-key rotation/retirement implemented; transport and at-rest encryption and KMS contract need PLN-07. |
| MC-033 | Identity/attestation/policy/key/time outage behavior | IMPLEMENTED | 1 | — |
| MC-034 | Tamper-evident security audit events | IMPLEMENTED | 2 | Chain head should be shipped to PLN-07 for truncation detection. |
| MC-035 | Comprehensive adversarial security tests | PARTIAL | 3 | Fuzz/injection/spoofing/replay/exhaustion covered; escape and side-channel campaigns need PLN-04 isolation. |
| MC-036 | Failure catalog plus health/stall detectors | IMPLEMENTED | 1 | — |
| MC-037 | Bounded retry with backoff/jitter | IMPLEMENTED | 2 | — |
| MC-038 | Full admission/load-shedding/circuit-breaker layer | IMPLEMENTED | 3 | — |
| MC-039 | Residency/consistency-safe failover | IMPLEMENTED | 1 | Selection + fencing implemented; wiring to a real site inventory is PLN-04. |
| MC-040 | Degraded operation mode | IMPLEMENTED | 2 | — |
| MC-041 | Crash consistency, replay, fencing, and split-brain protection | IMPLEMENTED | 3 | — |
| MC-042 | Quarantine/freeze/disable controls | IMPLEMENTED | 2 | — |
| MC-043 | Fault-injection recovery suite | IMPLEMENTED | 2 | In-process fault injection; network-level injection needs a deployed topology. |
| MC-044 | Performance engineering and release-regression suite | PARTIAL | 1 | Reproducible latency gate done; power, fleet capacity model and target-hardware budgets open. |
| MC-045 | Operational telemetry/explainability stack | IMPLEMENTED | 2 | No HTTP server shipped; health()/exposition() are the endpoints' bodies. |
| MC-046 | Interface contract, compatibility, and fuzz testing | PARTIAL | 1 | Schema/fixture/fuzz done; cross-architecture/provider compatibility needs other hosts. |
| MC-047 | Security, scale, soak, disaster, partition/reconnect test suites | PARTIAL | 2 | Security, soak, partition/reconnect, restore suites done in-process; fleet-scale certification open. |
| MC-048 | Captured machine-readable acceptance evidence | IMPLEMENTED | 1 | Evidence built and hashed; sealing uses PK_EVIDENCE_KEY if provided, else marked UNSEALED. pk_core gate still unavailable. |
| MC-049 | Canary/staged rollout and emergency-disable implementation | PARTIAL | 1 | Criteria + emergency disable done; promotion controller belongs to deployment system. |
| MC-050 | Compatibility, vulnerability/EOL, and backup/restore governance | IMPLEMENTED | 2 | SLAs need owner approval. |
| MC-051 | Production operations/governance artifacts | PENDING_APPROVAL | 1 | Runbooks, governance, exception register written; need owner approval. |
| MC-052 | Actor and workflow service surface | PENDING_APPROVAL | 1 | Proposed as approved-NA; needs board approval and CHECKLIST wording change. |
| MC-053 | wasmCloud/wRPC/Wadm concrete integration | BLOCKED | 1 | WIT package written; no wasmCloud host/provider, wRPC transport or Wadm manifest can be built or interop-tested until versions are chosen. |
| MC-054 | MASTER.md master-prompt/workflow artifact | BLOCKED | 1 | Original MASTER.md must be supplied by the owner; it was not reconstructed to avoid fabricating a source document. |
| MC-055 | pk_core dependency declaration/vendor bundle | BLOCKED | 1 | Declared as UNPINNED; pk_core source/version/digest must be supplied. |
| MC-056 | License, SBOM, provenance, and CI policy artifacts | PARTIAL | 1 | SBOM, CI, provenance hashing done; LICENSE choice is the owner's (BLOCKED). |
