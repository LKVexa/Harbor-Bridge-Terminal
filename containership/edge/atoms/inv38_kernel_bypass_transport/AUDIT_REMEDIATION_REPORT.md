# INV-38 v4.2.0 — Missing-Component Remediation: Re-Audit Report

- **Element:** INV-38 Kernel-bypass transport  
- **Checklist:** `INV38_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (50 MISSING items)  
- **Remediation date:** 2026-09-22  
- **RTM digest:** `d962010670141dae333fd8bf0dc995b55abce8400083982c1d5449ab086147af`  
- **Release verdict:** **CONDITIONAL_GO** (RTM-driven; see `release/PK_ACCEPTANCE.json`)

## How to read this report

Statuses follow the checklist's own completion rule: a requirement is only `DONE` when a repository-owned artifact **and** reproducible in-repo evidence exist that are sufficient for the achievable scope. Reference-model behaviour is never treated as hardware/`pk_core` certification, so anything that needs real RDMA/NIC/IOMMU hardware or the external `pk_core` is `IN_PROGRESS` (artifact + model tests only) or `BLOCKED` (named external blocker). No item was converted from SKIPPED/NOT_RUN into `DONE`.

## Rollup (50 in-scope requirements)

| Status | Count | Meaning |
|---|---|---|
| DONE | 21 | Repo artifact + reproducible in-repo evidence at achievable scope |
| IN_PROGRESS | 22 | Artifact present + model tests; production evidence needs hardware/pk_core/live infra |
| BLOCKED | 7 | Plan/spec present; cannot certify from this ZIP (external blocker named) |
| **Total** | **50** | |

## Verification evidence

- Automated tests: **123/123 passed**, 0 failed (dependency-free harness; `release/attestations/test-results.json`).
- Original reference-model suites (`test_transport.py`, `test_repository.py`, `test_component.py`) still pass.
- Structure-aware fuzz/property campaign over the transport model: 10,000 iterations, no invariant break.
- RTM validated in CI (100 unique IDs, no `DONE` without evidence); repo-integrity check confirms all 148 declared artifacts exist.
- Tamper tests confirm: audit chain detects delete/insert/reorder/mutation; release-gate rejects tampered signature, expired and unapproved waivers.

## Per-requirement disposition

| ID | Dim | Pri | Status | Key artifact(s) | Note |
|---|---|---|---|---|---|
| INV-38-C009 | Architecture | P1 | IN_PROGRESS | `docs/OWNERSHIP.md`, `.github/CODEOWNERS` | Escalation-drill (C009-T07) evidence needs a live paging integration. |
| INV-38-C010 | Architecture | P1 | IN_PROGRESS | `docs/adr/ADR-0038-kernel-bypass-backend.md`, `architecture/rdma-decision-record.yaml` | Backend benchmark evidence (C010-T07) needs RDMA hardware. |
| INV-38-C012 | Requirements | P1 | IN_PROGRESS | `specs/deployment-contexts.md`, `specs/deployment-contexts.yaml` | Per-context conformance across real NIC/SR-IOV needs hardware. |
| INV-38-C014 | Requirements | P1 | DONE | `specs/outcome-semantics.md`, `schemas/outcome-v1.schema.json` | Outcome model fully realized and tested at model scope. |
| INV-38-C015 | Requirements | P1 | DONE | `specs/lifecycle-state-machine.md`, `schemas/lifecycle-v1.schema.json` | Lifecycle state machine + illegal-transition tests pass. |
| INV-38-C019 | Requirements | P1 | DONE | `policy/constraint-precedence.md`, `policy/constraint-precedence.yaml` | Precedence lattice + decision-table tests pass. |
| INV-38-C020 | Requirements | P1 | DONE | `traceability/INV38_RTM.csv`, `traceability/INV38_RTM.json` | RTM generated from canonical data + CI validator. |
| INV-38-C022 | Interfaces | P0 | IN_PROGRESS | `schemas/pk_bypass_mr_v1.schema.json`, `schemas/pk_bypass_post_v1.schema.json` | Multi-language binding generation (C022-T07) needs a real IDL toolchain. |
| INV-38-C023 | Interfaces | P0 | IN_PROGRESS | `security/authentication.md`, `security/trust-roots.yaml` | Real credential/trust-root integration needs identity service. |
| INV-38-C024 | Interfaces | P0 | IN_PROGRESS | `security/authorization.md`, `security/capabilities.yaml` | OS/device-layer least privilege (VF/IOMMU) needs hardware. |
| INV-38-C027 | Interfaces | P1 | IN_PROGRESS | `compatibility/protocol-negotiation.md`, `compatibility/version-policy.yaml` | Real-backend adapter transcripts needed for full matrix. |
| INV-38-C031 | Implementation | P0 | BLOCKED | `platform/rdma-stack.lock.yaml`, `platform/hardware-qualification.yaml` | Hardware/firmware/driver qualification requires physical RDMA NICs + IOMMU. |
| INV-38-C032 | Implementation | P1 | DONE | `architecture/artifact-config-state-boundary.md`, `config/layout.schema.json` | Boundary documented + layout schema + drift check tested. |
| INV-38-C036 | Implementation | P1 | DONE | `config/provenance.schema.json`, `config/history/README.md` | Provenance schema + redaction + history tested. |
| INV-38-C037 | Implementation | P1 | DONE | `config/transaction-protocol.md`, `config/transaction.schema.json` | Prepare/validate/stage/commit txn engine + fault tests. |
| INV-38-C042 | Security, | P0 | IN_PROGRESS | `security/least-privilege.md`, `security/privilege-matrix.yaml` | Runtime privilege drop enforcement needs a real OS deployment. |
| INV-38-C043 | Security, | P0 | IN_PROGRESS | `security/ambient-authority-inventory.yaml`, `security/sandbox-profile.json` | Sandbox-escape tests need a real sandboxed host. |
| INV-38-C044 | Security, | P0 | IN_PROGRESS | `security/trust-bootstrap.md`, `security/peer-auth-policy.yaml` | Peer/provider mutual auth needs live identities/attestation. |
| INV-38-C045 | Security, | P0 | DONE | `supply-chain/verification-policy.yaml`, `sbom/inv38.sbom.json` | SBOM + provenance + signed-manifest verify + tamper tests in-repo. |
| INV-38-C048 | Security, | P0 | IN_PROGRESS | `security/dependency-outage-semantics.md`, `security/fail-safe-matrix.yaml` | Live KMS/attestation/time outage behaviour needs those services. |
| INV-38-C049 | Security, | P0 | DONE | `audit/event.schema.json`, `audit/integrity.md` | Hash-chained audit log + offline verifier + injection tests. |
| INV-38-C052 | Resilience | P0 | IN_PROGRESS | `resilience/health-stall-detection.md`, `resilience/thresholds.yaml` | Real device-reset/stall detection latency needs hardware. |
| INV-38-C053 | Resilience | P0 | DONE | `resilience/retry-policy.yaml`, `resilience/retry-safety-matrix.md` | Bounded retry+backoff+jitter engine, deterministic tests. |
| INV-38-C057 | Resilience | P0 | IN_PROGRESS | `resilience/state-recovery.md`, `schemas/recovery-checkpoint-v1.schema.json` | Real crash/device-reset recovery needs hardware. |
| INV-38-C058 | Resilience | P0 | IN_PROGRESS | `resilience/ownership-fencing.md`, `resilience/lease-epoch.schema.json` | True partition/fencing needs a multi-node cluster. |
| INV-38-C061 | Performance | P1 | BLOCKED | `benchmarks/baseline-plan.yaml`, `benchmarks/baseline-results.json` | Reproducible latency/throughput/power baselines require RDMA hardware. |
| INV-38-C063 | Performance | P1 | BLOCKED | `benchmarks/scenarios.yaml`, `benchmarks/load-results/README.md` | Steady/burst/overload campaign requires hardware + load infra. |
| INV-38-C064 | Performance | P1 | BLOCKED | `benchmarks/tenant-overhead.yaml`, `benchmarks/tenant-overhead-results.json` | Per-tenant overhead measurement requires hardware. |
| INV-38-C068 | Performance | P1 | BLOCKED | `benchmarks/power-thermal-plan.yaml`, `benchmarks/power-thermal-results.json` | Power/thermal measurement requires calibrated edge hardware. |
| INV-38-C070 | Performance | P0 | IN_PROGRESS | `ci/performance-gate.yaml`, `benchmarks/approved-baseline.json` | Gate mechanism done+tested; approved baseline BLOCKED on hardware (C061). |
| INV-38-C071 | Observability | P1 | DONE | `observability/health.schema.json`, `observability/status-contract.md` | Health/readiness snapshot, secret-free, generation-consistent. |
| INV-38-C073 | Observability | P1 | DONE | `observability/logging.schema.json`, `observability/logging-policy.md` | Structured log schema + redaction + injection safety tested. |
| INV-38-C074 | Observability | P1 | IN_PROGRESS | `observability/tracing.md`, `observability/trace-propagation-tests/README.md` | Cross-boundary trace continuity needs adjacent live components. |
| INV-38-C075 | Observability | P1 | DONE | `observability/diagnostics.md`, `observability/redaction-policy.yaml` | Redaction policy + bounded diagnostics + adversarial tests. |
| INV-38-C076 | Observability | P1 | DONE | `observability/decision-record.schema.json`, `observability/reason-codes.yaml` | Decision records: every branch has a reason code (tested). |
| INV-38-C077 | Observability | P1 | DONE | `ops/explain-view.md`, `tools/inv38-explain` | Operator explain view (human+machine) with golden fixtures. |
| INV-38-C078 | Observability | P1 | IN_PROGRESS | `observability/lineage-correlation.md`, `observability/resource-identity.schema.json` | Live infra-graph correlation needs the graph service. |
| INV-38-C079 | Observability | P1 | DONE | `observability/telemetry-policy.md`, `observability/retention.yaml` | Telemetry retention/sampling/export policy + conformance test. |
| INV-38-C080 | Observability | P1 | IN_PROGRESS | `observability/dashboards/inv38-overview.json`, `observability/alerts/inv38-alerts.yaml` | Dashboards/alerts validated against synthetic incidents; live wiring pending. |
| INV-38-C084 | Testing | P0 | BLOCKED | `compatibility/test-matrix.yaml`, `tests/compatibility/README.md` | Real CPU/hypervisor/provider/NIC rows require that hardware. |
| INV-38-C085 | Testing | P0 | DONE | `tests/fuzz/README.md`, `tests/fuzz/fuzz_transport.py` | Property/fuzz harness over schema + address arithmetic runs in CI. |
| INV-38-C088 | Testing | P0 | BLOCKED | `tests/performance/README.md`, `tests/soak/README.md` | Soak/fleet at scale requires hardware + multi-node fleet. |
| INV-38-C089 | Testing | P0 | IN_PROGRESS | `tests/disaster/README.md`, `tests/partition/README.md` | Real partition/device-reset needs hardware; model faults tested. |
| INV-38-C090 | Testing | P0 | IN_PROGRESS | `release/acceptance.schema.json`, `release/PK_ACCEPTANCE.json` | Acceptance builder+gate+tamper tests DONE; full certification CONDITIONAL_GO (pk_core/hw evidence absent). |
| INV-38-C093 | Operations, | P1 | IN_PROGRESS | `compatibility/SUPPORTED_VERSIONS.md`, `compatibility/supported-versions.yaml` | Rows for real backend stacks pending qualification. |
| INV-38-C094 | Operations, | P1 | DONE | `SECURITY.md`, `docs/PATCH_AND_EOL_POLICY.md` | SECURITY.md + patch/EOL policy authored; tabletop template included. |
| INV-38-C095 | Operations, | P1 | IN_PROGRESS | `ops/state-reconstruction.md`, `ops/migration.md` | Device-replacement rebuild needs hardware; reconstruction logic tested. |
| INV-38-C097 | Operations, | P1 | DONE | `ops/INCIDENT_RESPONSE.md`, `ops/severity.yaml` | Incident response + severity + runbooks authored. |
| INV-38-C098 | Operations, | P1 | DONE | `governance/review-schedule.yaml`, `governance/review-records/README.md` | Review schedule + governance CI check for overdue reviews. |
| INV-38-C099 | Operations, | P1 | DONE | `governance/waivers.schema.json`, `governance/WAIVERS.json` | Waiver/tech-debt register + validator (dup/expiry/dangling). |

## Blocked items and why (no fabricated evidence)

- **INV-38-C031** — Hardware/firmware/driver qualification requires physical RDMA NICs + IOMMU.
- **INV-38-C061** — Reproducible latency/throughput/power baselines require RDMA hardware.
- **INV-38-C063** — Steady/burst/overload campaign requires hardware + load infra.
- **INV-38-C064** — Per-tenant overhead measurement requires hardware.
- **INV-38-C068** — Power/thermal measurement requires calibrated edge hardware.
- **INV-38-C084** — Real CPU/hypervisor/provider/NIC rows require that hardware.
- **INV-38-C088** — Soak/fleet at scale requires hardware + multi-node fleet.

These are blocked on physical RDMA NICs / IOMMU / a multi-node fleet / calibrated edge hardware, or on the external `pk_core` package, none of which are present in this archive. Each ships with its repository artifact (plan/spec/lock file) and a runnable model harness so the gap is the *evidence*, not the design.

## Release gate

The RTM-driven acceptance record evaluates to **CONDITIONAL_GO** with **29 conditions** and **0 blocking open items**. `GO` is intentionally unreachable from this ZIP: full production certification (C090) requires the real backend, hardware qualification and `pk_core`, per the checklist's own release-evidence rules. A single time-bounded, approved waiver (WV-INV38-001, far-edge power/thermal) is recorded in `governance/WAIVERS.json`.

## What changed in the repository

- **19 executable model modules** (outcomes, lifecycle, status, audit_log, retry, decisions, precedence, authz, negotiation, config_txn/provenance, privilege_check, supply_chain, failsafe, health_stall, recovery, fencing, perf_gate, tracing, telemetry_policy, version_support, rtm_tools, release_gate, governance_checks, platform/preflight).
- **JSON schemas** for the three interfaces + error, outcome, lifecycle, recovery, config layout/provenance/transaction, audit event, health, logging, decision record, resource identity, release acceptance, waivers; plus golden vectors.
- **Policy/spec/ops docs & YAML** across governance, security, resilience, observability, benchmarks, compatibility, platform, config and release.
- **123 new tests** + CI configs (pipeline, performance gate, repo-integrity check) and machine-readable RTM + acceptance record.

_Generated from `traceability/INV38_RTM.json`; regenerate with `python -m inv38_kernel_bypass_transport.rtm_tools .`._