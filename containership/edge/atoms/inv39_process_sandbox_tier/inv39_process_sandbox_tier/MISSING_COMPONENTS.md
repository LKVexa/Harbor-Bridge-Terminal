# INV-39 5.1.0 — Residual Missing Components

Generated from `TRACEABILITY.json` after executing the v5.0.0 implementation checklist. Every item below is either PARTIAL (what is missing is stated) or BLOCKED (the external input needed is named). IMPLEMENTED items are not listed; none is ACCEPTED — acceptance requires an independent human reviewer (MC-093).

## BLOCKED

| ID | Priority | Component | Missing |
|---|---|---|---|
| MC-001 | P2 | Named accountable owner and escalation path | a named accountable owner, security reviewer, on-call and release approver |
| MC-032 | P0 | macOS Seatbelt profile compiler/launcher/verification adapter | a macOS host to execute and certify the Seatbelt backend |
| MC-071 | P2 | Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable | depends on MC-070 analysis; no optimisation claimed |
| MC-073 | P2 | Power/thermal measurements for constrained edge nodes | edge hardware and a power meter |
| MC-087 | P0 | Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions | runners for aarch64, other kernels, Python 3.10/3.12/3.13, bwrap and macOS |
| MC-091 | P0 | Benchmark, soak, burst, and fleet-scale certification tests | soak (>1 h) and fleet-scale environments |
| MC-093 | P0 | Machine-readable signed acceptance evidence required before release certification | an independent human reviewer's signing key and signature |
| MC-094 | P0 | Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent | pk_core framework (fails under INV39_CERT_TARGET=1) |
| MC-106 | P1 | Distribution license/NOTICE and package metadata suitable for redistribution | the owner's choice of licence and NOTICE text |

## PARTIAL

