# INV-66 v4.2.0 → v4.3.0 remediation: checklist execution record (generated)

Generated 2026-09-23T00:00:00Z by `tools/gen_docs.py` from `tools/mc_disposition.py`. Legend: ✅ DONE · ◐ PARTIAL · ☐ OPEN · ⊘ N/A (waived with justification).

**Totals over 1,420 items:** ✅ 1013 · ◐ 278 · ☐ 120 · ⊘ 9

| MC | Component | Sev | Disposition | ✅ | ◐ | ☐ | ⊘ | Waivers |
|---|---|---|---|---|---|---|---|---|
| MC-001 | Bundled master prompt/workflow source (`MASTER.md`) | Medium | partial | 14 | 5 | 1 | 0 | W-005 |
| MC-002 | Approved architecture decision record (ADR) | High | partial | 16 | 2 | 2 | 0 | W-002 |
| MC-003 | Accountable owner and escalation matrix | High | partial | 14 | 4 | 2 | 0 | W-001 |
| MC-004 | Deployment/topology architecture specification | High | closed-local | 15 | 4 | 1 | 0 | — |
| MC-005 | Production source-of-truth design | Critical | closed-local | 16 | 3 | 1 | 0 | — |
| MC-006 | Normative SHALL requirements specification | High | closed-local | 17 | 1 | 2 | 0 | — |
| MC-007 | Requirements traceability matrix (RTM) | High | closed-local | 17 | 1 | 2 | 0 | — |
| MC-008 | Lifecycle/state-transition model | High | closed-local | 15 | 2 | 3 | 0 | — |
| MC-009 | Capacity, quota, and fairness model | High | partial | 12 | 6 | 2 | 0 | W-009 |
| MC-010 | Offline/partition semantics | High | closed-local | 15 | 3 | 2 | 0 | — |
| MC-011 | Constraint precedence policy | Medium | closed-local | 15 | 3 | 2 | 0 | — |
| MC-012 | Versioned typed admission schema | Critical | closed-local | 17 | 2 | 1 | 0 | — |
| MC-013 | Versioned RBAC administration schema/API | Critical | closed-local | 14 | 5 | 1 | 0 | — |
| MC-014 | Versioned audit event schema/API | Critical | closed-local | 17 | 1 | 2 | 0 | — |
| MC-015 | Authentication boundary | Critical | closed-local | 16 | 3 | 1 | 0 | — |
| MC-016 | Structured machine-readable error model | High | closed-local | 18 | 1 | 1 | 0 | — |
| MC-017 | Idempotency, timeout, cancellation, retry, and backpressure contract | High | closed-local | 16 | 3 | 1 | 0 | — |
| MC-018 | Protocol/version compatibility matrix and negotiation | High | closed-local | 14 | 4 | 2 | 0 | — |
| MC-019 | Real deployment-manager adapter | Critical | partial | 15 | 4 | 1 | 0 | W-004 |
| MC-020 | Adjacent-layer integration adapters/tests | Critical | partial | 14 | 4 | 2 | 0 | W-004 |
| MC-021 | GitOps ingestion/change-controller integration | High | closed-local | 13 | 5 | 2 | 0 | — |
| MC-022 | Declarative production configuration schema/loader | Critical | closed-local | 18 | 1 | 1 | 0 | — |
| MC-023 | Configuration provenance and version history | High | closed-local | 18 | 1 | 1 | 0 | — |
| MC-024 | Atomic configuration activation and rollback | Critical | closed-local | 14 | 4 | 2 | 0 | — |
| MC-025 | Persistent RBAC/policy store | Critical | closed-local | 14 | 5 | 1 | 0 | — |
| MC-026 | Approved registry/signer policy administration store | Critical | closed-local | 16 | 3 | 1 | 0 | — |
| MC-027 | Secret-management integration | Critical | closed-local | 15 | 3 | 2 | 0 | — |
| MC-028 | Deterministic bootstrap/install packaging | High | partial | 13 | 5 | 2 | 0 | W-010 |
| MC-029 | Cryptographic artifact signature verification | Critical | partial | 14 | 5 | 1 | 0 | W-015 |
| MC-030 | Artifact digest/provenance verification | Critical | closed-local | 12 | 5 | 2 | 1 | — |
| MC-031 | Enterprise identity federation | Critical | partial | 12 | 5 | 3 | 0 | W-004 |
| MC-032 | Organisation/tenant RBAC hierarchy and capability model | Critical | closed-local | 16 | 3 | 1 | 0 | — |
| MC-033 | External policy-engine enforcement | Critical | partial | 16 | 2 | 1 | 1 | W-004 |
| MC-034 | Transport/storage encryption and key rotation | Critical | partial | 12 | 3 | 5 | 0 | W-007 |
| MC-035 | Durable tamper-evident audit anchoring | Critical | partial | 15 | 4 | 1 | 0 | W-007 |
| MC-036 | Formal threat model | High | closed-local | 16 | 2 | 2 | 0 | W-002 |
| MC-037 | Security adversarial and fuzz suite | High | closed-local | 15 | 3 | 2 | 0 | — |
| MC-038 | Durable state store with crash recovery/replay | Critical | closed-local | 16 | 3 | 1 | 0 | — |
| MC-039 | HA replication/consensus/leader election | Critical | partial | 13 | 5 | 2 | 0 | W-006 |
| MC-040 | Dependency health and degraded-mode controller | High | closed-local | 14 | 4 | 2 | 0 | — |
| MC-041 | Bounded retry/circuit breaker/load shedding | High | closed-local | 14 | 5 | 1 | 0 | — |
| MC-042 | Quarantine/freeze/emergency-disable control | High | closed-local | 15 | 4 | 1 | 0 | — |
| MC-043 | Fault-injection/recovery test suite | High | closed-local | 15 | 3 | 2 | 0 | — |
| MC-044 | Reproducible benchmark/load/soak suite | High | closed-local | 12 | 7 | 1 | 0 | — |
| MC-045 | Performance thresholds and regression gate | High | partial | 13 | 6 | 1 | 0 | W-011 |
| MC-046 | Bounded audit/forwarded retention | Critical | closed-local | 14 | 5 | 1 | 0 | — |
| MC-047 | Capacity/saturation model | High | closed-local | 16 | 3 | 1 | 0 | — |
| MC-048 | Edge power/thermal characterization | Low/conditional | n/a | 12 | 1 | 1 | 6 | W-012 |
| MC-049 | Health/readiness/version/config/dependency endpoint | High | closed-local | 17 | 2 | 1 | 0 | — |
| MC-050 | Metrics instrumentation/export | High | closed-local | 13 | 5 | 2 | 0 | — |
| MC-051 | Structured operational logging | High | closed-local | 16 | 3 | 1 | 0 | — |
| MC-052 | Distributed tracing/context propagation | High | closed-local | 14 | 5 | 1 | 0 | — |
| MC-053 | Decision explainability/policy linkage view | High | closed-local | 16 | 3 | 1 | 0 | — |
| MC-054 | Telemetry retention/privacy/export policy and dashboards/alerts | High | closed-local | 16 | 2 | 2 | 0 | — |
| MC-055 | Public-interface contract test suite | High | closed-local | 15 | 4 | 1 | 0 | — |
| MC-056 | End-to-end integration suite | Critical | partial | 10 | 8 | 2 | 0 | W-004 |
| MC-057 | Compatibility/platform test matrix | High | partial | 10 | 5 | 5 | 0 | W-010 |
| MC-058 | Distributed concurrency/race suite | High | partial | 12 | 7 | 1 | 0 | W-006 |
| MC-059 | Disaster/partition/reconnect certification suite | High | partial | 10 | 7 | 3 | 0 | W-006 |
| MC-060 | Full machine-readable production acceptance evidence bundle | High | partial | 13 | 5 | 2 | 0 | W-003 |
| MC-061 | CI/CD release pipeline and staged rollout artifacts | Critical | partial | 12 | 5 | 3 | 0 | W-010 |
| MC-062 | Vulnerability/SBOM/patch/EOL program artifacts | High | partial | 13 | 4 | 3 | 0 | W-010 |
| MC-063 | Backup/restore/migration/reconstruction runbook | Critical | closed-local | 12 | 7 | 1 | 0 | — |
| MC-064 | Complete day-0/day-1/day-2 operational runbooks | High | partial | 15 | 3 | 2 | 0 | W-014 |
| MC-065 | Incident response/on-call runbook | High | partial | 14 | 4 | 2 | 0 | W-014 |
| MC-066 | Recurring review automation/evidence | Medium | closed-local | 13 | 5 | 2 | 0 | — |
| MC-067 | Exception/waiver/technical-debt register | Medium | closed-local | 14 | 4 | 2 | 0 | — |
| MC-068 | Formal production exit gate artifact | Critical | closed-local | 14 | 4 | 2 | 0 | — |
| MC-069 | Cross-lattice inventory service | High | closed-local | 11 | 7 | 2 | 0 | — |
| MC-070 | Audit query/retention/export service | High | partial | 10 | 8 | 2 | 0 | W-013 |
| MC-071 | Repository license/notice metadata | Medium | partial | 13 | 5 | 1 | 1 | W-008 |

## Program-level gates

- ✅ `INV66-PROG-01` All 71 MC IDs have an RTM disposition and no Critical/High item is silently omitted.
- ☐ `INV66-PROG-02` All C001-C100 controls have machine-readable evidence or an approved, unexpired N/A/waiver disposition.
- ◐ `INV66-PROG-03` Admission, RBAC, audit, inventory, configuration, and administrative interfaces are versioned typed contracts with compatibility tests.
- ◐ `INV66-PROG-04` Authentication, capability-based authorization, policy evaluation, artifact signature/provenance verification, and tenant isolation are enforced end to end.
- ◐ `INV66-PROG-05` Authoritative state and audit data are durable, recoverable, tamper-evident, replicated as required, and validated by crash/partition/restore tests.
- ◐ `INV66-PROG-06` No unadmitted manifest can be forwarded under success, failure, retry, restart, failover, stale-leader, or partition scenarios.
- ◐ `INV66-PROG-07` Performance and capacity tests demonstrate the approved latency/throughput/resource thresholds and release regression gates pass.
- ◐ `INV66-PROG-08` Health, metrics, logs, traces, explain views, dashboards, alerts, retention/privacy controls, and runbook links are operationally validated.
- ☐ `INV66-PROG-09` E2E, compatibility, fuzz/security, concurrency, fault-injection, disaster/reconnect, benchmark/soak, backup/restore, and rollout/rollback suites pass in production-like environments.
- ◐ `INV66-PROG-10` SBOM, vulnerability status, license/notice, signed build/provenance, deployment artifacts, config/policy revisions, and full acceptance evidence are attached to the release.
- ☐ `INV66-PROG-11` Day-0/1/2 and incident runbooks have been exercised by operators; ownership/escalation rotations are live.
- ☐ `INV66-PROG-12` MC-068 production exit gate yields GO with the exact release artifact and evidence-bundle digests intended for production promotion.

## Item detail


### MC-001 — Bundled master prompt/workflow source (`MASTER.md`)

- ◐ `MC-001-T01` Locate the authoritative source for the Post-Kubernetes Master Prompt & Workflow Series and determine whether INV-66 is governed by a frozen release, generated … — *Authoritative Post-Kubernetes master text is not in the archive; MASTER.md pins CHECKLIST.json as the governing frozen source (W-005)*
- ◐ `MC-001-T02` Create `MASTER.md` with an immutable document identifier, semantic version, source revision/commit, generation timestamp, and SHA-256 digest of the authoritativ… — *MASTER.md carries id/version/timestamp/digest of CHECKLIST.json, not of the upstream master prompt (W-005)*
- ✅ `MC-001-T03` Ensure all 100 INV-66 checklist requirements are represented without silent omission, reordering, or semantic weakening; add a machine-verifiable count and ID r…
- ✅ `MC-001-T04` Add a provenance header identifying the generator/source path and the exact transformation rules used if `MASTER.md` is generated rather than hand-maintained.
- ◐ `MC-001-T05` Add CI validation that fails if README/BOM claims `MASTER.md` exists but the file is missing, or if its digest/count no longer matches the authoritative source. — *Check implemented in tools/repo_checks.py; not yet run on hosted CI (W-010)*
- ✅ `MC-001-T06` Add release-manifest coverage so `MASTER.md` is included in `RELEASE_MANIFEST.sha256` and therefore protected by release integrity checks.
- ✅ `MC-001-T07` Document whether `MASTER.md` is normative or informative and define the change-control process required to update it.
- ✅ `MC-001-T08` If the project intentionally does not bundle the master source, remove all inclusion claims and replace them with a resolvable, version-pinned source reference …
- ◐ `MC-001-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence. — *Roles and change control defined; named people pending (W-001)*
- ✅ `MC-001-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- ✅ `MC-001-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- ✅ `MC-001-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- ✅ `MC-001-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.
- ✅ `MC-001-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-001-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-001-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-001-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-001-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-001-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-001-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-002 — Approved architecture decision record (ADR)

- ✅ `MC-002-T01` Create an ADR using a stable ID such as `ADR-0001-enterprise-wasm-control-plane.md` and record status, date, deciders, technical owners, and review expiry.
- ✅ `MC-002-T02` Document the decision to use Cosmonic Control/wasmCloud-aligned control-plane concepts, distinguishing product-specific dependencies from architecture-level con…
- ✅ `MC-002-T03` Compare at least the chosen approach with a custom wasmCloud controller, Kubernetes/GitOps controller patterns, direct lattice management, and alternative polic…
- ✅ `MC-002-T04` Record decision drivers: multi-lattice governance, tenant isolation, signer/registry policy, GitOps integration, append-only audit, latency SLO, edge/site auton…
- ✅ `MC-002-T05` Record rejected alternatives and explicit reasons including complexity, failure domains, lock-in, portability, security boundary, and lifecycle cost.
- ✅ `MC-002-T06` Capture hard constraints and assumptions from `contract.py`, including untrusted callers, independently failing peers/paths/stores, and local/remote behavioral …
- ✅ `MC-002-T07` Document consequences: new durable stores, identity federation, policy-engine coupling, deployment-manager adapter, audit anchoring, HA requirements, and operat…
- ☐ `MC-002-T08` Require architecture/security/SRE approval and link the ADR to the RTM and production-exit gate. — *Architecture/security/SRE approval not yet given (W-002)*
- ◐ `MC-002-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence. — *Roles and change control defined; named people pending (W-001)*
- ✅ `MC-002-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- ✅ `MC-002-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- ✅ `MC-002-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- ✅ `MC-002-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.
- ✅ `MC-002-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-002-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-002-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-002-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-002-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-002-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-002-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-003 — Accountable owner and escalation matrix

- ✅ `MC-003-T01` Define a RACI/ownership matrix covering service owner, product owner, architecture owner, security owner, IAM owner, SRE/on-call owner, data/audit owner, and re…
- ☐ `MC-003-T02` Assign each role to a durable team or rotation rather than only an individual; include primary and secondary escalation contacts. — *Durable teams/rotations and contacts must be named by the organisation (W-001)*
- ✅ `MC-003-T03` Define 24x7 vs business-hours support expectations and severity-based acknowledgement/engagement targets.
- ✅ `MC-003-T04` Map ownership to concrete boundaries: admission service, RBAC/policy data, registry/signer policy, audit store, identity federation, deployment adapter, CI/CD, …
- ✅ `MC-003-T05` Define who can approve emergency policy changes, disable admission, rotate keys, restore state, waive controls, and declare production readiness.
- ✅ `MC-003-T06` Create an escalation tree for dependency failures involving INV-63, INV-64, GAP-13, GAP-07, identity, registry, KMS, and storage teams.
- ◐ `MC-003-T07` Include ownership metadata in runbooks, alert routing, CODEOWNERS/review rules, and production-exit evidence. — *Ownership in runbooks/alerts; no CODEOWNERS until owners named (W-001)*
- ◐ `MC-003-T08` Add a recurring control that detects orphaned ownership when teams, aliases, or rotations change. — *tools/review.py flags placeholder owners; no HR/rotation source to diff against (W-001)*
- ◐ `MC-003-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence. — *Roles and change control defined; named people pending (W-001)*
- ✅ `MC-003-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- ✅ `MC-003-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- ✅ `MC-003-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- ✅ `MC-003-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.
- ✅ `MC-003-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-003-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-003-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-003-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-003-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-003-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-003-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-004 — Deployment/topology architecture specification

- ✅ `MC-004-T01` Produce a production topology diagram covering control-plane instances, load balancers/gateways, identity provider, policy engine, provenance service, registry …
- ✅ `MC-004-T02` Define trust zones and network boundaries for tenant traffic, administrative traffic, east-west service calls, storage access, and cross-site replication.
- ◐ `MC-004-T03` Document deployment modes for single site, multi-site, regional, disconnected/edge, and disaster-recovery operation, including unsupported topologies. — *Single-site + DR restore documented; multi-site/regional/edge modes stated but not designed in depth (W-006, W-012)*
- ✅ `MC-004-T04` Define failure domains and placement rules so replicas do not share node/rack/zone/site single points of failure where the availability target requires separati…
- ✅ `MC-004-T05` Identify every persisted dataset, its authoritative owner, consistency model, replication scope, retention class, residency constraints, and recovery objective.
- ✅ `MC-004-T06` Define ingress/egress ports, protocols, TLS identities, DNS/service-discovery assumptions, firewall policy, and required network reachability.
- ✅ `MC-004-T07` Document scaling units and control loops: stateless admission replicas, stateful stores, worker/queue partitions, and cross-lattice inventory shards.
- ◐ `MC-004-T08` Add sequence/data-flow diagrams for successful admission, denial, dependency failure, configuration activation, rollback, and emergency freeze. — *Topology + flows described in prose/ASCII; no separate sequence diagrams per flow*
- ◐ `MC-004-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence. — *Roles and change control defined; named people pending (W-001)*
- ✅ `MC-004-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- ✅ `MC-004-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- ✅ `MC-004-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- ✅ `MC-004-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.
- ✅ `MC-004-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-004-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-004-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-004-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-004-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-004-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-004-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-005 — Production source-of-truth design

- ✅ `MC-005-T01` Define the authoritative data model for admissions, refusals, policy/config versions, RBAC changes, registry/signer changes, forwarding outcomes, and cross-latt…
- ✅ `MC-005-T02` Select a durable source-of-truth architecture: append-only event log with projections, transactional database plus immutable journal, or equivalent design with …
- ✅ `MC-005-T03` Define event IDs, monotonic ordering scope, causal/correlation identifiers, idempotency keys, actor identity, policy/config digests, timestamps, and integrity f…
- ✅ `MC-005-T04` Define exactly which state is reconstructed from the log and which state is independently authoritative; prohibit ambiguous dual-write ownership.
- ✅ `MC-005-T05` Implement atomic persistence semantics so a decision cannot be acknowledged as durable if its authoritative audit/state record was not committed.
- ✅ `MC-005-T06` Define recovery/replay from an empty projection, checkpoint/snapshot strategy, schema evolution, and deterministic replay requirements.
- ◐ `MC-005-T07` Protect the source of truth using access control, encryption, tamper-evident anchoring, backup/restore, retention, and legal-hold controls. — *Access control, anchoring, backup, retention done; at-rest encryption delegated to volume (W-007)*
- ✅ `MC-005-T08` Add consistency tests proving post-crash state, replayed state, exported audit state, and live projections converge to the same logical result.
- ◐ `MC-005-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence. — *Roles and change control defined; named people pending (W-001)*
- ✅ `MC-005-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- ✅ `MC-005-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- ✅ `MC-005-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- ✅ `MC-005-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.
- ✅ `MC-005-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-005-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-005-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-005-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-005-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-005-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-005-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-006 — Normative SHALL requirements specification

- ✅ `MC-006-T01` Create a normative requirements specification with stable IDs (for example `REQ-INV66-*`) and RFC 2119/8174-style SHALL/SHOULD/MAY language.
- ✅ `MC-006-T02` Cover functional requirements for admission, RBAC, registry/signer policy, audit, cross-lattice inventory, GitOps intake, configuration, and administrative cont…
- ✅ `MC-006-T03` Cover non-functional requirements for availability, durability, consistency, latency, throughput, isolation, residency, recoverability, observability, and opera…
- ✅ `MC-006-T04` For every SHALL, define measurable acceptance criteria, evidence type, owner, and failure disposition.
- ✅ `MC-006-T05` Separate normative requirements from implementation notes, rationale, examples, and future work so certification cannot be satisfied by prose-only intent.
- ✅ `MC-006-T06` Express negative/security requirements explicitly, including zero forwarding of unadmitted manifests, fail-closed conditions, and forbidden cross-tenant disclos…
- ✅ `MC-006-T07` Assign version and change history; require impact analysis when a normative requirement changes.
- ✅ `MC-006-T08` Validate that the specification maps without gaps to all applicable C001-C100 checklist items.
- ✅ `MC-006-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- ✅ `MC-006-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- ✅ `MC-006-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- ✅ `MC-006-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- ☐ `MC-006-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability. — *Human review pending (W-002)*
- ✅ `MC-006-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-006-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-006-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-006-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-006-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-006-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-006-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-007 — Requirements traceability matrix (RTM)

- ✅ `MC-007-T01` Create a machine-readable RTM in JSON/YAML/CSV with one row per normative requirement and one row per C001-C100 control where appropriate.
- ✅ `MC-007-T02` Include fields for requirement ID, source, owner, implementation artifact/path, test IDs, evidence URI/hash, status, waiver ID, release version, and last verifi…
- ✅ `MC-007-T03` Allow many-to-many mappings between requirements, code modules, schemas, tests, dashboards, runbooks, and evidence.
- ✅ `MC-007-T04` Fail CI when a normative SHALL has no implementation reference, no verification reference, an expired waiver, or stale/missing evidence.
- ✅ `MC-007-T05` Validate that all 100 checklist IDs are present exactly once in the control coverage view and that no unknown/deprecated IDs appear silently.
- ✅ `MC-007-T06` Generate human-readable coverage summaries from the RTM rather than maintaining duplicate manually edited status tables.
- ✅ `MC-007-T07` Preserve historical RTM snapshots per release to support auditability and regression analysis.
- ✅ `MC-007-T08` Link each MC-001..MC-071 closure to the RTM evidence that demonstrates the gap is actually resolved.
- ✅ `MC-007-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- ✅ `MC-007-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- ✅ `MC-007-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- ✅ `MC-007-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- ☐ `MC-007-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability. — *Human review pending (W-002)*
- ✅ `MC-007-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-007-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-007-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-007-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-007-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-007-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-007-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-008 — Lifecycle/state-transition model

- ✅ `MC-008-T01` Define an explicit workload/change lifecycle such as proposed -> validated -> authorized -> admitted -> persisted -> forwarded -> acknowledged -> deployed, plus…
- ✅ `MC-008-T02` Define legal transitions, transition initiators, guards, side effects, and required durable writes using a state-transition table or executable state machine.
- ✅ `MC-008-T03` Distinguish admission decision state from downstream deployment/reconciliation state so a successful admission is not misreported as successful deployment.
- ✅ `MC-008-T04` Define retryable vs terminal failures at each transition and whether retries reuse the same idempotency key and decision record.
- ☐ `MC-008-T05` Define cancellation and supersession semantics for GitOps changes that are replaced while validation or forwarding is in progress. — *Supersession/cancellation of in-flight GitOps changes not modelled*
- ◐ `MC-008-T06` Define rollback transitions and whether rollback itself requires fresh authorization/admission. — *Rollback is an authorised lifecycle transition; re-admission of a replacement goes through admit, but 'fresh authorization for rollback' policy is not configurable*
- ✅ `MC-008-T07` Include quarantine/freeze transitions that prevent forwarding while preserving operator visibility and auditability.
- ✅ `MC-008-T08` Create transition tests that prove illegal transitions fail closed and concurrent transitions cannot produce contradictory terminal states.
- ✅ `MC-008-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- ✅ `MC-008-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- ✅ `MC-008-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- ✅ `MC-008-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- ☐ `MC-008-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability. — *Human review pending (W-002)*
- ✅ `MC-008-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-008-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-008-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-008-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-008-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-008-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-008-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-009 — Capacity, quota, and fairness model

- ◐ `MC-009-T01` Define quota dimensions by organisation, tenant, lattice, environment, site, workload, principal, and API operation where applicable. — *Quotas by tenant/lattice (+ global bulkhead); not by principal/operation/site*
- ✅ `MC-009-T02` Specify hard limits and soft budgets for request rate, concurrent admissions, manifest bytes/components, pending forwards, inventory objects, audit write rate, …
- ◐ `MC-009-T03` Define fairness algorithm and isolation strategy (for example per-tenant token buckets/weighted fair queues) so one tenant cannot starve others. — *Per-tenant token buckets; no weighted fair queue (W-009)*
- ◐ `MC-009-T04` Define burst capacity, refill rates, borrowing rules, and administrative overrides with expiration and audit. — *Burst = rate; no borrowing or expiring administrative overrides (W-009)*
- ◐ `MC-009-T05` Expose quota headers/status or typed error details so clients can distinguish policy denial from throttling/capacity exhaustion. — *QUOTA_EXCEEDED is typed + retryable; no Retry-After/quota headers*
- ✅ `MC-009-T06` Define queue depth and wait-time limits; reject or shed load before unbounded memory or latency growth occurs.
- ✅ `MC-009-T07` Create capacity formulas linking replica count and dependency throughput to safe admitted QPS and tenant count.
- ◐ `MC-009-T08` Test noisy-neighbor scenarios and prove per-tenant limits and global protection remain effective under overload. — *Quota + bulkhead + overload shedding tested; no multi-tenant noisy-neighbour load test*
- ✅ `MC-009-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- ✅ `MC-009-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- ✅ `MC-009-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- ✅ `MC-009-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- ☐ `MC-009-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability. — *Human review pending (W-002)*
- ✅ `MC-009-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-009-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-009-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-009-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-009-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-009-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-009-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-010 — Offline/partition semantics

- ✅ `MC-010-T01` Document behavior independently for identity, policy, registry, signer/provenance, deployment manager, audit store, configuration store, DNS/time, and network u…
- ✅ `MC-010-T02` Classify each dependency as security-critical, durability-critical, availability-enhancing, or optional and define fail-closed/fail-open/degraded behavior accor…
- ✅ `MC-010-T03` Define cache eligibility, maximum staleness, signed cache artifacts, revocation behavior, and clock assumptions for offline operation.
- ✅ `MC-010-T04` Define whether previously admitted workloads may continue, whether new admissions are blocked, and whether administrative changes are accepted during partitions…
- ◐ `MC-010-T05` Define local-site autonomy and reconciliation semantics when connectivity returns, including conflict resolution and duplicate-event handling. — *Single-writer per site; reconnect = outbox drain; no multi-site conflict resolution (W-006)*
- ✅ `MC-010-T06` Define operator-visible degraded states and explicit reason codes for denials caused by unavailable trust dependencies.
- ✅ `MC-010-T07` Prevent stale identity/policy/provenance data from silently extending beyond configured TTL/lease periods.
- ◐ `MC-010-T08` Create partition/reconnect tests that exercise each dependency independently and in correlated failure combinations. — *Dependency failures tested independently; correlated/partition combinations not tested (W-006)*
- ✅ `MC-010-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- ✅ `MC-010-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- ✅ `MC-010-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- ✅ `MC-010-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- ☐ `MC-010-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability. — *Human review pending (W-002)*
- ✅ `MC-010-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-010-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-010-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-010-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-010-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-010-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-010-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-011 — Constraint precedence policy

- ✅ `MC-011-T01` Define a deterministic precedence lattice for security, legal/residency, tenant isolation, safety, availability/SLO, performance, and cost constraints.
- ✅ `MC-011-T02` Specify non-overridable controls such as signature/provenance trust, tenant isolation, and legal residency where applicable.
- ✅ `MC-011-T03` Define how conflicts are surfaced as stable machine-readable reason codes rather than relying on evaluation order or free-form text.
- ✅ `MC-011-T04` Define policy-composition semantics for organisation, tenant, environment, site, lattice, and workload scopes including deny-overrides/permit-overrides rules.
- ✅ `MC-011-T05` Define tie-breaking for equally scoped policies using explicit priority/version rather than incidental storage or iteration order.
- ◐ `MC-011-T06` Document emergency exceptions, who may authorize them, their maximum TTL, required compensating controls, and mandatory audit fields. — *Freeze/waiver rules documented; no emergency-exception object with TTL for tiers 3-5 in code*
- ◐ `MC-011-T07` Create conflict fixtures that prove the same input produces the same outcome across nodes, versions, and policy-engine deployment modes. — *Determinism via single evaluation order + golden fixtures; no cross-node/cross-engine differential test*
- ✅ `MC-011-T08` Link precedence rules to the operator explain view so rejected constraints and winning constraints are visible.
- ✅ `MC-011-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- ✅ `MC-011-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- ✅ `MC-011-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- ✅ `MC-011-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- ☐ `MC-011-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability. — *Human review pending (W-002)*
- ✅ `MC-011-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-011-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-011-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-011-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-011-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-011-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-011-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-012 — Versioned typed admission schema