| ID | Priority | Component | Missing |
|---|---|---|---|
| MC-002 | P2 | Approved ADR selecting and justifying Linux bubblewrap/seccomp and macOS Seatbelt, including rejected alternatives | ADR is Proposed; owner approval |
| MC-003 | P2 | Formal SHALL-level functional requirements specification with deployment-context applicability | owner approval; FR-14 (macOS) unverified |
| MC-004 | P2 | Quantified non-functional objectives for startup latency, availability, determinism, isolation, CPU/memory overhead, and tail latency | numbers PROPOSED, measured on one host; owner approval |
| MC-007 | P2 | Backward-compatibility, deprecation, and migration policy for schemas/backends | policy owner approval; migration tooling for /1 consumers |
| MC-010 | P2 | Precedence rules for security vs residency vs SLO vs cost conflicts | residency/cost inputs do not exist in this tier; owner approval |
| MC-011 | P2 | Requirements traceability matrix linking all 100 checks to code, tests, evidence, owner, and status | owners UNASSIGNED for all 100 checks |
| MC-012 | P2 | Supported platform/kernel/runtime/backend compatibility matrix | only x86_64 / kernel 6.18 / Python 3.11 exercised |
| MC-020 | P1 | Automated interoperability tests with PLN-04, GAP-13, GAP-09, and any runtime launcher/control-plane neighbor | tested against reference stubs only; real PLN-04/GAP-13/GAP-09 builds not available |
| MC-021 | P1 | Dependency/package manifest declaring and pinning `pk_core` and supported Python versions | pk_core wheel + digest not supplied |
| MC-029 | P1 | Deterministic bootstrap/install path from an empty supported node | run on this container only, not on a freshly provisioned supported node |
| MC-031 | P0 | Linux bubblewrap (`bwrap`) launcher/integration adapter | bwrap not installed on build host; adapter never executed |
| MC-037 | P0 | Mount namespace hardening, private propagation, root/pivot isolation, read-only bind policy, and safe temporary filesystem setup | no pivot_root / read-only root in the native backend (bwrap path provides it, unexecuted) |
| MC-039 | P0 | Network namespace setup, interface policy, inherited-socket control, and network egress policy | deny-all egress only; no allow-listed egress / interface policy |
| MC-040 | P0 | Device isolation and `/proc`/`/sys` exposure policy | /sys and /dev still host views in native backend |
| MC-043 | P0 | Resource enforcement using rlimits and/or cgroup v2 for processes, CPU, memory, I/O, and file descriptors | cgroup v2 CPU/memory/IO not implemented (EX-004) |
| MC-047 | P0 | Kernel/backend evidence adapter for facts that cannot be exactly read back from normal kernel APIs (notably installed seccomp rule contents) | rule contents launcher-attested; PTRACE_SECCOMP_GET_FILTER read-back not built |
| MC-048 | P0 | Backend-specific threat model with attack paths, mitigations, owners, and tests linked to each threat | draft; owner/security sign-off |
| MC-049 | P0 | Signed policy/artifact verification, digest pinning, provenance validation, and downgrade protection | no asymmetric signatures on policy artifacts; downgrade protection covers config overlays only |
| MC-050 | P0 | Node/control-plane identity and attestation mechanism before trusting profile or evidence sources | hardware-rooted node attestation (TPM/TEE) and an identity service |
| MC-052 | P0 | Encryption design for any remote sensitive profile/evidence transport and at-rest sensitive state | design only; no transport exists; at-rest encryption delegated to disk encryption |
| MC-056 | P1 | Comprehensive failure-mode matrix for process, runtime, node, site, dependency, and control-plane failures | site/control-plane failure rows are design statements |
| MC-057 | P1 | Health/readiness/stall detection with quantified thresholds | no watchdog / stall detector with quantified thresholds |
| MC-060 | P1 | Failover semantics preserving isolation/residency guarantees | no cross-node failover by design; needs PLN-04 confirmation |
| MC-061 | P1 | Defined and tested degraded mode when noncritical dependencies are unavailable | telemetry-export degraded mode described; GAP-09 exporter not built |
| MC-063 | P1 | Duplicate ownership/stale-controller/duplicate-execution prevention | leases are in-process; multi-controller needs a shared store |
| MC-064 | P1 | Quarantine/freeze/disable/kill control with authorization and audit | quarantine blocks new launches; does not yet kill already-running sandboxes |
| MC-065 | P1 | Automated fault-injection suite proving recovery objectives | local fault injection only; no recovery-objective numbers |
| MC-067 | P2 | p50/p95/p99/worst-case release thresholds | thresholds PROPOSED |
| MC-068 | P2 | Steady/burst/overload/scale/recovery performance scenarios | steady + burst only; overload/scale/recovery scenarios missing |
| MC-069 | P2 | Per-workload/per-tenant overhead accounting | per-profile metrics; per-tenant CPU/memory accounting needs cgroups |
| MC-070 | P2 | Profiling evidence for serialization/copy/context-switch/hop inefficiencies | one cProfile run; no hop/copy analysis |
| MC-072 | P2 | Capacity model and saturation signals predicting resource exhaustion | single-node model only |
| MC-082 | P1 | Correlation with release lineage and live infrastructure graph | live infrastructure graph does not exist here |
| MC-083 | P1 | Telemetry retention, sampling, privacy, and export policy | retention enforced by the export target, not built |
| MC-084 | P1 | Dashboards and alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect | dashboards not deployed |
| MC-086 | P0 | Real backend integration tests with adjacent layers and actual OS enforcement | real OS enforcement verified; adjacent layers are stubs |
| MC-092 | P0 | Disaster/partition/reconnect/degraded-control-plane tests | partition/reconnect need a real control plane |
| MC-095 | P1 | Executable canary/staged rollout workflow with tested rollback and emergency disable | no fleet orchestrator |
| MC-096 | P1 | Supported-version compatibility matrix for backend/kernel/runtime/adjacent dependencies | see MC-012 |
| MC-097 | P1 | Patching, vulnerability response, security advisory, and end-of-life SLA/process | advisory channel + SLA owner unassigned |
| MC-098 | P1 | Backup/restore/reconstruction procedure for policy, configuration, evidence, and exception state where external state exists | restore drill not performed |
| MC-099 | P1 | Detailed executable day-0/day-1/day-2 runbooks rather than README-level guidance | not exercised by an operator |
| MC-100 | P1 | Incident severity, paging, escalation, containment, and recovery runbook | paging integration + owner |
| MC-101 | P1 | Recurring access/policy/dependency/configuration/architecture review process | owner + calendar |
| MC-102 | P1 | Exception/waiver/technical-debt/deprecation register with owner and expiry | every entry owner _UNASSIGNED_ |
| MC-104 | P0 | CI workflow executing compile, unit, optimized-mode, schema, backend integration, security, benchmark, and release gates | ci.sh executed locally; hosted workflow never run |
| MC-105 | P0 | SBOM/provenance generation and signed release artifact pipeline | SBOM+provenance done; release signing key not provisioned |