- ✅ `MC-012-T01` Define the canonical `PK_ECP_ADMIT/1` request/response schema in JSON Schema, protobuf, WIT, or another versioned IDL and publish generated language bindings wh…
- ✅ `MC-012-T02` Model authenticated principal separately from user-supplied payload fields; include tenant/organisation, lattice, environment/site context, manifest, request ID…
- ◐ `MC-012-T03` Define manifest schema or reference the authoritative INV-64 schema by immutable version/digest rather than using unconstrained generic JSON. — *Manifest schema bundled; INV-64 authoritative schema not available to pin by digest (W-004)*
- ✅ `MC-012-T04` Define a typed decision response with admitted/denied status, stable reason/error codes, policy/config/provenance versions, manifest digest, audit event ID, and…
- ✅ `MC-012-T05` Add explicit maximum sizes/counts, required fields, canonicalization rules, unknown-field behavior, and Unicode/identifier normalization rules.
- ✅ `MC-012-T06` Publish compatibility rules for adding/removing fields and version negotiation for `PK_ECP_ADMIT/1` successors.
- ✅ `MC-012-T07` Generate positive, negative, boundary, and malicious conformance fixtures from the schema.
- ✅ `MC-012-T08` Validate every externally received request against the schema before security-sensitive evaluation and fail closed on validation failure.
- ✅ `MC-012-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-012-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-012-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-012-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-012-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-012-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-012-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-012-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-012-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-012-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-012-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-012-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-013 — Versioned RBAC administration schema/API

- ◐ `MC-013-T01` Define a typed `PK_ECP_RBAC/1` administration API covering bindings, groups/service principals, organisation/tenant/lattice scopes, roles/capabilities, conditio… — *RBAC administered via versioned config revisions (bindings/groups/service principals); no per-binding CRUD endpoint*
- ✅ `MC-013-T02` Separate read/query operations from mutation operations and define distinct authorization capabilities for each.
- ✅ `MC-013-T03` Include optimistic concurrency/version preconditions so concurrent administrators cannot silently overwrite newer policy state.
- ◐ `MC-013-T04` Require change reason, actor, approver where applicable, desired activation time, expiry for temporary grants, and idempotency key on mutations. — *Actor, approvers, source revision, expiry recorded; no desired activation time*
- ◐ `MC-013-T05` Define bulk import/export semantics with transactional validation and per-entry error reporting without partial unsafe application. — *Whole-document transactional validation; no per-entry error report*
- ◐ `MC-013-T06` Define pagination/filtering and high-cardinality protections for query surfaces. — *Audit query is cursor-paginated/bounded; binding listing is via /version + config only*
- ✅ `MC-013-T07` Define stable error codes for conflict, stale version, forbidden scope, invalid principal, invalid capability, dependency unavailable, and policy lock/freeze.
- ✅ `MC-013-T08` Add contract tests and authorization-negative tests for every operation and scope boundary.
- ✅ `MC-013-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-013-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-013-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-013-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-013-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-013-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-013-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-013-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-013-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-013-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-013-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-013-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-014 — Versioned audit event schema/API

- ✅ `MC-014-T01` Define `PK_ECP_AUDIT/1` as a versioned immutable event schema with event ID, sequence/order scope, timestamp, actor, subject, tenant/lattice/workload IDs, actio…
- ✅ `MC-014-T02` Define query API semantics for time range, actor, tenant, lattice, workload, action, decision, event ID, and correlation/request ID filters.
- ✅ `MC-014-T03` Define pagination/cursor stability, maximum query windows, rate limits, and authorization controls for audit reads.
- ✅ `MC-014-T04` Define immutable export format and cryptographic verification metadata so exported batches can be independently validated.
- ✅ `MC-014-T05` Define retention class, legal hold, archival tier, deletion restrictions, and privacy/redaction behavior without mutating integrity-critical source records.
- ✅ `MC-014-T06` Define schema evolution rules that preserve old event readability and chain/hash verification.
- ☐ `MC-014-T07` Create SIEM/export adapter contract with delivery acknowledgements, retry/idempotency, backpressure, and dead-letter semantics. — *No SIEM delivery adapter with ack/retry/dead-letter (W-013)*
- ✅ `MC-014-T08` Add conformance fixtures proving events emitted by every security-sensitive operation validate against the schema.
- ✅ `MC-014-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-014-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-014-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-014-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-014-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-014-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-014-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-014-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-014-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-014-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-014-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-014-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-015 — Authentication boundary

- ✅ `MC-015-T01` Place authentication at the transport/service boundary so `ControlPlane.admit()` never treats a caller-supplied username as proof of identity.
- ◐ `MC-015-T02` Select supported mechanisms such as OIDC/JWT for humans/services, SPIFFE/SPIRE or mTLS workload identities for service-to-service calls, and document where each… — *JWT (EdDSA/HS256) + mTLS cert binding; SPIFFE/SPIRE not integrated*
- ✅ `MC-015-T03` Validate issuer, audience, signature algorithm, key ID, expiry/not-before, nonce/replay characteristics, and tenant/organisation claims before authorization.
- ✅ `MC-015-T04` Bind the authenticated principal to request context and prohibit overriding it through manifest or API fields.
- ◐ `MC-015-T05` Define certificate/token revocation, signing-key rotation, JWKS caching/refresh, clock-skew limits, and fail-closed behavior when trust material is unavailable. — *Key rotation by kid in config, skew bounds, fail closed; no JWKS fetch/refresh, no revocation list*
- ✅ `MC-015-T06` Map external identities into stable internal principal IDs so email/display-name changes do not rewrite authorization history.
- ✅ `MC-015-T07` Emit authentication outcome and principal metadata into the audit trail without logging credentials/tokens.
- ✅ `MC-015-T08` Add negative tests for forged tokens, wrong audience, expired/not-yet-valid tokens, revoked credentials, unknown CA, tenant mismatch, and credential replay.
- ✅ `MC-015-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-015-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-015-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-015-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-015-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-015-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-015-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-015-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-015-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-015-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-015-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-015-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-016 — Structured machine-readable error model

- ✅ `MC-016-T01` Define a stable namespaced error-code taxonomy separating validation, authentication, authorization, policy, provenance, quota, conflict, dependency, timeout, o…
- ✅ `MC-016-T02` For each code, define HTTP/gRPC/WIT mapping, retryability, operator severity, client remediation guidance, and whether details are safe to expose.
- ✅ `MC-016-T03` Return machine-readable field violations with JSON pointer/path and bounded sanitized context for invalid requests.
- ✅ `MC-016-T04` Include correlation/request ID and dependency identifier where relevant, but never secret values, raw tokens, or cross-tenant data.
- ✅ `MC-016-T05` Keep human-readable messages non-normative; clients must branch on stable codes, not string matching.
- ✅ `MC-016-T06` Define nested causes only when they preserve abstraction boundaries and cannot leak infrastructure internals.
- ✅ `MC-016-T07` Version the error catalog and test backward compatibility for existing codes.
- ✅ `MC-016-T08` Add tests asserting every documented failure path maps to an approved code and unknown exceptions become a safe generic internal error.
- ✅ `MC-016-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-016-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-016-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-016-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-016-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-016-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-016-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-016-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-016-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-016-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-016-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-016-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-017 — Idempotency, timeout, cancellation, retry, and backpressure contract

- ✅ `MC-017-T01` Define globally unique request IDs and client-supplied idempotency keys, including scope, retention window, collision behavior, and replayed-response semantics.
- ✅ `MC-017-T02` Define end-to-end deadlines and per-dependency timeout budgets derived from the p99 admission SLO rather than independent arbitrary defaults.
- ◐ `MC-017-T03` Propagate cancellation to in-flight dependency calls when safe, while preserving already-committed authoritative audit/state writes. — *Deadlines bound dependency calls; no cooperative cancellation of in-flight calls*
- ✅ `MC-017-T04` Classify each remote operation as safely retryable, conditionally retryable with idempotency, or non-retryable; encode this in client middleware.
- ✅ `MC-017-T05` Define bounded exponential backoff with jitter, maximum attempts/time, and retry budgets to prevent synchronized retry storms.
- ◐ `MC-017-T06` Define admission queues/backpressure, maximum queue depth, maximum age, overload rejection code, and client retry-after behavior. — *Bounded bulkhead fails fast (no queue); no Retry-After hint*
- ✅ `MC-017-T07` Define duplicate forwarding prevention for INV-63 using idempotency keys/outbox semantics.
- ✅ `MC-017-T08` Create timeout/cancellation/retry tests that inject lost responses, partial commits, duplicate requests, slow dependencies, and overload.
- ✅ `MC-017-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-017-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-017-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-017-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-017-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-017-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-017-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-017-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-017-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-017-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-017-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-017-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-018 — Protocol/version compatibility matrix and negotiation

- ◐ `MC-018-T01` Maintain a version matrix for admission, RBAC, audit, INV-64 manifest schema, GAP-13 policy API, GAP-07 provenance API, INV-63 deployment API, and supported was… — *Matrix covers INV-66 protocols/Python; GAP-13/GAP-07/INV-64/wasmCloud versions unknown here (W-004)*
- ✅ `MC-018-T02` Define minimum/maximum compatible versions and semantic differences that require translation adapters or block interoperability.
- ✅ `MC-018-T03` Implement explicit protocol negotiation or capability discovery where multiple wire versions may coexist.
- ◐ `MC-018-T04` Define rolling-upgrade rules so N and N-1 replicas do not make divergent security decisions on the same request. — *Single writer per store prevents divergent N/N-1 decisions; no mixed-version test*
- ✅ `MC-018-T05` Keep golden cross-version fixtures proving old clients can read required fields and new clients handle old responses safely.
- ☐ `MC-018-T06` Define deprecation lifecycle, telemetry for old-version use, warning period, and hard removal policy. — *Deprecation lifecycle and old-version telemetry not defined*
- ✅ `MC-018-T07` Pin dependency versions in release metadata and expose active protocol capabilities through the version/status endpoint.
- ◐ `MC-018-T08` Run the compatibility matrix in CI and block release when a claimed supported combination fails. — *Matrix defined in CI workflow; not executed on hosted runners (W-010)*
- ✅ `MC-018-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-018-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-018-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-018-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-018-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-018-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-018-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-018-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-018-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-018-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-018-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-018-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-019 — Real deployment-manager adapter

- ✅ `MC-019-T01` Implement an INV-63 client adapter behind an interface that can be replaced with test doubles without changing admission logic.
- ◐ `MC-019-T02` Define the exact INV-63 request schema, endpoint/service discovery, authentication identity, authorization capability, timeout, and TLS requirements. — *Schema/auth/timeout/TLS defined; service discovery is static URL*
- ✅ `MC-019-T03` Forward only after the authoritative admitted decision/audit record is durably committed; use transactional outbox or equivalent to avoid lost/duplicate deliver…
- ✅ `MC-019-T04` Attach admission event ID, manifest digest, tenant/lattice, desired-state revision, and idempotency key to downstream requests.
- ◐ `MC-019-T05` Define acknowledgement semantics distinguishing accepted-for-reconciliation from deployed/healthy. — *Ack = accepted-for-reconciliation; observed deployed/healthy not ingested from INV-63*
- ✅ `MC-019-T06` Handle timeout, rejection, conflict, unavailable, and duplicate acknowledgements with typed state transitions and bounded retries.
- ✅ `MC-019-T07` Persist forwarding state and last error so restart/replay resumes safely without re-authorizing a different artifact under the same request.
- ◐ `MC-019-T08` Add integration tests against a real or protocol-faithful INV-63 test service covering success, duplicate delivery, lost ack, rejection, restart, and backpressu… — *Protocol-faithful HTTP fake + crash/duplicate tests; no real INV-63 (W-004)*
- ✅ `MC-019-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-019-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-019-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-019-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-019-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-019-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-019-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-019-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-019-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-019-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-019-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-019-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-020 — Adjacent-layer integration adapters/tests

- ✅ `MC-020-T01` Create an adapter boundary and executable integration contract for INV-64 application model, GAP-13 policy engine, GAP-07 provenance/signing, identity provider,…
- ✅ `MC-020-T02` For each adapter, document ownership, request/response schema, authentication identity, timeout, retryability, consistency requirement, and failure classificati…
- ◐ `MC-020-T03` Use protocol-faithful test containers/fakes generated from the actual schema; avoid mocks that bypass serialization, authentication, or error behavior. — *Live HTTP fakes (real serialization); no real service containers (W-004)*
- ✅ `MC-020-T04` Create a dependency matrix that states which adapters are required for admission and which can degrade without violating security or durability.
- ✅ `MC-020-T05` Propagate request/trace/correlation IDs and stable tenant/workload identifiers across every adapter call.
- ◐ `MC-020-T06` Pin supported adapter/protocol versions and prove version-skew behavior. — *Policy bundle version pinned; no version-skew tests for other adapters*
- ◐ `MC-020-T07` Create end-to-end negative tests where each dependency returns malformed, stale, unauthorized, unavailable, slow, or conflicting data. — *Unavailable/malformed/version-mismatch tested for policy + deploy; not for identity/registry*
- ☐ `MC-020-T08` Add CI jobs that execute all supported adjacent-layer integrations and retain machine-readable evidence. — *No CI job against real adjacent layers (W-004, W-010)*
- ✅ `MC-020-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-020-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-020-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-020-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-020-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-020-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-020-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-020-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-020-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-020-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-020-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-020-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-021 — GitOps ingestion/change-controller integration

- ✅ `MC-021-T01` Define a GitOps source abstraction covering repository URL/project identity, branch/ref, path, commit SHA, change-set ID, author, signature status, and desired-…
- ◐ `MC-021-T02` Support secure ingestion by webhook and/or polling with authenticated source events, replay protection, and deduplication by immutable commit/change ID. — *Ingestion API with commit-scoped idempotency; no authenticated webhook receiver/poller*
- ✅ `MC-021-T03` Parse desired state using the authoritative INV-64 application model and reject ambiguous or mutable artifact references before admission.
- ✅ `MC-021-T04` Define reconciliation handoff semantics: detect new revision, validate, authorize, admit, persist, forward, and record terminal/retry state.
- ☐ `MC-021-T05` Handle force-push, branch deletion, superseded commits, revert commits, and concurrent changes deterministically. — *Force-push/branch-deletion/supersession semantics not implemented*
- ◐ `MC-021-T06` Define repository credentials as secret references and enforce least-privilege read-only access where write-back is not required. — *INV-66 never holds repository credentials (operates on a checked-out tree); least-privilege documented only*
- ◐ `MC-021-T07` Expose GitOps status linked to commit SHA, admission event, deployment-manager acknowledgement, and live inventory. — *Ingest result links commit to decisions; no persistent GitOps status endpoint*
- ◐ `MC-021-T08` Add integration tests using an actual Git server fixture for webhook replay, invalid signature, rapid successive commits, rollback commit, and repository outage… — *Filesystem change-set fixture; no real Git server/webhook replay test*
- ✅ `MC-021-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- ✅ `MC-021-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- ✅ `MC-021-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- ✅ `MC-021-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- ✅ `MC-021-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.
- ✅ `MC-021-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-021-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-021-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-021-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-021-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-021-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-021-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-022 — Declarative production configuration schema/loader

- ✅ `MC-022-T01` Define a versioned declarative configuration schema for identity, policy, RBAC store, registry/signer policy, audit store, deployment adapter, limits, telemetry…
- ✅ `MC-022-T02` Separate non-secret configuration values from secret references; prohibit inline credentials in normal config.
- ✅ `MC-022-T03` Provide secure defaults with deny-by-default trust policy, bounded limits, disabled unauthenticated admin surfaces, and explicit production-mode requirements.
- ✅ `MC-022-T04` Implement layered configuration precedence (built-in defaults < environment/site profile < deployment override) with deterministic merge semantics.
- ✅ `MC-022-T05` Validate syntax, types, ranges, endpoint schemes, duplicate/conflicting policy, and cross-field constraints before activation.
- ✅ `MC-022-T06` Reject unknown security-critical fields to prevent typo-driven bypass; define controlled forward-compatibility behavior for noncritical extensions.
- ✅ `MC-022-T07` Expose the active configuration version/digest while redacting secret references/values.
- ✅ `MC-022-T08` Add schema tests, invalid-fixture tests, and golden configuration examples for development, single-site production, and multi-site production.
- ✅ `MC-022-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-022-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-022-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-022-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-022-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-022-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-022-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-022-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-022-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-022-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-022-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-022-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-023 — Configuration provenance and version history

- ✅ `MC-023-T01` Assign every configuration revision a unique immutable ID and cryptographic digest over canonicalized non-secret content plus secret-reference identifiers.
- ✅ `MC-023-T02` Record author/principal, source system/repository, source revision/commit, approver(s), creation time, activation time, previous version, and reason/ticket.
- ✅ `MC-023-T03` Persist provenance independently of process memory and link every admission decision to the exact active configuration revision.
- ✅ `MC-023-T04` Retain historical versions for the defined audit/rollback period and prevent silent mutation of previously activated revisions.
- ✅ `MC-023-T05` Capture automated transformations/default injection so the stored effective configuration can be reproduced exactly.
- ✅ `MC-023-T06` Expose provenance through administrative query APIs with scope-aware authorization.
- ✅ `MC-023-T07` Add integrity checks that detect configuration history gaps or digest mismatch.
- ✅ `MC-023-T08` Produce release evidence showing the production config revision used for each environment/site.
- ✅ `MC-023-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-023-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-023-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-023-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-023-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-023-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-023-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-023-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-023-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-023-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-023-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-023-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-024 — Atomic configuration activation and rollback

- ◐ `MC-024-T01` Implement staged configuration lifecycle: draft -> validated -> approved -> staged -> activated, with atomic switch of the active revision. — *validate -> approved (two-person) -> atomic activate; no separate draft/staged objects*
- ✅ `MC-024-T02` Validate the complete candidate configuration and all referenced policy/secret/dependency prerequisites before changing active state.
- ✅ `MC-024-T03` Use transactional storage/CAS so partial writes across RBAC, registry/signer policy, and service settings cannot create mixed revisions.
- ✅ `MC-024-T04` Give every admission operation a consistent configuration snapshot/version so an in-flight request is not evaluated against multiple revisions.
- ◐ `MC-024-T05` Define automatic rollback triggers for activation failure and operator-driven rollback to a known prior revision. — *Operator rollback implemented; automatic rollback triggers not implemented*
- ☐ `MC-024-T06` Prevent rollback to cryptographically/semantically incompatible or revoked configuration without explicit break-glass approval. — *Rollback to a revision with revoked signers is not blocked*
- ✅ `MC-024-T07` Audit activation, rejection, rollback, and failed rollback with actor, reason, old/new digests, and correlation ID.
- ◐ `MC-024-T08` Create concurrency tests for simultaneous activations, stale-version writers, process crash mid-activation, and dependency failure during validation. — *Stale-writer (if_match) + invalid-candidate tests; no crash-mid-activation test*
- ✅ `MC-024-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-024-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-024-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-024-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-024-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-024-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-024-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-024-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-024-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-024-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-024-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-024-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-025 — Persistent RBAC/policy store

- ◐ `MC-025-T01` Select a durable RBAC/policy datastore with transactional updates, high availability, backup/restore, encryption, and supported consistency semantics. — *Persistence via journal; no separate HA RBAC datastore (W-006)*
- ✅ `MC-025-T02` Define normalized entities for organisations, tenants, principals, groups, service principals, lattices, roles/capabilities, conditions, bindings, denials, and …
- ◐ `MC-025-T03` Enforce referential integrity and uniqueness rules that prevent ambiguous duplicate grants or orphaned principals/scopes. — *Schema-level validation; no referential integrity for principals/scopes*
- ✅ `MC-025-T04` Use optimistic concurrency or serializable transactions for administrative updates; reject stale writers.
- ◐ `MC-025-T05` Support delegated administration bounded by scope and capability, never by arbitrary record-level write access. — *Scoped capabilities + escalation guard; no delegated per-tenant admin workflow*
- ✅ `MC-025-T06` Publish change events or revision tokens so all admission replicas observe a controlled, monotonic policy version.
- ✅ `MC-025-T07` Implement cache invalidation/TTL behavior that never extends revoked privilege beyond an approved maximum window.
- ◐ `MC-025-T08` Add migration, backup/restore, audit, and multi-replica consistency tests including revocation propagation. — *Backup/restore/audit tested; no multi-replica revocation-propagation test (W-006)*
- ✅ `MC-025-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-025-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-025-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-025-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-025-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-025-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-025-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-025-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-025-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-025-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-025-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-025-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-026 — Approved registry/signer policy administration store

- ✅ `MC-026-T01` Define persistent entities for approved registries, repository namespaces, signer identities/keys/certificates, allowed artifact types, environments, scopes, an…
- ◐ `MC-026-T02` Support policy conditions such as exact registry host, namespace/repository prefix, immutable digest requirement, signer key ID, issuer, certificate constraints… — *Approval = two-person rule on config revision; no separate registry/signer approval workflow*
- ◐ `MC-026-T03` Require dual control or designated approval for trust-root/signer changes in production environments. — *Distributed as config revision; no push distribution to other sites*
- ✅ `MC-026-T04` Record provenance, justification, ticket, author, approver, activation/expiry, and superseded revision for every policy change.
- ✅ `MC-026-T05` Implement atomic distribution/versioning so all admission replicas evaluate against a coherent registry/signer policy revision.
- ✅ `MC-026-T06` Handle signer/key rotation with overlap windows and explicit revocation semantics.
- ✅ `MC-026-T07` Provide a dry-run impact query showing which currently deployed/inventory artifacts would violate a proposed policy.
- ✅ `MC-026-T08` Add tests for namespace confusion, registry case/canonicalization, expired signer, revoked key, overlapping rotations, and stale replica policy.
- ✅ `MC-026-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-026-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-026-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-026-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-026-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-026-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-026-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-026-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-026-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-026-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-026-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-026-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-027 — Secret-management integration

- ◐ `MC-027-T01` Define a provider-agnostic secret-reference interface for KMS/Vault/cloud secret managers and workload identity based retrieval. — *Secret-reference model + env/file provider; no KMS/Vault client*
- ✅ `MC-027-T02` Keep secret material out of environment dumps, config files, command-line arguments, logs, traces, metrics labels, audit payloads, and crash reports.
- ✅ `MC-027-T03` Grant each service identity only the exact secret/key paths required and separate read, unwrap/sign, and administrative capabilities.
- ✅ `MC-027-T04` Define secret caching in memory, TTL, zeroization/best-effort lifecycle, renewal, and behavior when the provider is unavailable.
- ☐ `MC-027-T05` Support rotation without service restart where practical and verify old credentials stop being accepted after the overlap window. — *Rotation without restart not supported*
- ✅ `MC-027-T06` Differentiate secret references from ordinary strings in configuration schemas to prevent accidental inline values.
- ✅ `MC-027-T07` Audit secret-reference configuration changes and access failures without recording secret contents.
- ◐ `MC-027-T08` Add tests using ephemeral secret-manager fixtures for rotation, revoked access, expired lease, provider outage, and log-redaction guarantees. — *Provider unit behaviour; no ephemeral secret-manager fixture tests*
- ✅ `MC-027-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-027-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-027-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-027-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-027-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-027-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-027-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-027-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-027-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-027-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-027-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-027-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-028 — Deterministic bootstrap/install packaging

- ✅ `MC-028-T01` Add `pyproject.toml` with explicit package metadata, supported Python versions, dependency groups, entry points, and deterministic build backend configuration.
- ✅ `MC-028-T02` Pin direct dependencies and produce a lock/constraints artifact with hashes; document controlled update workflow.
- ◐ `MC-028-T03` Build a minimal production container/image or equivalent service package with non-root execution, read-only filesystem where feasible, and explicit runtime user… — *Non-root Dockerfile provided; base-image digest placeholder, image not built here (W-010)*
- ◐ `MC-028-T04` Provide reproducible build commands and record compiler/interpreter/base-image versions plus artifact digests. — *Build commands + pins recorded; no artifact digests from a real build*
- ✅ `MC-028-T05` Add service bootstrap manifests (container orchestration/system service as applicable), health checks, resource requests/limits, and required volumes/network po…
- ☐ `MC-028-T06` Provide environment bootstrap validation for DNS, certificates, storage, KMS, identity, policy, and deployment-manager reachability. — *No environment bootstrap validator for DNS/cert/KMS reachability*
- ◐ `MC-028-T07` Generate SBOM and provenance/attestation for the built artifact and sign the release artifact. — *SBOM generated; signing/provenance only in CI release job (W-010)*
- ◐ `MC-028-T08` Add CI that installs from a clean environment and proves the produced package starts and passes smoke tests without undeclared local dependencies. — *Clean-container install+test run locally; not on hosted CI (W-010)*
- ✅ `MC-028-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- ✅ `MC-028-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- ✅ `MC-028-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- ✅ `MC-028-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- ✅ `MC-028-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.
- ✅ `MC-028-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-028-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-028-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-028-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-028-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-028-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-028-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-029 — Cryptographic artifact signature verification

- ◐ `MC-029-T01` Define accepted signature formats and trust roots for Wasm/components/manifests, including signer identity binding, algorithm policy, key IDs, and certificate/a… — *Ed25519 over defined payload with key ids; no certificate/Fulcio identity binding*
- ✅ `MC-029-T02` Resolve the actual artifact bytes or immutable digest before verification; never accept a manifest `signer` string as evidence.
- ✅ `MC-029-T03` Verify signature cryptographically against the exact digest/content and enforce approved algorithm/key-size/curve requirements.
- ◐ `MC-029-T04` Validate signer authorization for tenant/environment/repository/artifact scope and validity window. — *Signer validity window enforced; signer scope per tenant/repository not modelled*
- ◐ `MC-029-T05` Check revocation/expiration and signer trust-root rotation; define offline behavior when revocation or trust services are unavailable. — *Expiry via not_after; no revocation service/transparency log (W-015)*
- ✅ `MC-029-T06` Protect against signature wrapping/substitution and canonicalization ambiguity by signing/verifying a precisely defined payload format.
- ◐ `MC-029-T07` Record verification result, signer key/cert fingerprint, algorithm, trust policy revision, and artifact digest in the admission audit event. — *Digest, signer id, errors and config revision recorded; key fingerprint/algorithm not separately recorded*
- ✅ `MC-029-T08` Add negative tests for forged signature, altered artifact, wrong key, expired/revoked cert, unapproved signer, algorithm downgrade, and replayed metadata.
- ✅ `MC-029-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-029-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-029-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-029-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-029-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-029-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-029-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-029-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-029-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-029-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-029-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-029-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-030 — Artifact digest/provenance verification

- ✅ `MC-030-T01` Require immutable artifact references by digest for production admission or resolve tags to immutable digests before policy evaluation.
- ☐ `MC-030-T02` Fetch and validate registry metadata using authenticated registry clients with tenant-scoped credentials and TLS verification. — *No authenticated registry client; digests are verified by signature, not by fetching content*
- ◐ `MC-030-T03` Verify artifact digest against downloaded/resolved content and reject digest mismatch or mutable-reference race conditions. — *Immutable digest pinning + signature over digest; content bytes not re-hashed*
- ◐ `MC-030-T04` Consume signed provenance attestations (for example SLSA/in-toto compatible) and verify builder identity, source revision, build recipe, and subject digest. — *Attestation presence + digest binding required; attestation contents (builder/source) not verified*
- ◐ `MC-030-T05` Associate SBOMs with artifact digest and enforce required SBOM/provenance presence, freshness, and policy constraints. — *SBOM/provenance presence enforced; freshness not enforced*
- ✅ `MC-030-T06` Validate approved version/channel policy without trusting unverified semantic-version labels embedded in manifests.
- ⊘ `MC-030-T07` Cache verified metadata by immutable digest with bounded lifetime and revocation invalidation. — *No metadata cache exists (nothing fetched)*
- ◐ `MC-030-T08` Add TOCTOU tests where tag contents change between resolution and forwarding, plus malformed provenance/SBOM and registry compromise simulations. — *Tags rejected (no TOCTOU window); malformed provenance covered by schema tests*
- ✅ `MC-030-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-030-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-030-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-030-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-030-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-030-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-030-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-030-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-030-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-030-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-030-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-030-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-031 — Enterprise identity federation

- ◐ `MC-031-T01` Integrate supported enterprise identity providers using OIDC/OAuth2 and/or SAML for human administrators and workload identity for services. — *JWT from OIDC IdPs + service principals; SAML must be bridged by the IdP (W-004)*
- ◐ `MC-031-T02` Define tenant/organisation discovery and claim mapping rules; prohibit arbitrary caller-controlled tenant selection without authorization. — *Tenant is request data checked by scoped RBAC; no claim-based tenant discovery*
- ✅ `MC-031-T03` Use stable immutable subject IDs plus issuer rather than mutable usernames/email addresses as authorization keys.
- ◐ `MC-031-T04` Validate token audience, issuer, signature, lifetime, authentication strength/AMR where required, and group/role claims against approved mappings. — *aud/iss/sig/lifetime/groups validated; AMR/authentication strength not enforced*
- ☐ `MC-031-T05` Define joiner/mover/leaver lifecycle, account disable propagation, group-change latency, and emergency revocation targets. — *Joiner/mover/leaver propagation targets not defined*
- ✅ `MC-031-T06` Support service principals/non-human identities with independent credentials and lifecycle controls.
- ☐ `MC-031-T07` Define session duration, refresh, step-up authentication for privileged admin operations, and break-glass accounts with enhanced audit. — *No step-up auth or break-glass accounts*
- ◐ `MC-031-T08` Add federation tests against representative identity providers and negative fixtures for tenant confusion, stale groups, token substitution, and deprovisioned u… — *Negative token fixtures; no representative IdP federation tests (W-004)*
- ✅ `MC-031-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-031-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-031-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-031-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-031-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-031-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-031-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-031-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-031-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-031-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-031-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-031-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-032 — Organisation/tenant RBAC hierarchy and capability model

- ◐ `MC-032-T01` Define hierarchy and inheritance across organisation -> tenant -> environment/site -> lattice -> workload/resource scopes. — *org > tenant > lattice; environment is per-instance; no workload-level scope*
- ✅ `MC-032-T02` Define roles as explicit capability sets; avoid hard-coded role-name checks inside decision code where capability evaluation is required.
- ◐ `MC-032-T03` Support groups, service principals, automation identities, temporary elevation, scoped delegation, and explicit deny rules. — *Groups, service principals, expiring grants, explicit deny; no temporary elevation workflow*
- ✅ `MC-032-T04` Define inheritance/override semantics and deny precedence so grants at broader scope cannot silently bypass narrower restrictions.
- ✅ `MC-032-T05` Enforce least privilege and separation of duties for policy admin, deployment, audit read, security admin, and emergency control capabilities.
- ✅ `MC-032-T06` Define privilege-escalation prevention: administrators may not grant capabilities they do not possess unless explicitly authorized by a higher-level control.
- ✅ `MC-032-T07` Provide access-review queries showing effective permissions and the complete chain of grants/denials that produced them.
- ✅ `MC-032-T08` Add property tests and adversarial tests for cross-tenant access, scope confusion, wildcard abuse, group nesting, expired grants, and delegation escalation.
- ✅ `MC-032-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-032-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-032-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-032-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-032-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-032-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-032-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-032-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-032-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-032-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-032-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-032-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-033 — External policy-engine enforcement

- ✅ `MC-033-T01` Define the GAP-13 policy decision contract including input document, policy bundle/version/digest, decision, obligations, reason codes, and evaluation metadata.
- ✅ `MC-033-T02` Pass authenticated principal, tenant/lattice/environment, artifact digest/provenance, registry/signer results, quotas, topology/site, and desired operation into…
- ✅ `MC-033-T03` Pin or record the exact policy revision used for every admission; do not permit untraceable “latest” policy during decision evaluation.
- ✅ `MC-033-T04` Define fail-closed behavior when the policy engine is unavailable for security-critical decisions and explicitly identify any safe cached-policy mode.
- ⊘ `MC-033-T05` If caching compiled policy, verify bundle signature/digest, maximum age, revocation, and deterministic evaluation equivalence. — *No compiled-policy cache (always remote or embedded rules)*
- ✅ `MC-033-T06` Prevent policy-engine responses from granting capabilities beyond the authenticated request context or bypassing non-overridable control-plane invariants.
- ✅ `MC-033-T07` Propagate policy reason/obligation data into machine-readable decisions and the operator explain view.
- ◐ `MC-033-T08` Add integration and differential tests comparing local/cached vs remote evaluation, stale policy, malformed response, engine timeout, and conflicting policy ver… — *Remote vs rule engine, malformed, version-mismatch, unavailable tested; no differential equivalence test*
- ✅ `MC-033-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-033-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-033-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-033-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-033-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-033-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-033-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-033-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-033-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-033-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-033-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-033-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-034 — Transport/storage encryption and key rotation

- ✅ `MC-034-T01` Require TLS 1.2+ or approved organisational baseline for every remote boundary and prefer mTLS for service-to-service control-plane traffic.
- ◐ `MC-034-T02` Define certificate identities, trust roots, SAN expectations, rotation cadence, revocation, and automated renewal for each service. — *TLS/mTLS wiring in CLI; certificate identities/rotation per org PKI, documented only*
- ☐ `MC-034-T03` Encrypt durable RBAC/config/audit/inventory data at rest using managed KMS keys and document envelope-encryption design where applicable. — *No application-level at-rest encryption (volume encryption required) (W-007)*
- ☐ `MC-034-T04` Separate keys by environment/tenant/data class where risk and compliance require it; restrict decrypt/sign capabilities by workload identity. — *Key separation by tenant/data class not implemented (W-007)*
- ◐ `MC-034-T05` Define key rotation and re-encryption process, overlap window, rollback, and handling of unavailable/revoked keys. — *Rotation procedure documented; no re-encryption (nothing app-encrypted)*
- ✅ `MC-034-T06` Disable insecure protocols/ciphers and enforce hostname/service-identity verification; prohibit plaintext downgrade paths.
- ☐ `MC-034-T07` Expose key/certificate expiry health signals without exposing private material. — *No certificate/key expiry health signal*
- ☐ `MC-034-T08` Add automated TLS configuration tests, expired/revoked certificate tests, wrong-service identity tests, and restore tests for encrypted backups. — *No automated TLS configuration / expired-cert tests (W-007)*
- ✅ `MC-034-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-034-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-034-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-034-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-034-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-034-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-034-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-034-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-034-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-034-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-034-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-034-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-035 — Durable tamper-evident audit anchoring

- ◐ `MC-035-T01` Persist audit records in append-only/WORM-capable storage or an append-only log whose mutation controls are stronger than the service actor. — *Append-only journal + read-only sealed segments + external WORM anchor sink; store itself is not WORM*
- ✅ `MC-035-T02` Anchor batches/segments using signed Merkle roots/hash-chain heads to an independent trust domain or transparency/timestamp service.
- ◐ `MC-035-T03` Use a dedicated audit-signing key protected by KMS/HSM with restricted signing policy and no general application read access to private key material. — *Dedicated MAC key via secret reference; not KMS/HSM-protected (W-007)*
- ✅ `MC-035-T04` Define segment rotation, checkpoint frequency, chain continuity across replicas/restarts, and immutable export verification.
- ✅ `MC-035-T05` Ensure an administrator who can modify application data cannot rewrite both records and anchors without detection.
- ◐ `MC-035-T06` Implement periodic background verification and alert on chain discontinuity, anchor mismatch, missing segment, timestamp anomaly, or verification failure. — *Periodic anchoring + /healthz chain verification + alerts; anchor verification not scheduled in loop*
- ✅ `MC-035-T07` Define recovery behavior when the audit sink/anchor is unavailable; security-sensitive operations must follow documented durability rules.
- ✅ `MC-035-T08` Create tamper tests that delete/reorder/edit/re-chain records, compromise one storage layer, replay old segments, and verify independent validation still detect…
- ✅ `MC-035-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-035-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-035-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-035-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-035-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-035-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-035-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-035-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-035-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-035-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-035-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-035-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-036 — Formal threat model

- ✅ `MC-036-T01` Create a formal threat model with assets, trust boundaries, data flows, entry points, actors, attacker capabilities, and security assumptions.
- ✅ `MC-036-T02` Cover malicious tenant/admin, compromised service identity, compromised admission replica, registry compromise, signer-key compromise, policy-engine compromise,…
- ✅ `MC-036-T03` Use STRIDE plus abuse cases/attack trees for spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege, replay, confus…
- ✅ `MC-036-T04` Identify security invariants such as “unadmitted manifests are never forwarded” and “cross-tenant data is never disclosed.”
- ✅ `MC-036-T05` Map each threat to preventative, detective, and recovery controls and to concrete test IDs.
- ◐ `MC-036-T06` Rate residual risk using the organisation’s approved methodology and create owned remediation items for unacceptable risk. — *Residuals listed; organisational risk-rating method not applied (W-002)*
- ✅ `MC-036-T07` Include boundary-specific threats for OIDC/mTLS, GitOps webhooks, registry resolution, provenance verification, policy calls, audit export, and admin APIs.
- ☐ `MC-036-T08` Review the threat model on material architecture/interface changes and before every production exit gate. — *Review before exit gate not yet held (W-002)*
- ✅ `MC-036-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-036-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-036-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-036-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-036-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-036-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-036-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-036-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-036-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-036-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-036-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-036-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-037 — Security adversarial and fuzz suite

- ◐ `MC-037-T01` Create grammar/schema-aware fuzzers for admission manifests, RBAC/admin payloads, audit query parameters, configuration documents, and any protocol decoders. — *Seeded mutation fuzzer for admission; no grammar fuzzers for admin/audit/config payloads*
- ◐ `MC-037-T02` Add property-based tests for authorization monotonicity, tenant isolation, idempotency, deterministic canonicalization, and audit-chain invariants. — *Invariant checks in fuzz; no property-based framework*
- ✅ `MC-037-T03` Build replay/spoofing tests for tokens, webhooks, idempotency keys, signed artifacts, policy responses, and downstream acknowledgements.
- ✅ `MC-037-T04` Create injection tests for JSON/string fields, log forging, path/URL parsing, registry references, Unicode confusables, and control characters.
- ✅ `MC-037-T05` Create resource-exhaustion cases: oversized/deep JSON, huge lists, compression bombs if supported, slow clients, many concurrent requests, and pathological poli…
- ✅ `MC-037-T06` Exercise privilege-escalation paths including scope confusion, wildcard roles, stale caches, race conditions, and admin API abuse.
- ☐ `MC-037-T07` Run sanitizers/static analysis/dependency scanning appropriate to implementation languages and retain crash corpora/minimized reproducers. — *No static analysis / dependency scanning executed (W-010)*
- ✅ `MC-037-T08` Gate releases on zero unresolved high-severity fuzz/security findings or a time-bounded approved waiver with compensating controls.
- ✅ `MC-037-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- ✅ `MC-037-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- ✅ `MC-037-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- ✅ `MC-037-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- ✅ `MC-037-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.
- ✅ `MC-037-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-037-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-037-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-037-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-037-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-037-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-037-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-038 — Durable state store with crash recovery/replay

- ✅ `MC-038-T01` Persist admission decisions, audit events, forwarding/outbox state, config/policy revision references, and inventory state in durable storage before acknowledgi…
- ✅ `MC-038-T02` Define transaction boundaries that prevent an admitted decision from existing without its corresponding authoritative audit/state record.
- ✅ `MC-038-T03` Implement write-ahead journal/outbox semantics for downstream forwarding and replay unfinished deliveries after restart.
- ✅ `MC-038-T04` Define snapshot/checkpoint creation and deterministic replay from log plus snapshot, including schema-version migration.
- ◐ `MC-038-T05` Use fsync/commit durability settings consistent with stated RPO; document acknowledged-loss guarantees explicitly. — *fsync per append; acknowledged-loss guarantee documented; replicated-volume RPO depends on storage (W-006)*
- ✅ `MC-038-T06` Detect and reject corrupted/incomplete journal segments rather than silently skipping them.
- ✅ `MC-038-T07` Implement startup recovery that verifies state integrity before becoming ready for traffic.
- ✅ `MC-038-T08` Add crash-point tests at every persistence/forwarding boundary and prove restart yields exactly-once logical state even when physical delivery is at-least-once.
- ✅ `MC-038-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- ✅ `MC-038-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- ✅ `MC-038-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- ✅ `MC-038-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- ◐ `MC-038-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment. — *Multi-process/fault-injection locally; no production-like environment (W-006)*
- ✅ `MC-038-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-038-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-038-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-038-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-038-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-038-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-038-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-039 — HA replication/consensus/leader election

- ✅ `MC-039-T01` Define whether admission replicas are stateless over a shared strongly consistent store or coordinate through leader/partition ownership; document the chosen co…
- ✅ `MC-039-T02` If leaders/owners exist, implement leases/epochs/fencing tokens so stale controllers cannot commit after losing ownership.
- ☐ `MC-039-T03` Define replication factor, quorum/consistency settings, placement across failure domains, and behavior during quorum loss. — *Replication factor/quorum delegated to storage; not specified or tested (W-006)*
- ✅ `MC-039-T04` Prevent duplicate forwarding and duplicate config activation across replicas using durable idempotency/outbox coordination.
- ◐ `MC-039-T05` Define read consistency for policy/config changes and maximum propagation delay for revocation-sensitive data. — *Single writer => immediate consistency within a site; cross-site propagation not defined (W-006)*
- ✅ `MC-039-T06` Define split-brain detection and safe mode; never allow both partitions to make mutually incompatible authoritative changes when consistency is required.
- ◐ `MC-039-T07` Expose leader/epoch/replica health and replication lag metrics. — *Leader/epoch exposed; no replication lag metric (W-006)*
- ◐ `MC-039-T08` Create multi-node tests for leader loss, delayed packets, asymmetric partition, clock skew, stale owner, concurrent writers, and healing after split-brain. — *Multi-process lease/fencing/race tests; no multi-node packet delay/partition/clock-skew tests (W-006)*
- ✅ `MC-039-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- ✅ `MC-039-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- ✅ `MC-039-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- ✅ `MC-039-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- ◐ `MC-039-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment. — *Multi-process on one host only (W-006)*
- ✅ `MC-039-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-039-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-039-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-039-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-039-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-039-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-039-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-040 — Dependency health and degraded-mode controller

- ✅ `MC-040-T01` Create a dependency registry describing criticality, endpoint, active protocol version, health method, timeout budget, and degraded-mode policy for each externa…
- ✅ `MC-040-T02` Implement active/passive health checks that distinguish unreachable, unauthorized, stale, overloaded, semantically unhealthy, and version-incompatible states.
- ✅ `MC-040-T03` Aggregate dependency state into readiness without marking the service ready when a security-critical dependency cannot support safe admission.
- ✅ `MC-040-T04` Define explicit degraded capabilities: e.g., audit queries available while new admissions are blocked, or cached read-only inventory while deployment forwarding…
- ☐ `MC-040-T05` Use hysteresis/debounce to prevent readiness flapping and synchronized reconnect storms. — *No hysteresis/debounce on readiness*
- ◐ `MC-040-T06` Expose last-success/last-error, latency, breaker state, and staleness age without leaking sensitive details. — *Breaker state + status per dependency; no last-success timestamps/latency per dependency*
- ◐ `MC-040-T07` Emit audit/operator events when entering or leaving degraded mode. — *Degraded transitions logged via metrics; not journalled as audit events*
- ✅ `MC-040-T08` Add tests for each dependency failing independently and correlated failures, verifying readiness and allowed operation set match policy.
- ✅ `MC-040-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- ✅ `MC-040-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- ✅ `MC-040-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- ✅ `MC-040-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- ◐ `MC-040-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment. — *Multi-process/fault-injection locally; no production-like environment (W-006)*
- ✅ `MC-040-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-040-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-040-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-040-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-040-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-040-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-040-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-041 — Bounded retry/circuit breaker/load shedding

- ✅ `MC-041-T01` Implement shared retry middleware with operation-specific policy, exponential backoff, full/equal jitter, retry budget, maximum elapsed time, and cancellation s…
- ✅ `MC-041-T02` Retry only idempotent operations or operations protected by idempotency keys/transaction IDs; document exceptions explicitly.
- ✅ `MC-041-T03` Implement circuit breakers per dependency/endpoint with closed/open/half-open states and bounded probe traffic.
- ◐ `MC-041-T04` Add concurrency and queue limits per dependency to stop slow downstreams from exhausting worker/thread/socket pools. — *Global bulkhead + per-dependency breaker; no per-dependency concurrency limit*
- ◐ `MC-041-T05` Implement load shedding before resource exhaustion and return stable overload errors plus safe retry-after hints. — *Stable OVERLOADED error; no retry-after hint*
- ✅ `MC-041-T06` Honor upstream deadlines so retries cannot exceed the caller’s end-to-end budget.
- ◐ `MC-041-T07` Export retry count, breaker transitions, shed requests, queue depth, wait time, and dependency saturation metrics. — *Shed/outcome/breaker gauges exported; no retry-count metric*
- ✅ `MC-041-T08` Create failure-injection tests for timeouts, resets, 429/503, lost acknowledgements, partial outages, and recovery without retry amplification.
- ✅ `MC-041-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- ✅ `MC-041-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- ✅ `MC-041-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- ✅ `MC-041-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- ◐ `MC-041-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment. — *Multi-process/fault-injection locally; no production-like environment (W-006)*
- ✅ `MC-041-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-041-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-041-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-041-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-041-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-041-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-041-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-042 — Quarantine/freeze/emergency-disable control

- ✅ `MC-042-T01` Implement audited administrative controls to freeze all admissions, quarantine a tenant/organisation, quarantine a lattice/site, disable forwarding, and revoke …
- ◐ `MC-042-T02` Define separate capabilities for invoking, approving, and clearing emergency controls; use dual control for high-impact production actions where required. — *Freeze capability separate from admit; no dual control for global freeze*
- ◐ `MC-042-T03` Persist emergency state durably and replicate it consistently so a restart or failover cannot silently clear the control. — *Journalled and replayed across restart/failover within a site; cross-site replication (W-006)*
- ✅ `MC-042-T04` Define precedence so emergency deny/freeze controls override ordinary allow policy and cached decisions.
- ✅ `MC-042-T05` Include reason, incident/ticket, actor, approver, activation time, expiry/TTL, scope, and recovery criteria in every action.
- ✅ `MC-042-T06` Expose current emergency state prominently through health/status and operator interfaces.
- ✅ `MC-042-T07` Define safe unfreeze procedure including policy/config refresh and verification that the unsafe condition is resolved.
- ✅ `MC-042-T08` Add tests proving quarantined scopes cannot forward while unaffected tenants remain isolated and operational as intended.
- ✅ `MC-042-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- ✅ `MC-042-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- ✅ `MC-042-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- ✅ `MC-042-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- ◐ `MC-042-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment. — *Multi-process/fault-injection locally; no production-like environment (W-006)*
- ✅ `MC-042-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-042-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-042-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-042-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-042-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-042-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-042-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-043 — Fault-injection/recovery test suite

- ✅ `MC-043-T01` Build a deterministic fault-injection harness capable of failing each dependency with timeout, connection reset, stale data, malformed response, authorization e…
- ✅ `MC-043-T02` Inject process crash/kill at persistence boundaries, config activation, audit append, outbox enqueue, forwarding send, and acknowledgement handling.
- ✅ `MC-043-T03` Test storage failure modes including disk/full quota, read-only volume, corruption, high latency, lost quorum, and restore from backup.
- ◐ `MC-043-T04` Test network partitions, asymmetric reachability, DNS failure, certificate expiry, KMS outage, and clock skew/time-service loss. — *Dependency outages + fencing tested; no DNS/cert-expiry/KMS/clock-skew injection*
- ✅ `MC-043-T05` Define expected safe state, data-loss bound, recovery-time objective, and operator signal for every fault scenario.
- ✅ `MC-043-T06` Automate recovery assertions so tests verify no unauthorized forward, no silent audit gap, no cross-tenant leakage, and no duplicate logical operation.
- ☐ `MC-043-T07` Run representative chaos tests in a production-like multi-replica environment rather than only unit-test mocks. — *No production-like multi-replica chaos environment (W-006)*
- ✅ `MC-043-T08` Retain machine-readable fault-injection results and link them to resilience requirements in the RTM.
- ✅ `MC-043-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- ✅ `MC-043-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- ✅ `MC-043-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- ✅ `MC-043-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- ◐ `MC-043-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment. — *Multi-process/fault-injection locally; no production-like environment (W-006)*
- ✅ `MC-043-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-043-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-043-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-043-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-043-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-043-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-043-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-044 — Reproducible benchmark/load/soak suite

- ✅ `MC-044-T01` Create a reproducible benchmark harness with fixed hardware/runtime metadata, dataset seeds, dependency versions, and workload profiles.
- ◐ `MC-044-T02` Measure admission end-to-end and internal-stage latency (authn, authz, policy, provenance, persistence, forwarding enqueue), throughput, CPU, RSS/heap, I/O, net… — *End-to-end latency measured; per-stage timings not broken out*
- ◐ `MC-044-T03` Cover cold start, warm steady state, burst, overload, scale-out, scale-in, dependency slowdown, restart/recovery, and multi-tenant noisy-neighbor scenarios. — *Steady, burst/overload, restart replay covered; scale-out/in and dependency slowdown not*
- ◐ `MC-044-T04` Include manifest-size/component-count distributions representative of expected production workloads plus adversarial boundary sizes. — *Single-component manifests; no size/component distribution sweep*
- ◐ `MC-044-T05` Run soak tests long enough to expose leaks, queue growth, compaction pauses, key/token refresh effects, and periodic background tasks. — *Soak mode exists; long (hours) soak not run here*
- ◐ `MC-044-T06` Record p50/p95/p99/p99.9/max and confidence/sample counts; do not report only averages. — *p50/p95/p99/max; no p99.9 or confidence intervals*
- ✅ `MC-044-T07` Publish baseline artifacts and compare new runs against an approved reference using statistical/absolute regression thresholds.
- ◐ `MC-044-T08` Automate execution in a controlled CI/performance environment and store raw results plus environment fingerprints. — *Automated in CI workflow; not executed on a controlled perf host (W-010)*
- ✅ `MC-044-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- ✅ `MC-044-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- ✅ `MC-044-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- ✅ `MC-044-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- ✅ `MC-044-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.
- ✅ `MC-044-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-044-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-044-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-044-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-044-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-044-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-044-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-045 — Performance thresholds and regression gate

- ◐ `MC-045-T01` Define explicit latency thresholds for successful admission, policy denial, authentication denial, dependency-degraded denial, and administrative operations. — *Threshold for successful admission only; denial/admin op thresholds not separate*
- ◐ `MC-045-T02` Derive a stage budget from the contract p99 <50 ms target, reserving margin for network and storage variability. — *Single end-to-end budget; stage budget not derived*
- ✅ `MC-045-T03` Define minimum sustained throughput and maximum resource cost at target load, plus overload behavior and recovery thresholds.
- ◐ `MC-045-T04` Define startup/readiness, failover, config-propagation, and revocation-propagation performance objectives where operationally relevant. — *Replay/startup budget set; failover/propagation objectives not set*
- ✅ `MC-045-T05` Use both absolute ceilings and percentage regression limits so a fast baseline cannot degrade materially while remaining under a loose maximum.
- ◐ `MC-045-T06` Gate on tail latency with sufficient sample size and stable environment; exclude warmup using documented methodology rather than cherry-picking. — *Warm-up excluded; sample size 3000; saturation p99 exceeds SLO (W-011)*
- ✅ `MC-045-T07` Create waiver workflow for intentional regressions with owner, rationale, expiry, and compensating capacity plan.
- ✅ `MC-045-T08` Publish pass/fail benchmark evidence into the release acceptance bundle.
- ✅ `MC-045-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- ◐ `MC-045-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation. — *Latency/throughput/RSS/journal bytes; no CPU/I/O breakdown*
- ✅ `MC-045-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- ✅ `MC-045-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- ✅ `MC-045-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.
- ✅ `MC-045-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-045-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-045-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-045-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-045-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-045-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-045-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-046 — Bounded audit/forwarded retention

- ✅ `MC-046-T01` Remove unbounded process-local `_audit` and `_forwarded` growth from production code paths; replace with durable bounded interfaces/projections.
- ✅ `MC-046-T02` Define audit retention tiers, hot-query window, archival policy, compaction/index lifecycle, and legal-hold exceptions.
- ✅ `MC-046-T03` Define forwarded/outbox retention by terminal acknowledgement, retry horizon, deduplication window, and incident-forensics needs.
- ✅ `MC-046-T04` Apply hard memory/queue bounds and backpressure before process memory can grow with traffic indefinitely.
- ◐ `MC-046-T05` Use streaming/paginated audit export instead of loading entire history into memory. — *Audit query paginated; export returns full retained set in one response*
- ◐ `MC-046-T06` Expose retained count/bytes, queue depth, oldest pending age, compaction lag, and storage capacity/saturation metrics. — *Head sequence, outbox depth, compactions exported; no retained-bytes/oldest-pending-age*
- ◐ `MC-046-T07` Define behavior when retention/archival sinks are full or unavailable; never silently drop security audit events. — *Store failure => fail closed (never drop); archive-sink-full behaviour not separate*
- ◐ `MC-046-T08` Add long-duration tests proving memory reaches steady state under sustained load and retention/compaction does not break audit verification. — *RSS steady-state gate in bench (short run); no multi-hour test*
- ✅ `MC-046-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- ✅ `MC-046-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- ✅ `MC-046-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- ✅ `MC-046-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- ✅ `MC-046-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.
- ✅ `MC-046-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-046-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-046-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-046-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-046-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-046-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-046-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-047 — Capacity/saturation model

- ✅ `MC-047-T01` Derive a capacity model from per-admission CPU time, memory, external-call concurrency, audit write throughput, outbox throughput, and datastore limits.
- ✅ `MC-047-T02` Model capacity by tenant count, lattices, active policies/bindings, manifest size, admission QPS, audit events/sec, inventory objects, and query load.
- ✅ `MC-047-T03` Define saturation indicators such as CPU, runnable queue, request queue depth/age, connection pool utilization, datastore latency, replication lag, breaker stat…
- ◐ `MC-047-T04` Define scale-up/out trigger thresholds with hysteresis and minimum/maximum replica bounds. — *Thresholds defined; no autoscaler (scale unit is site instance)*
- ✅ `MC-047-T05` Account for dependency bottlenecks so control-plane replicas are not scaled beyond safe identity/policy/registry/store throughput.
- ◐ `MC-047-T06` Include failure-headroom requirements (for example N+1/N+AZ-loss capacity) in sizing. — *70% headroom rule; N+1 across zones depends on W-006*
- ✅ `MC-047-T07` Validate the model using measured benchmark data and document known nonlinearities.
- ✅ `MC-047-T08` Create an operator capacity dashboard and runbook mapping saturation signals to scaling/remediation actions.
- ✅ `MC-047-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- ✅ `MC-047-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- ✅ `MC-047-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- ✅ `MC-047-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- ✅ `MC-047-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.
- ✅ `MC-047-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-047-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-047-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-047-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-047-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-047-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-047-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-048 — Edge power/thermal characterization

- ✅ `MC-048-T01` Determine whether INV-66 is ever deployed on constrained near/far-edge nodes; if not, document C068 as not applicable with architecture approval.
- ⊘ `MC-048-T02` If applicable, define representative hardware classes, ambient/thermal conditions, power modes, and baseline idle/load measurements. — *C068 not applicable (W-012)*
- ⊘ `MC-048-T03` Measure incremental CPU package/system power, energy per admission, memory pressure, storage I/O, and thermal throttling under representative loads. — *C068 not applicable (W-012)*
- ⊘ `MC-048-T04` Measure cold-start and reconnect behavior under battery/power-saving modes where relevant. — *C068 not applicable (W-012)*
- ⊘ `MC-048-T05` Define power/thermal budgets and overload/thermal-throttling behavior that preserves security semantics. — *C068 not applicable (W-012)*
- ⊘ `MC-048-T06` Compare local admission vs remote-control-plane architecture to quantify energy/network tradeoffs for disconnected sites. — *C068 not applicable (W-012)*
- ⊘ `MC-048-T07` Record measurement tooling, calibration, sampling period, and environmental conditions for reproducibility. — *C068 not applicable (W-012)*
- ✅ `MC-048-T08` Add the resulting applicability decision or benchmark evidence to the production acceptance bundle.
- ✅ `MC-048-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- ✅ `MC-048-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- ✅ `MC-048-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- ✅ `MC-048-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- ✅ `MC-048-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.
- ✅ `MC-048-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-048-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-048-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-048-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-048-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-048-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-048-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-049 — Health/readiness/version/config/dependency endpoint

- ◐ `MC-049-T01` Implement unauthenticated-minimal liveness and authenticated/appropriately exposed readiness/status endpoints with clearly separated semantics. — *Health/ready/version/metrics are unauthenticated-minimal; must be bound to the ops network*
- ✅ `MC-049-T02` Report service build/version, protocol versions, active config/policy revision digests, feature/capability set, replica/site identity, and start time.
- ✅ `MC-049-T03` Report dependency health for identity, policy, provenance/registry, audit store, config/RBAC store, deployment manager, KMS, and telemetry/export sinks.
- ✅ `MC-049-T04` Include degraded-mode flags, emergency freeze/quarantine status, replication/leader state if applicable, and last successful authoritative write.
- ✅ `MC-049-T05` Keep readiness fail-closed when the service cannot safely admit/record/forward according to production requirements.
- ✅ `MC-049-T06` Bound endpoint latency and output size; do not perform unbounded dependency fan-out per scrape.
- ✅ `MC-049-T07` Redact secrets, tokens, internal credentials, and cross-tenant data; expose only operator-safe diagnostic metadata.
- ✅ `MC-049-T08` Add conformance tests for healthy, degraded, dependency-failed, stale-config, audit-store-failed, and emergency-freeze states.
- ✅ `MC-049-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- ✅ `MC-049-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- ✅ `MC-049-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- ✅ `MC-049-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- ✅ `MC-049-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.
- ✅ `MC-049-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-049-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-049-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-049-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-049-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-049-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-049-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-050 — Metrics instrumentation/export

- ✅ `MC-050-T01` Instrument request counters by operation/outcome/reason class, authorization denials, policy denials, provenance failures, audit appends, forwarding outcomes, r…
- ◐ `MC-050-T02` Instrument histograms for end-to-end admission and each major stage, using buckets appropriate to the <50 ms p99 target. — *End-to-end histogram; no per-stage histograms*
- ◐ `MC-050-T03` Export gauges for in-flight requests, queue depth/age, outbox backlog, policy/config age, cache size/hit ratio, replication lag, and dependency breaker state. — *In-flight, outbox, head, freezes, leader, breakers; no cache hit ratio/config age*
- ☐ `MC-050-T04` Export process/runtime CPU, memory, GC, file descriptor/socket, thread/task, network, and storage metrics. — *No process/runtime metrics exporter*
- ✅ `MC-050-T05` Use OpenTelemetry/Prometheus-compatible naming, units, descriptions, and stable semantic conventions.
- ✅ `MC-050-T06` Control label cardinality: tenant/workload identifiers must not be unbounded default labels; use exemplars/log correlation for high-cardinality detail.
- ◐ `MC-050-T07` Add metric schema/version tests and dashboard queries that fail visibly if required series disappear. — *Tests assert required series exist; no dashboard-query CI*
- ◐ `MC-050-T08` Validate instrumentation overhead under benchmark load and ensure metrics export failure cannot block admission. — *Overhead included in bench; export failure isolation not tested*
- ✅ `MC-050-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- ✅ `MC-050-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- ✅ `MC-050-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- ✅ `MC-050-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- ✅ `MC-050-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.
- ✅ `MC-050-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-050-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-050-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-050-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-050-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-050-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-050-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-051 — Structured operational logging

- ✅ `MC-051-T01` Define a structured JSON/log schema with timestamp, severity, event name, service/version, site/replica, request ID, trace/span ID, tenant/lattice/workload IDs,…
- ✅ `MC-051-T02` Use explicit event IDs rather than free-form-only messages for security and operational state transitions.
- ✅ `MC-051-T03` Create redaction rules for tokens, secrets, headers, manifest sensitive fields, repository credentials, and PII; default to omission rather than masking unknown…
- ✅ `MC-051-T04` Prevent log forging by structured encoding and sanitizing embedded control characters/newlines from untrusted fields.
- ◐ `MC-051-T05` Define sampling rules that never sample away required security/audit events while controlling high-volume success logs. — *Level threshold only; no sampling (so nothing security-relevant is dropped)*
- ◐ `MC-051-T06` Route logs to approved sinks with buffering/backpressure that cannot exhaust application memory. — *stderr JSON lines to the platform collector; no in-process buffering*
- ✅ `MC-051-T07` Include enough correlation to reconstruct an admission across authn, policy, provenance, persistence, and forwarding without logging entire sensitive payloads.
- ✅ `MC-051-T08` Add tests that inspect emitted logs for required fields, tenant isolation, secret absence, bounded field lengths, and malformed-input safety.
- ✅ `MC-051-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- ✅ `MC-051-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- ✅ `MC-051-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- ✅ `MC-051-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- ✅ `MC-051-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.
- ✅ `MC-051-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-051-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-051-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-051-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-051-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-051-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-051-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-052 — Distributed tracing/context propagation

- ✅ `MC-052-T01` Adopt W3C Trace Context/OpenTelemetry or organisational standard and propagate trace/span context through admission, identity, policy, provenance/registry, stor…
- ◐ `MC-052-T02` Create spans for major stages with stable names and attributes such as outcome/reason class, dependency, protocol version, and bounded manifest metadata. — *One span per admission logged with trace/span id; no per-stage spans or OTel exporter*
- ✅ `MC-052-T03` Never attach tokens, full manifests, secrets, or unbounded/high-cardinality payloads to spans.
- ✅ `MC-052-T04` Propagate baggage only for explicitly approved low-cardinality context; do not use baggage as an authorization source.
- ◐ `MC-052-T05` Link asynchronous outbox/forwarding spans to the originating admission trace/event using span links or persisted correlation IDs. — *Outbox delivery reuses decision trace id; no explicit span links*
- ◐ `MC-052-T06` Define trace sampling that keeps errors/security denials at adequate rates while controlling ordinary high-volume traffic. — *Sampling policy documented; no sampler in code*
- ✅ `MC-052-T07` Export trace IDs in structured logs and audit metadata where policy permits correlation.
- ◐ `MC-052-T08` Add integration tests proving context survives each protocol boundary and is not trusted when supplied by unauthenticated callers. — *Propagation tested to policy/deploy adapters; untrusted-context handling = new span id only*
- ✅ `MC-052-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- ✅ `MC-052-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- ✅ `MC-052-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- ✅ `MC-052-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- ✅ `MC-052-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.
- ✅ `MC-052-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-052-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-052-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-052-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-052-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-052-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-052-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-053 — Decision explainability/policy linkage view

- ✅ `MC-053-T01` Define an explain record keyed by admission/audit event ID that links authenticated principal, requested operation, tenant/lattice/workload, manifest/artifact d…
- ◐ `MC-053-T02` Capture exact RBAC bindings/capabilities and policy bundle/config revision that were evaluated, including deny/allow precedence. — *Config revision/digest + policy version + errors; matched RBAC bindings not captured per decision (access_review gives current chain)*
- ✅ `MC-053-T03` Capture registry/signer/provenance checks with immutable digest and verifier result, without exposing secrets or unnecessary certificate content.
- ✅ `MC-053-T04` Capture quota/capacity decisions, dependency/degraded state, topology/site constraints, and forwarding disposition.
- ◐ `MC-053-T05` Provide a bounded operator query/view that renders machine reason codes into a human-readable decision tree while retaining raw structured evidence. — *Machine-readable explain; no human-rendered decision tree UI*
- ✅ `MC-053-T06` Enforce tenant/scope-aware authorization for explain data because it may reveal policy and infrastructure metadata.
- ✅ `MC-053-T07` Make explain data immutable or derived from immutable audit/event state so retrospective explanations cannot drift after policy changes.
- ✅ `MC-053-T08` Add tests verifying every denial and admission can be explained completely and the explanation references the exact versions used at decision time.
- ✅ `MC-053-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- ✅ `MC-053-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- ✅ `MC-053-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- ✅ `MC-053-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- ✅ `MC-053-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.
- ✅ `MC-053-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-053-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-053-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-053-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-053-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-053-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-053-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-054 — Telemetry retention/privacy/export policy and dashboards/alerts

- ✅ `MC-054-T01` Classify telemetry by data sensitivity and define retention periods separately for metrics, logs, traces, audit events, and explain/inventory data.
- ✅ `MC-054-T02` Define tenant/PII handling, hashing/pseudonymization, permitted attributes, geographic residency, and access controls for telemetry backends.
- ✅ `MC-054-T03` Define sampling rules for traces/logs and guarantee required security/audit evidence is not sampled away.
- ◐ `MC-054-T04` Configure export buffering, retry, disk spool limits, and drop policy so telemetry outages cannot cause unbounded resource growth or silently discard mandated a… — *Bounded in-process telemetry; export spooling belongs to the collector*
- ✅ `MC-054-T05` Create dashboards for admission volume/latency, denials by class, dependency health, audit/outbox backlog, saturation, policy/config revision, and emergency sta…
- ✅ `MC-054-T06` Create alerts that distinguish capacity load, dependency degradation, policy rejection spikes, authentication attack signals, audit-integrity failure, and softw…
- ✅ `MC-054-T07` Define alert thresholds, routing, severity, deduplication, runbook links, and SLO burn-rate alerts.
- ☐ `MC-054-T08` Periodically test dashboard queries and synthetic alerts in CI/staging to detect observability drift. — *No synthetic alert/dashboard tests*
- ✅ `MC-054-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- ✅ `MC-054-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- ✅ `MC-054-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- ✅ `MC-054-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- ✅ `MC-054-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.
- ✅ `MC-054-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-054-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-054-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-054-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-054-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-054-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-054-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-055 — Public-interface contract test suite

- ✅ `MC-055-T01` Generate contract tests directly from the published admission, RBAC, audit, status, and administrative schemas.
- ✅ `MC-055-T02` Test every required field, optional field, boundary size/count, enum, version, unknown-field rule, and canonicalization constraint.
- ✅ `MC-055-T03` Include authorization matrices proving each operation denies principals missing required capability/scope.
- ✅ `MC-055-T04` Include stable error-code assertions for validation, authn/authz, conflict, quota, timeout, dependency, overload, and internal failures.
- ◐ `MC-055-T05` Run the same fixtures against in-process handlers and deployed service endpoints to detect adapter/serialization drift. — *Same fixtures in-process; HTTP endpoint tests use separate cases*
- ✅ `MC-055-T06` Maintain golden compatibility fixtures for supported older protocol versions.
- ✅ `MC-055-T07` Include malformed-wire and truncated-message cases rather than testing only deserialized application objects.
- ✅ `MC-055-T08` Publish machine-readable contract-test results and fail release on any externally claimed interface mismatch.
- ✅ `MC-055-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-055-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-055-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-055-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-055-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-055-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-055-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-055-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-055-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-055-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-055-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-055-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-056 — End-to-end integration suite

- ☐ `MC-056-T01` Stand up an end-to-end test environment containing a real/test identity provider, GAP-13 policy engine, registry, GAP-07 provenance verifier, durable stores, IN… — *No E2E environment with real dependencies (W-004)*
- ◐ `MC-056-T02` Exercise the entire path from authenticated GitOps/API request through admission, durable audit, downstream forwarding, reconciliation acknowledgement, and inve… — *GitOps->admission->journal->HTTP deploy fake->ack path tested in-process*
- ✅ `MC-056-T03` Verify a policy/registry/signer/RBAC denial never reaches the deployment manager and produces complete audit/explain evidence.
- ✅ `MC-056-T04` Verify admitted artifacts are identified by immutable digest and the same digest reaches the downstream deployment path.
- ◐ `MC-056-T05` Inject each adjacent dependency failure and assert documented degraded/fail-closed behavior. — *Policy/deploy/store failures injected; not every dependency*
- ◐ `MC-056-T06` Exercise configuration/RBAC/signer rotation and prove new revisions propagate without inconsistent mixed decisions. — *Config/signer rotation via revisions tested; not under concurrent load*
- ◐ `MC-056-T07` Run tenant-isolation scenarios with at least two organisations/tenants/lattices concurrently. — *Two tenants isolation tested; not two organisations concurrently*
- ◐ `MC-056-T08` Retain service logs/traces/audit exports plus machine test results as release evidence. — *Machine results retained; no service logs/traces bundle from E2E env*
- ✅ `MC-056-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-056-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-056-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-056-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-056-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-056-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-056-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-056-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-056-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-056-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-056-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-056-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-057 — Compatibility/platform test matrix

- ✅ `MC-057-T01` Define the supported matrix for Python/runtime versions, OS distributions, CPU architectures, container runtime/orchestrator, wasmCloud/Cosmonic versions, and a…
- ✅ `MC-057-T02` Classify combinations as fully supported, limited/experimental, or explicitly unsupported; do not imply support from untested portability.
- ☐ `MC-057-T03` Run unit/contract/integration smoke tests on every supported baseline combination in CI. — *Matrix not executed (W-010)*
- ☐ `MC-057-T04` Include at least the architectures/sites actually used in production, including ARM64 if edge deployments depend on it. — *arm64 not executed (W-010)*
- ☐ `MC-057-T05` Validate TLS/crypto/provider behavior across platforms where library/backend differences can affect security. — *Cross-platform crypto not validated (W-010)*
- ☐ `MC-057-T06` Run schema/protocol compatibility tests across N/N-1 rolling upgrade combinations. — *No N/N-1 rolling tests*
- ◐ `MC-057-T07` Record matrix results and exact dependency versions in release metadata. — *Local run versions recorded in evidence*
- ◐ `MC-057-T08` Block publication of a support claim when its matrix job is missing, skipped, or failing. — *CI job fails on skips; not yet running*
- ✅ `MC-057-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-057-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-057-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-057-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-057-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-057-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-057-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-057-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-057-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-057-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-057-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-057-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-058 — Distributed concurrency/race suite

- ◐ `MC-058-T01` Build multi-process/multi-node tests against the real durable coordination/store layer rather than only Python threads. — *Multi-process against real file store; no multi-node*
- ✅ `MC-058-T02` Test concurrent admissions for the same idempotency key, same manifest, different tenants, and conflicting policy/config revisions.
- ◐ `MC-058-T03` Test concurrent RBAC/config mutations with stale revision tokens and verify one deterministic outcome without lost updates. — *Stale-writer rejection tested sequentially; not concurrently*
- ✅ `MC-058-T04` Test leader failover/lease expiry/fencing where applicable, including delayed stale leader writes after failover.
- ✅ `MC-058-T05` Test duplicate downstream sends, lost acknowledgements, outbox replay, and deduplication across process restart.
- ◐ `MC-058-T06` Test concurrent audit appends/query/export and preserve global/partition ordering guarantees as specified. — *Concurrent appends tested; concurrent query/export not*
- ◐ `MC-058-T07` Use stress/race tooling and repeated randomized scheduling to increase probability of exposing timing defects. — *Repeated multi-process contention; no randomized scheduler/race tooling*
- ✅ `MC-058-T08` Assert invariants automatically: no unauthorized forward, no duplicate logical transition, no audit gap, no cross-tenant state leak.
- ✅ `MC-058-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-058-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-058-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-058-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-058-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-058-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-058-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-058-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-058-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-058-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-058-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-058-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-059 — Disaster/partition/reconnect certification suite

- ◐ `MC-059-T01` Define certified recovery scenarios for process/node loss, datastore replica loss, zone/site loss, network partition, dependency region loss, and complete contr… — *Process loss, store corruption, restore covered; site/zone/region loss not (W-006)*
- ◐ `MC-059-T02` Specify RTO/RPO and acceptable degraded capabilities for each scenario. — *RPO/RTO targets stated for restore only*
- ✅ `MC-059-T03` Test backup restore into clean infrastructure and verify audit chain, policy/config revisions, RBAC, inventory, and pending outbox state.
- ☐ `MC-059-T04` Test site partition where local control continues only within documented leases/staleness limits, then reconcile deterministically on reconnect. — *No site partition test (W-006)*
- ◐ `MC-059-T05` Test DNS/time/KMS/identity/policy outages and recovery sequencing without security bypass. — *Policy outage tested; DNS/time/KMS/identity outages not*
- ✅ `MC-059-T06` Test stale controller and duplicate event conditions after reconnect/failover.
- ☐ `MC-059-T07` Validate operator runbooks by having a separate operator execute them from documented instructions rather than test-author knowledge. — *Runbooks not executed by a separate operator (W-014)*
- ◐ `MC-059-T08` Produce signed/machine-readable disaster-test evidence with timestamps, environment build, achieved RTO/RPO, and any deviations. — *Machine-readable DR test results; not signed, no achieved RTO/RPO measured*
- ✅ `MC-059-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-059-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-059-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-059-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-059-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-059-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-059-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-059-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-059-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-059-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-059-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-059-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-060 — Full machine-readable production acceptance evidence bundle

- ✅ `MC-060-T01` Define a versioned acceptance-evidence schema covering all C001-C100 items and MC closure status.
- ✅ `MC-060-T02` For each control, include status, evidence type, artifact URI/path, cryptographic digest, test/run ID, environment, timestamp, tool version, and responsible own…
- ✅ `MC-060-T03` Distinguish PASS, FAIL, NOT_APPLICABLE, WAIVED, and BLOCKED states; require rationale/approval/expiry for non-PASS dispositions.
- ◐ `MC-060-T04` Generate evidence automatically from CI, security scans, benchmarks, compatibility matrix, chaos/disaster tests, and documentation checks where possible. — *Generated from local test/bench/doc checks; no security scans/matrix inputs yet (W-010)*
- ☐ `MC-060-T05` Include `pk_core` conformance evidence or vendor the required runtime so production certification cannot silently skip unavailable tests. — *pk_core not vendored/available (W-003)*
- ◐ `MC-060-T06` Chain/sign the evidence bundle or include it in signed release provenance to prevent post-release editing. — *Evidence bundle digested + HMAC-sealed when a release key is provided; not in signed provenance yet*
- ✅ `MC-060-T07` Validate that every normative SHALL and every C001-C100 control is covered before producing a production gate result.
- ✅ `MC-060-T08` Archive evidence per release with enough environment metadata to reproduce or investigate the result.
- ✅ `MC-060-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-060-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-060-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-060-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-060-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-060-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-060-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-060-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-060-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-060-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-060-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-060-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-061 — CI/CD release pipeline and staged rollout artifacts

- ✅ `MC-061-T01` Create CI stages for lint/static analysis, unit/property/fuzz tests, schema/contract tests, integration tests, security scans, SBOM/provenance, compatibility ma…
- ☐ `MC-061-T02` Build release artifacts from a clean, pinned environment and sign/attest them; never promote locally built untracked binaries. — *No signed build produced (W-010)*
- ✅ `MC-061-T03` Define environment promotion dev -> test -> staging -> canary -> production with immutable artifact digests.
- ◐ `MC-061-T04` Implement staged/canary rollout using health/SLO/security signals and automatic halt/rollback thresholds. — *Rollout plan with checks; no automation executing it*
- ✅ `MC-061-T05` Pin deployment manifests/config schema versions and record exact config/policy revisions per rollout.
- ◐ `MC-061-T06` Implement automated rollback that restores the prior known-good artifact/config without bypassing audit or authorization. — *Rollback procedure + config rollback API; not automated*
- ☐ `MC-061-T07` Require protected-branch/code-owner approvals and production release authorization by designated roles. — *Branch protection/CODEOWNERS need named owners (W-001)*
- ✅ `MC-061-T08` Emit machine-readable pipeline/release metadata into the acceptance evidence bundle.
- ✅ `MC-061-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-061-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-061-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-061-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-061-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-061-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-061-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-061-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-061-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-061-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-061-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-061-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-062 — Vulnerability/SBOM/patch/EOL program artifacts

- ✅ `MC-062-T01` Generate SPDX or CycloneDX SBOMs for application dependencies, base image/OS packages, and bundled tools for every release artifact.
- ☐ `MC-062-T02` Run SCA/vulnerability scanning with an approved severity/EPSS/exploitability policy and fail builds according to defined thresholds. — *No vulnerability scanner executed (W-010)*
- ✅ `MC-062-T03` Define patch SLAs by severity and exposure, including emergency out-of-band release procedures for actively exploited vulnerabilities.
- ✅ `MC-062-T04` Track supported release branches, minimum dependency versions, end-of-standard-support, and end-of-life dates.
- ☐ `MC-062-T05` Monitor new CVEs continuously against released SBOMs, not only at build time. — *No continuous CVE monitoring*
- ✅ `MC-062-T06` Define exception/false-positive workflow with owner, technical rationale, compensating control, expiry, and re-evaluation.
- ◐ `MC-062-T07` Include license/third-party notice compliance scanning and provenance verification in dependency update workflows. — *License gate in tools/sbom.py; no provenance verification of dependency updates*
- ✅ `MC-062-T08` Publish vulnerability/SBOM status and unresolved approved exceptions into release evidence.
- ✅ `MC-062-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-062-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-062-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-062-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-062-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-062-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-062-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-062-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-062-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-062-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-062-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-062-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-063 — Backup/restore/migration/reconstruction runbook

- ✅ `MC-063-T01` Inventory every durable dataset: audit/event log, RBAC/policy data, registry/signer policy, configuration history, inventory projections, outbox/pending operati…
- ✅ `MC-063-T02` Define backup frequency, retention, encryption, immutability, geographic location, RPO/RTO, and dependency ordering for each dataset.
- ◐ `MC-063-T03` Implement automated backups with success/failure monitoring and independent verification that backup objects are readable and complete. — *Backup tool + verification; scheduling/monitoring left to ops platform*
- ✅ `MC-063-T04` Document restore sequencing, including keys/certificates, datastore schemas, snapshots/log replay, config activation, and dependency reattachment.
- ◐ `MC-063-T05` Define schema migration forward/backward compatibility and rollback strategy for persisted data. — *Replay-based migration strategy documented; no second format exists yet*
- ✅ `MC-063-T06` Provide reconstruction procedure from authoritative event log when projections/indexes are lost.
- ◐ `MC-063-T07` Perform periodic clean-room restore tests and verify audit integrity plus pending/idempotency state after recovery. — *Automated clean-directory restore test; no periodic clean-room drill yet (W-014)*
- ◐ `MC-063-T08` Record backup/restore test evidence, achieved RPO/RTO, and operator sign-off. — *Test evidence recorded; no operator sign-off or achieved RTO (W-014)*
- ✅ `MC-063-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-063-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-063-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-063-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-063-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-063-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-063-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-063-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-063-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-063-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-063-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-063-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-064 — Complete day-0/day-1/day-2 operational runbooks

- ✅ `MC-064-T01` Create Day-0 runbook for infrastructure prerequisites, IAM/service identities, certificates, KMS/secrets, stores, DNS/network policy, installation, bootstrap co…
- ✅ `MC-064-T02` Create Day-1 runbook for deployment, smoke validation, staged rollout, config/policy activation, initial RBAC/registry/signer setup, and production readiness ve…
- ✅ `MC-064-T03` Create Day-2 runbooks for upgrades, scaling, certificate/key rotation, policy changes, tenant onboarding/offboarding, capacity management, backup verification, …
- ✅ `MC-064-T04` Add troubleshooting procedures keyed to stable error codes, alerts, dependency health states, and common failure signatures.
- ✅ `MC-064-T05` Include explicit commands/API examples with expected outputs and safety checks; avoid destructive commands without preconditions/rollback.
- ✅ `MC-064-T06` Include rollback and emergency freeze/quarantine procedures, plus criteria for resuming normal operation.
- ✅ `MC-064-T07` Link every alert/dashboard to the relevant runbook section and owner/escalation route.
- ☐ `MC-064-T08` Test runbooks during game days and update them from observed operator gaps. — *No game day held (W-014)*
- ✅ `MC-064-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-064-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-064-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-064-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-064-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-064-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-064-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-064-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-064-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-064-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-064-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-064-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-065 — Incident response/on-call runbook

- ✅ `MC-065-T01` Define incident severity levels using customer/security/data-integrity/availability impact and examples specific to unauthorized forwarding, audit integrity fai…
- ◐ `MC-065-T02` Define paging targets, primary/secondary rotations, acknowledgement/escalation timers, and dependency-team engagement paths. — *Ack/escalation timers defined; rotations need names (W-001)*
- ✅ `MC-065-T03` Create containment playbooks for global admission freeze, tenant/lattice quarantine, signer/registry revocation, credential rotation, and deployment forwarding …
- ✅ `MC-065-T04` Define evidence-preservation steps for audit anchors, logs, traces, config/policy snapshots, identity records, and affected artifact digests.
- ✅ `MC-065-T05` Define recovery criteria and required verification before clearing emergency controls or returning to normal traffic.
- ✅ `MC-065-T06` Define communications roles/channels, customer/compliance notification decision process, and status cadence.
- ✅ `MC-065-T07` Require post-incident review with root cause, control failures, corrective actions, owners, due dates, and threat-model/runbook updates.
- ☐ `MC-065-T08` Exercise the runbook with tabletop and live game-day scenarios at a scheduled cadence. — *No tabletop/game day held (W-014)*
- ✅ `MC-065-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-065-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-065-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-065-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-065-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-065-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-065-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-065-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-065-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-065-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-065-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-065-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-066 — Recurring review automation/evidence

- ✅ `MC-066-T01` Define review frequencies and owners for access/RBAC, elevated grants, break-glass accounts, registry/signer trust, policy bundles, dependencies, config drift, …
- ✅ `MC-066-T02` Automate extraction of current state and diffs so reviewers assess effective configuration rather than manually assembled screenshots.
- ✅ `MC-066-T03` Flag stale/unused privileges, expired temporary grants, unknown signers/registries, old protocol versions, unsupported dependencies, and unowned exceptions.
- ◐ `MC-066-T04` Require reviewer disposition, remediation owner, due date, and evidence for every finding. — *Findings carry severity + remediation hint; reviewer disposition captured manually*
- ✅ `MC-066-T05` Retain immutable review results and link material findings to tickets/waivers/incidents.
- ✅ `MC-066-T06` Escalate overdue critical findings and block production exit when required recurring reviews are stale.
- ◐ `MC-066-T07` Add review status to governance dashboards and acceptance evidence. — *Review status in evidence bundle; no governance dashboard*
- ☐ `MC-066-T08` Periodically validate the automation itself against source systems to detect blind spots or partial data extraction. — *Automation not validated against source systems*
- ✅ `MC-066-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-066-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-066-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-066-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-066-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-066-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-066-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-066-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-066-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-066-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-066-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-066-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-067 — Exception/waiver/technical-debt register

- ✅ `MC-067-T01` Create a machine-readable register with unique waiver/debt ID, affected requirement/control, scope/environment, owner, approver, rationale, risk rating, compens…
- ◐ `MC-067-T02` Prohibit indefinite waivers; require explicit expiry/review date and automated notification before expiration. — *Expiry required and checked; no notification channel*
- ✅ `MC-067-T03` Differentiate temporary security exceptions, functional limitations, technical debt, and deprecation commitments.
- ✅ `MC-067-T04` Link each register entry to RTM rows and production gate results so waived controls cannot appear as ordinary PASS.
- ✅ `MC-067-T05` Block release on expired waivers or waivers missing required approval for their risk level.
- ☐ `MC-067-T06` Provide trend reporting for open/aging debt and repeated extensions. — *No trend reporting*
- ✅ `MC-067-T07` Require closure evidence demonstrating the underlying control is implemented and verified before marking a waiver resolved.
- ✅ `MC-067-T08` Archive historical entries without deleting their relationship to prior releases.
- ✅ `MC-067-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-067-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-067-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-067-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-067-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-067-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-067-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-067-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-067-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-067-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-067-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-067-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-068 — Formal production exit gate artifact

- ✅ `MC-068-T01` Define a signed/generated production exit-gate schema with independent sections for architecture, requirements, interfaces, implementation/config, security, res…
- ✅ `MC-068-T02` Require every C001-C100 item to resolve to PASS, approved NOT_APPLICABLE, or unexpired approved waiver; BLOCKED/FAIL prevents production GO.
- ✅ `MC-068-T03` Consume evidence from the RTM/acceptance bundle by immutable digest rather than manually copying status into a report.
- ☐ `MC-068-T04` Require named approvals from service owner, architecture, security, SRE/operations, and release authority according to organisational policy. — *Named approvals cannot be recorded until owners are named (W-001, W-002)*
- ✅ `MC-068-T05` Include exact artifact digest, source revision, deployment manifest version, config/policy revision, compatibility matrix, and evidence-bundle digest.
- ✅ `MC-068-T06` Automate objective checks and isolate subjective approvals so humans cannot override missing machine evidence without a formal waiver.
- ✅ `MC-068-T07` Generate a reproducible gate report with timestamp and decision inputs and retain it with the release.
- ◐ `MC-068-T08` Prevent deployment/promotion automation from bypassing a non-GO gate except through an explicitly audited break-glass process. — *CI release job requires GO; no deployment automation to bind yet*
- ✅ `MC-068-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-068-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-068-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-068-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-068-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-068-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-068-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-068-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-068-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-068-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-068-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-068-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-069 — Cross-lattice inventory service

- ✅ `MC-069-T01` Define a durable cross-lattice inventory model with organisation/tenant, site, lattice, workload/application, component/provider, artifact digest, desired revis…
- ◐ `MC-069-T02` Distinguish desired/admitted state from downstream observed runtime state; record source and freshness for each field. — *Admitted/lifecycle state recorded; observed runtime state not ingested*
- ☐ `MC-069-T03` Ingest updates from INV-63/wasmCloud reconciliation using authenticated event/query mechanisms with idempotent versioned updates. — *No ingestion from INV-63 reconciliation events (W-004)*
- ◐ `MC-069-T04` Provide scoped query APIs for tenant/lattice/workload/artifact/revision and pagination suitable for large fleets. — *Tenant/lattice filters; no artifact/revision filter or pagination*
- ✅ `MC-069-T05` Enforce tenant isolation and administrative scope on inventory reads; avoid global inventory disclosure by default.
- ◐ `MC-069-T06` Define stale/offline semantics and last-observed timestamps for disconnected sites. — *as_of_sequence given; no per-site last-observed timestamps*
- ✅ `MC-069-T07` Correlate inventory entries with admission event, GitOps commit, policy/config revision, and deployment acknowledgement.
- ◐ `MC-069-T08` Add reconciliation tests for out-of-order/duplicate updates, site reconnect, deletion/tombstone, drift, and projection rebuild from source events. — *Rollback removal + replay tested; no out-of-order observed-state tests*
- ✅ `MC-069-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-069-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-069-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-069-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-069-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-069-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-069-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-069-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-069-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-069-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-069-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-069-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-070 — Audit query/retention/export service

- ◐ `MC-070-T01` Implement durable indexed audit storage and a read/query service independent from the in-process `audit` snapshot. — *Durable journal + query API; linear scan, no secondary index*
- ◐ `MC-070-T02` Define retention classes by event type/tenant/regulatory need, hot vs archive tiers, legal hold, and immutable deletion governance. — *Hot journal/archive tiers + legal hold on purge; retention classes by event type not separate*
- ◐ `MC-070-T03` Index common dimensions such as time, tenant, lattice, principal, workload, action/outcome, request/trace ID, artifact digest, and event ID while controlling co… — *Filters: sequence, kind, tenant; no time/principal/digest index*
- ◐ `MC-070-T04` Provide cursor-based pagination and bounded query ranges; protect service with authorization, rate limits, and query-cost controls. — *Cursor pagination + limit + authz; no query-cost controls*
- ✅ `MC-070-T05` Provide cryptographically verifiable export bundles including event segment roots/anchors, schema version, and manifest digest.
- ☐ `MC-070-T06` Implement SIEM/security-lake export with durable checkpointing, idempotent delivery, retries, backpressure, and dead-letter visibility. — *No SIEM connector (W-013)*
- ✅ `MC-070-T07` Ensure retention/archival operations preserve tamper-evident chain/anchor verification and legal-hold records.
- ◐ `MC-070-T08` Add tests for large-range queries, tenant access control, archived retrieval, export verification, SIEM outage/recovery, and restore from backup. — *Access control, archive retrieval, export, restore tested; SIEM outage not*
- ✅ `MC-070-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-070-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-070-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-070-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-070-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-070-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-070-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-070-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-070-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-070-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-070-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-070-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*

### MC-071 — Repository license/notice metadata

- ◐ `MC-071-T01` Select and document the repository/project license with legal/owner approval and add the complete `LICENSE` text at repository root. — *Proprietary all-rights-reserved placeholder shipped; owner/legal selection pending (W-008)*
- ✅ `MC-071-T02` Add `NOTICE` when required by the chosen license or bundled third-party works and include copyright/attribution information.
- ✅ `MC-071-T03` Inventory third-party dependencies/assets and verify their licenses are compatible with distribution and intended deployment.
- ✅ `MC-071-T04` Generate/maintain third-party notices from the dependency lock/SBOM to prevent manual drift.
- ⊘ `MC-071-T05` Add source-file headers only where organisational policy/license requires them; avoid inconsistent or misleading headers. — *No per-file headers required by the placeholder licence*
- ✅ `MC-071-T06` Add packaging rules ensuring LICENSE/NOTICE/third-party notices ship in source and binary/container distributions where required.
- ◐ `MC-071-T07` Add CI compliance checks for missing/forbidden licenses and new dependency-license changes. — *tools/sbom.py fails on forbidden/unknown licences; CI not yet running (W-010)*
- ✅ `MC-071-T08` Record license metadata in `pyproject.toml`, SBOM, release manifest, and README.
- ✅ `MC-071-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- ◐ `MC-071-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approve… — *Automated locally and wired into CI workflow; hosted CI not yet executed (W-010)*
- ✅ `MC-071-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- ✅ `MC-071-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- ◐ `MC-071-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence. — *Cadence defined; named owners pending (W-001)*
- ✅ `MC-071-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls… — *In repo at documented path and in RELEASE_MANIFEST.sha256*
- ✅ `MC-071-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact. — *Schemas/configs/tests pinned (constraints.txt, versioned $id)*
- ✅ `MC-071-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver. — *RTM row generated in governance/RTM.json*
- ◐ `MC-071-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absen… — *Passes in a clean container locally; hosted CI not yet executed (W-010)*
- ☐ `MC-071-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register. — *Human security/architecture/operations review pending (W-002)*
- ✅ `MC-071-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component. — *governance/ACCEPTANCE_EVIDENCE.json records artifact and test-run digests*
- ✅ `MC-071-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author m… — *docs/OPERATIONS.md covers inspect/diagnose/rollback*
