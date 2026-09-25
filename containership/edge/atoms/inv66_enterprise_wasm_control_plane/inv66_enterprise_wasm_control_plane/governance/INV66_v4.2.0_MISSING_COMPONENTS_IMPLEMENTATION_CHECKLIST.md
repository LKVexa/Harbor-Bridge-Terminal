# INV-66 v4.2.0 — Missing Components Implementation & Verification Checklist

**Repository:** Enterprise Wasm Control Plane (`INV-66`)  
**Baseline audited release:** `4.2.0`  
**Source gap inventory:** `inv66_enterprise_wasm_control_plane_v4.2.0_MISSING_COMPONENTS.md`  
**Checklist scope:** all 71 post-hardening missing production components/artifacts  
**Severity distribution:** 26 Critical, 39 High, 5 Medium, 1 Low/conditional  

## How to use this checklist

- A checkbox is **not complete** because a design note exists. Mark it complete only when the described implementation/control exists and its required evidence is retained.
- Task IDs are stable in the form `MC-###-T##`; Definition-of-Done evidence items use `MC-###-D##`.
- Security-critical controls should fail closed unless an explicitly approved degraded mode is defined and tested.
- Machine-readable acceptance evidence should record artifact/test digests, tool/runtime versions, environment, timestamp, owner, and reviewer.
- Any `N/A` disposition must be explicit, justified, approved, and represented in the RTM/evidence bundle; do not delete the task.
- Any temporary exception requires an entry in the exception/waiver register (MC-067) with owner, compensating controls, and expiry.

## Recommended implementation sequence

1. **Governance and normative baseline:** MC-001 through MC-011 plus MC-071.
2. **Typed trust boundaries and integrations:** MC-012 through MC-021, MC-029 through MC-037.
3. **Durable configuration/state and distributed correctness:** MC-022 through MC-028, MC-038 through MC-043, MC-069 and MC-070.
4. **Performance and operator visibility:** MC-044 through MC-054.
5. **Certification, release, and operations:** MC-055 through MC-068.

> This ordering is dependency-oriented, not a waiver of severity. Critical security/durability gaps should remain release-blocking until closed.

# Architecture and governance

## MC-001 — Bundled master prompt/workflow source (`MASTER.md`)

**Severity:** Medium  
**Related controls:** C020, C090, C100  
**Gap statement:** README previously claimed it was present, but it is not in the archive. Restore the authoritative 100-item master prompt/workflow source or remove it from the release bill of materials.  

### Implementation checklist

- [ ] `MC-001-T01` Locate the authoritative source for the Post-Kubernetes Master Prompt & Workflow Series and determine whether INV-66 is governed by a frozen release, generated source, or maintained upstream document.
- [ ] `MC-001-T02` Create `MASTER.md` with an immutable document identifier, semantic version, source revision/commit, generation timestamp, and SHA-256 digest of the authoritative source.
- [ ] `MC-001-T03` Ensure all 100 INV-66 checklist requirements are represented without silent omission, reordering, or semantic weakening; add a machine-verifiable count and ID reconciliation check.
- [ ] `MC-001-T04` Add a provenance header identifying the generator/source path and the exact transformation rules used if `MASTER.md` is generated rather than hand-maintained.
- [ ] `MC-001-T05` Add CI validation that fails if README/BOM claims `MASTER.md` exists but the file is missing, or if its digest/count no longer matches the authoritative source.
- [ ] `MC-001-T06` Add release-manifest coverage so `MASTER.md` is included in `RELEASE_MANIFEST.sha256` and therefore protected by release integrity checks.
- [ ] `MC-001-T07` Document whether `MASTER.md` is normative or informative and define the change-control process required to update it.
- [ ] `MC-001-T08` If the project intentionally does not bundle the master source, remove all inclusion claims and replace them with a resolvable, version-pinned source reference plus offline retrieval instructions.
- [ ] `MC-001-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence.
- [ ] `MC-001-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- [ ] `MC-001-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- [ ] `MC-001-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- [ ] `MC-001-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.

### Definition of done / acceptance evidence

- [ ] `MC-001-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-001-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-001-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-001-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-001-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-001-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-001-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-002 — Approved architecture decision record (ADR)

**Severity:** High  
**Related controls:** C010  
**Gap statement:** No ADR records the Cosmonic Control/wasmCloud technology choice, alternatives, constraints, or approval.  

### Implementation checklist

- [ ] `MC-002-T01` Create an ADR using a stable ID such as `ADR-0001-enterprise-wasm-control-plane.md` and record status, date, deciders, technical owners, and review expiry.
- [ ] `MC-002-T02` Document the decision to use Cosmonic Control/wasmCloud-aligned control-plane concepts, distinguishing product-specific dependencies from architecture-level contracts.
- [ ] `MC-002-T03` Compare at least the chosen approach with a custom wasmCloud controller, Kubernetes/GitOps controller patterns, direct lattice management, and alternative policy/admission architectures.
- [ ] `MC-002-T04` Record decision drivers: multi-lattice governance, tenant isolation, signer/registry policy, GitOps integration, append-only audit, latency SLO, edge/site autonomy, and operational ownership.
- [ ] `MC-002-T05` Record rejected alternatives and explicit reasons including complexity, failure domains, lock-in, portability, security boundary, and lifecycle cost.
- [ ] `MC-002-T06` Capture hard constraints and assumptions from `contract.py`, including untrusted callers, independently failing peers/paths/stores, and local/remote behavioral equivalence.
- [ ] `MC-002-T07` Document consequences: new durable stores, identity federation, policy-engine coupling, deployment-manager adapter, audit anchoring, HA requirements, and operations burden.
- [ ] `MC-002-T08` Require architecture/security/SRE approval and link the ADR to the RTM and production-exit gate.
- [ ] `MC-002-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence.
- [ ] `MC-002-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- [ ] `MC-002-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- [ ] `MC-002-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- [ ] `MC-002-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.

### Definition of done / acceptance evidence

- [ ] `MC-002-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-002-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-002-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-002-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-002-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-002-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-002-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-003 — Accountable owner and escalation matrix

**Severity:** High  
**Related controls:** C009, C097  
**Gap statement:** No named service owner, security owner, on-call owner, or escalation route is packaged.  

### Implementation checklist

- [ ] `MC-003-T01` Define a RACI/ownership matrix covering service owner, product owner, architecture owner, security owner, IAM owner, SRE/on-call owner, data/audit owner, and release manager.
- [ ] `MC-003-T02` Assign each role to a durable team or rotation rather than only an individual; include primary and secondary escalation contacts.
- [ ] `MC-003-T03` Define 24x7 vs business-hours support expectations and severity-based acknowledgement/engagement targets.
- [ ] `MC-003-T04` Map ownership to concrete boundaries: admission service, RBAC/policy data, registry/signer policy, audit store, identity federation, deployment adapter, CI/CD, and infrastructure.
- [ ] `MC-003-T05` Define who can approve emergency policy changes, disable admission, rotate keys, restore state, waive controls, and declare production readiness.
- [ ] `MC-003-T06` Create an escalation tree for dependency failures involving INV-63, INV-64, GAP-13, GAP-07, identity, registry, KMS, and storage teams.
- [ ] `MC-003-T07` Include ownership metadata in runbooks, alert routing, CODEOWNERS/review rules, and production-exit evidence.
- [ ] `MC-003-T08` Add a recurring control that detects orphaned ownership when teams, aliases, or rotations change.
- [ ] `MC-003-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence.
- [ ] `MC-003-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- [ ] `MC-003-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- [ ] `MC-003-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- [ ] `MC-003-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.

### Definition of done / acceptance evidence

- [ ] `MC-003-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-003-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-003-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-003-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-003-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-003-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-003-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-004 — Deployment/topology architecture specification

**Severity:** High  
**Related controls:** C003, C005, C006, C051  
**Gap statement:** No production topology defines control-plane instances, trust zones, stores, sites, dependency endpoints, or failure domains.  

### Implementation checklist

- [ ] `MC-004-T01` Produce a production topology diagram covering control-plane instances, load balancers/gateways, identity provider, policy engine, provenance service, registry endpoints, audit store, configuration store, and INV-63 deployment manager.
- [ ] `MC-004-T02` Define trust zones and network boundaries for tenant traffic, administrative traffic, east-west service calls, storage access, and cross-site replication.
- [ ] `MC-004-T03` Document deployment modes for single site, multi-site, regional, disconnected/edge, and disaster-recovery operation, including unsupported topologies.
- [ ] `MC-004-T04` Define failure domains and placement rules so replicas do not share node/rack/zone/site single points of failure where the availability target requires separation.
- [ ] `MC-004-T05` Identify every persisted dataset, its authoritative owner, consistency model, replication scope, retention class, residency constraints, and recovery objective.
- [ ] `MC-004-T06` Define ingress/egress ports, protocols, TLS identities, DNS/service-discovery assumptions, firewall policy, and required network reachability.
- [ ] `MC-004-T07` Document scaling units and control loops: stateless admission replicas, stateful stores, worker/queue partitions, and cross-lattice inventory shards.
- [ ] `MC-004-T08` Add sequence/data-flow diagrams for successful admission, denial, dependency failure, configuration activation, rollback, and emergency freeze.
- [ ] `MC-004-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence.
- [ ] `MC-004-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- [ ] `MC-004-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- [ ] `MC-004-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- [ ] `MC-004-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.

### Definition of done / acceptance evidence

- [ ] `MC-004-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-004-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-004-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-004-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-004-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-004-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-004-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-005 — Production source-of-truth design

**Severity:** Critical  
**Related controls:** C004, C032, C057, C095  
**Gap statement:** The contract says the audit log is authoritative, but only process-local memory exists; no durable authoritative store or consistency model is implemented.  
**Key cross-component dependencies:** MC-014, MC-023, MC-035, MC-038, MC-063, MC-070  

### Implementation checklist

- [ ] `MC-005-T01` Define the authoritative data model for admissions, refusals, policy/config versions, RBAC changes, registry/signer changes, forwarding outcomes, and cross-lattice inventory.
- [ ] `MC-005-T02` Select a durable source-of-truth architecture: append-only event log with projections, transactional database plus immutable journal, or equivalent design with documented consistency semantics.
- [ ] `MC-005-T03` Define event IDs, monotonic ordering scope, causal/correlation identifiers, idempotency keys, actor identity, policy/config digests, timestamps, and integrity fields.
- [ ] `MC-005-T04` Define exactly which state is reconstructed from the log and which state is independently authoritative; prohibit ambiguous dual-write ownership.
- [ ] `MC-005-T05` Implement atomic persistence semantics so a decision cannot be acknowledged as durable if its authoritative audit/state record was not committed.
- [ ] `MC-005-T06` Define recovery/replay from an empty projection, checkpoint/snapshot strategy, schema evolution, and deterministic replay requirements.
- [ ] `MC-005-T07` Protect the source of truth using access control, encryption, tamper-evident anchoring, backup/restore, retention, and legal-hold controls.
- [ ] `MC-005-T08` Add consistency tests proving post-crash state, replayed state, exported audit state, and live projections converge to the same logical result.
- [ ] `MC-005-T09` Define the artifact owner, reviewer roles, approval authority, change-control path, and review cadence.
- [ ] `MC-005-T10` Capture assumptions, non-goals, dependencies, trust boundaries, failure domains, and unsupported modes that materially affect this component.
- [ ] `MC-005-T11` Use stable document/schema IDs and semantic versions; keep a changelog or revision history suitable for release evidence.
- [ ] `MC-005-T12` Link the artifact to relevant `CHECKLIST.json` controls and normative requirement IDs in the RTM.
- [ ] `MC-005-T13` Add automated repository checks for required presence, internal links/references, version consistency, and release-manifest inclusion.

### Definition of done / acceptance evidence

- [ ] `MC-005-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-005-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-005-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-005-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-005-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-005-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-005-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Requirements and semantics

## MC-006 — Normative SHALL requirements specification

**Severity:** High  
**Related controls:** C011-C019  
**Gap statement:** The checklist asks for testable requirements, but the archive has no separate normative requirements document with IDs, acceptance criteria, and owners.  

### Implementation checklist

- [ ] `MC-006-T01` Create a normative requirements specification with stable IDs (for example `REQ-INV66-*`) and RFC 2119/8174-style SHALL/SHOULD/MAY language.
- [ ] `MC-006-T02` Cover functional requirements for admission, RBAC, registry/signer policy, audit, cross-lattice inventory, GitOps intake, configuration, and administrative controls.
- [ ] `MC-006-T03` Cover non-functional requirements for availability, durability, consistency, latency, throughput, isolation, residency, recoverability, observability, and operability.
- [ ] `MC-006-T04` For every SHALL, define measurable acceptance criteria, evidence type, owner, and failure disposition.
- [ ] `MC-006-T05` Separate normative requirements from implementation notes, rationale, examples, and future work so certification cannot be satisfied by prose-only intent.
- [ ] `MC-006-T06` Express negative/security requirements explicitly, including zero forwarding of unadmitted manifests, fail-closed conditions, and forbidden cross-tenant disclosure.
- [ ] `MC-006-T07` Assign version and change history; require impact analysis when a normative requirement changes.
- [ ] `MC-006-T08` Validate that the specification maps without gaps to all applicable C001-C100 checklist items.
- [ ] `MC-006-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- [ ] `MC-006-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- [ ] `MC-006-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- [ ] `MC-006-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- [ ] `MC-006-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability.

### Definition of done / acceptance evidence

- [ ] `MC-006-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-006-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-006-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-006-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-006-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-006-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-006-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-007 — Requirements traceability matrix (RTM)

**Severity:** High  
**Related controls:** C020, C090, C100  
**Gap statement:** No machine-readable mapping connects all 100 requirements to code, tests, evidence, exceptions, and release status.  

### Implementation checklist

- [ ] `MC-007-T01` Create a machine-readable RTM in JSON/YAML/CSV with one row per normative requirement and one row per C001-C100 control where appropriate.
- [ ] `MC-007-T02` Include fields for requirement ID, source, owner, implementation artifact/path, test IDs, evidence URI/hash, status, waiver ID, release version, and last verification timestamp.
- [ ] `MC-007-T03` Allow many-to-many mappings between requirements, code modules, schemas, tests, dashboards, runbooks, and evidence.
- [ ] `MC-007-T04` Fail CI when a normative SHALL has no implementation reference, no verification reference, an expired waiver, or stale/missing evidence.
- [ ] `MC-007-T05` Validate that all 100 checklist IDs are present exactly once in the control coverage view and that no unknown/deprecated IDs appear silently.
- [ ] `MC-007-T06` Generate human-readable coverage summaries from the RTM rather than maintaining duplicate manually edited status tables.
- [ ] `MC-007-T07` Preserve historical RTM snapshots per release to support auditability and regression analysis.
- [ ] `MC-007-T08` Link each MC-001..MC-071 closure to the RTM evidence that demonstrates the gap is actually resolved.
- [ ] `MC-007-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- [ ] `MC-007-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- [ ] `MC-007-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- [ ] `MC-007-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- [ ] `MC-007-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability.

### Definition of done / acceptance evidence

- [ ] `MC-007-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-007-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-007-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-007-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-007-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-007-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-007-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-008 — Lifecycle/state-transition model

**Severity:** High  
**Related controls:** C014-C015  
**Gap statement:** No explicit state machine defines proposed/admitted/rejected/deployed/rolled-back/quarantined states and legal transitions.  

### Implementation checklist

- [ ] `MC-008-T01` Define an explicit workload/change lifecycle such as proposed -> validated -> authorized -> admitted -> persisted -> forwarded -> acknowledged -> deployed, plus rejected/quarantined/rolled-back/failed terminal or recovery states.
- [ ] `MC-008-T02` Define legal transitions, transition initiators, guards, side effects, and required durable writes using a state-transition table or executable state machine.
- [ ] `MC-008-T03` Distinguish admission decision state from downstream deployment/reconciliation state so a successful admission is not misreported as successful deployment.
- [ ] `MC-008-T04` Define retryable vs terminal failures at each transition and whether retries reuse the same idempotency key and decision record.
- [ ] `MC-008-T05` Define cancellation and supersession semantics for GitOps changes that are replaced while validation or forwarding is in progress.
- [ ] `MC-008-T06` Define rollback transitions and whether rollback itself requires fresh authorization/admission.
- [ ] `MC-008-T07` Include quarantine/freeze transitions that prevent forwarding while preserving operator visibility and auditability.
- [ ] `MC-008-T08` Create transition tests that prove illegal transitions fail closed and concurrent transitions cannot produce contradictory terminal states.
- [ ] `MC-008-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- [ ] `MC-008-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- [ ] `MC-008-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- [ ] `MC-008-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- [ ] `MC-008-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability.

### Definition of done / acceptance evidence

- [ ] `MC-008-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-008-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-008-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-008-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-008-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-008-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-008-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-009 — Capacity, quota, and fairness model

**Severity:** High  
**Related controls:** C017, C028, C067, C069  
**Gap statement:** `max_components` and manifest bytes are local parser limits only; tenant/lattice quotas, concurrency budgets, and fairness are absent.  

### Implementation checklist

- [ ] `MC-009-T01` Define quota dimensions by organisation, tenant, lattice, environment, site, workload, principal, and API operation where applicable.
- [ ] `MC-009-T02` Specify hard limits and soft budgets for request rate, concurrent admissions, manifest bytes/components, pending forwards, inventory objects, audit write rate, and storage consumption.
- [ ] `MC-009-T03` Define fairness algorithm and isolation strategy (for example per-tenant token buckets/weighted fair queues) so one tenant cannot starve others.
- [ ] `MC-009-T04` Define burst capacity, refill rates, borrowing rules, and administrative overrides with expiration and audit.
- [ ] `MC-009-T05` Expose quota headers/status or typed error details so clients can distinguish policy denial from throttling/capacity exhaustion.
- [ ] `MC-009-T06` Define queue depth and wait-time limits; reject or shed load before unbounded memory or latency growth occurs.
- [ ] `MC-009-T07` Create capacity formulas linking replica count and dependency throughput to safe admitted QPS and tenant count.
- [ ] `MC-009-T08` Test noisy-neighbor scenarios and prove per-tenant limits and global protection remain effective under overload.
- [ ] `MC-009-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- [ ] `MC-009-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- [ ] `MC-009-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- [ ] `MC-009-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- [ ] `MC-009-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability.

### Definition of done / acceptance evidence

- [ ] `MC-009-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-009-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-009-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-009-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-009-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-009-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-009-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-010 — Offline/partition semantics

**Severity:** High  
**Related controls:** C018, C048, C055-C057, C089  
**Gap statement:** No documented or implemented behavior exists for identity, policy, registry, signer, deployment-manager, or audit-store unavailability.  

### Implementation checklist

- [ ] `MC-010-T01` Document behavior independently for identity, policy, registry, signer/provenance, deployment manager, audit store, configuration store, DNS/time, and network unavailability.
- [ ] `MC-010-T02` Classify each dependency as security-critical, durability-critical, availability-enhancing, or optional and define fail-closed/fail-open/degraded behavior accordingly.
- [ ] `MC-010-T03` Define cache eligibility, maximum staleness, signed cache artifacts, revocation behavior, and clock assumptions for offline operation.
- [ ] `MC-010-T04` Define whether previously admitted workloads may continue, whether new admissions are blocked, and whether administrative changes are accepted during partitions.
- [ ] `MC-010-T05` Define local-site autonomy and reconciliation semantics when connectivity returns, including conflict resolution and duplicate-event handling.
- [ ] `MC-010-T06` Define operator-visible degraded states and explicit reason codes for denials caused by unavailable trust dependencies.
- [ ] `MC-010-T07` Prevent stale identity/policy/provenance data from silently extending beyond configured TTL/lease periods.
- [ ] `MC-010-T08` Create partition/reconnect tests that exercise each dependency independently and in correlated failure combinations.
- [ ] `MC-010-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- [ ] `MC-010-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- [ ] `MC-010-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- [ ] `MC-010-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- [ ] `MC-010-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability.

### Definition of done / acceptance evidence

- [ ] `MC-010-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-010-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-010-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-010-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-010-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-010-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-010-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-011 — Constraint precedence policy

**Severity:** Medium  
**Related controls:** C019  
**Gap statement:** No deterministic precedence rules resolve security, residency, SLO, availability, and cost conflicts.  

### Implementation checklist

- [ ] `MC-011-T01` Define a deterministic precedence lattice for security, legal/residency, tenant isolation, safety, availability/SLO, performance, and cost constraints.
- [ ] `MC-011-T02` Specify non-overridable controls such as signature/provenance trust, tenant isolation, and legal residency where applicable.
- [ ] `MC-011-T03` Define how conflicts are surfaced as stable machine-readable reason codes rather than relying on evaluation order or free-form text.
- [ ] `MC-011-T04` Define policy-composition semantics for organisation, tenant, environment, site, lattice, and workload scopes including deny-overrides/permit-overrides rules.
- [ ] `MC-011-T05` Define tie-breaking for equally scoped policies using explicit priority/version rather than incidental storage or iteration order.
- [ ] `MC-011-T06` Document emergency exceptions, who may authorize them, their maximum TTL, required compensating controls, and mandatory audit fields.
- [ ] `MC-011-T07` Create conflict fixtures that prove the same input produces the same outcome across nodes, versions, and policy-engine deployment modes.
- [ ] `MC-011-T08` Link precedence rules to the operator explain view so rejected constraints and winning constraints are visible.
- [ ] `MC-011-T09` Express externally observable behavior deterministically, including success, denial, degraded, retryable, and terminal outcomes.
- [ ] `MC-011-T10` Define tenant/site/environment scope and any consistency, ordering, freshness, time, or isolation guarantees needed to remove ambiguity.
- [ ] `MC-011-T11` Assign stable normative IDs and map each behavior to implementation and verification evidence in the RTM.
- [ ] `MC-011-T12` Create executable/golden fixtures for boundary cases and conflicting inputs rather than relying solely on prose.
- [ ] `MC-011-T13` Require architecture/security/SRE review for semantics that can affect authorization, durability, or production availability.

### Definition of done / acceptance evidence

- [ ] `MC-011-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-011-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-011-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-011-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-011-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-011-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-011-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Interfaces and integration

## MC-012 — Versioned typed admission schema

**Severity:** Critical  
**Related controls:** C021-C022, C082  
**Gap statement:** `PK_ECP_ADMIT/1` is named but no JSON Schema, protobuf, WIT, OpenAPI, or equivalent typed contract is included.  
**Key cross-component dependencies:** MC-015, MC-016, MC-017, MC-018, MC-055  

### Implementation checklist

- [ ] `MC-012-T01` Define the canonical `PK_ECP_ADMIT/1` request/response schema in JSON Schema, protobuf, WIT, or another versioned IDL and publish generated language bindings where used.
- [ ] `MC-012-T02` Model authenticated principal separately from user-supplied payload fields; include tenant/organisation, lattice, environment/site context, manifest, request ID, idempotency key, and deadline metadata.
- [ ] `MC-012-T03` Define manifest schema or reference the authoritative INV-64 schema by immutable version/digest rather than using unconstrained generic JSON.
- [ ] `MC-012-T04` Define a typed decision response with admitted/denied status, stable reason/error codes, policy/config/provenance versions, manifest digest, audit event ID, and forwarding disposition.
- [ ] `MC-012-T05` Add explicit maximum sizes/counts, required fields, canonicalization rules, unknown-field behavior, and Unicode/identifier normalization rules.
- [ ] `MC-012-T06` Publish compatibility rules for adding/removing fields and version negotiation for `PK_ECP_ADMIT/1` successors.
- [ ] `MC-012-T07` Generate positive, negative, boundary, and malicious conformance fixtures from the schema.
- [ ] `MC-012-T08` Validate every externally received request against the schema before security-sensitive evaluation and fail closed on validation failure.
- [ ] `MC-012-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-012-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-012-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-012-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-012-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-012-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-012-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-012-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-012-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-012-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-012-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-012-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-013 — Versioned RBAC administration schema/API

**Severity:** Critical  
**Related controls:** C021-C024  
**Gap statement:** `PK_ECP_RBAC/1` has no typed request/response contract or administration surface.  
**Key cross-component dependencies:** MC-025, MC-031, MC-032, MC-055  

### Implementation checklist

- [ ] `MC-013-T01` Define a typed `PK_ECP_RBAC/1` administration API covering bindings, groups/service principals, organisation/tenant/lattice scopes, roles/capabilities, conditions, and deny rules.
- [ ] `MC-013-T02` Separate read/query operations from mutation operations and define distinct authorization capabilities for each.
- [ ] `MC-013-T03` Include optimistic concurrency/version preconditions so concurrent administrators cannot silently overwrite newer policy state.
- [ ] `MC-013-T04` Require change reason, actor, approver where applicable, desired activation time, expiry for temporary grants, and idempotency key on mutations.
- [ ] `MC-013-T05` Define bulk import/export semantics with transactional validation and per-entry error reporting without partial unsafe application.
- [ ] `MC-013-T06` Define pagination/filtering and high-cardinality protections for query surfaces.
- [ ] `MC-013-T07` Define stable error codes for conflict, stale version, forbidden scope, invalid principal, invalid capability, dependency unavailable, and policy lock/freeze.
- [ ] `MC-013-T08` Add contract tests and authorization-negative tests for every operation and scope boundary.
- [ ] `MC-013-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-013-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-013-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-013-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-013-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-013-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-013-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-013-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-013-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-013-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-013-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-013-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-014 — Versioned audit event schema/API

**Severity:** Critical  
**Related controls:** C021-C022, C027  
**Gap statement:** `PK_ECP_AUDIT/1` has no formal external event schema, query/export API, or compatibility rules.  
**Key cross-component dependencies:** MC-035, MC-038, MC-070  

### Implementation checklist

- [ ] `MC-014-T01` Define `PK_ECP_AUDIT/1` as a versioned immutable event schema with event ID, sequence/order scope, timestamp, actor, subject, tenant/lattice/workload IDs, action, outcome, reason, request/trace IDs, policy/config/provenance digests, and integrity metadata.
- [ ] `MC-014-T02` Define query API semantics for time range, actor, tenant, lattice, workload, action, decision, event ID, and correlation/request ID filters.
- [ ] `MC-014-T03` Define pagination/cursor stability, maximum query windows, rate limits, and authorization controls for audit reads.
- [ ] `MC-014-T04` Define immutable export format and cryptographic verification metadata so exported batches can be independently validated.
- [ ] `MC-014-T05` Define retention class, legal hold, archival tier, deletion restrictions, and privacy/redaction behavior without mutating integrity-critical source records.
- [ ] `MC-014-T06` Define schema evolution rules that preserve old event readability and chain/hash verification.
- [ ] `MC-014-T07` Create SIEM/export adapter contract with delivery acknowledgements, retry/idempotency, backpressure, and dead-letter semantics.
- [ ] `MC-014-T08` Add conformance fixtures proving events emitted by every security-sensitive operation validate against the schema.
- [ ] `MC-014-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-014-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-014-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-014-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-014-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-014-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-014-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-014-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-014-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-014-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-014-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-014-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-015 — Authentication boundary

**Severity:** Critical  
**Related controls:** C023, C044  
**Gap statement:** `admit()` accepts a caller-supplied user string; there is no authenticated principal, token validation, mTLS, workload identity, or peer attestation.  
**Key cross-component dependencies:** MC-031, MC-034  

### Implementation checklist

- [ ] `MC-015-T01` Place authentication at the transport/service boundary so `ControlPlane.admit()` never treats a caller-supplied username as proof of identity.
- [ ] `MC-015-T02` Select supported mechanisms such as OIDC/JWT for humans/services, SPIFFE/SPIRE or mTLS workload identities for service-to-service calls, and document where each is valid.
- [ ] `MC-015-T03` Validate issuer, audience, signature algorithm, key ID, expiry/not-before, nonce/replay characteristics, and tenant/organisation claims before authorization.
- [ ] `MC-015-T04` Bind the authenticated principal to request context and prohibit overriding it through manifest or API fields.
- [ ] `MC-015-T05` Define certificate/token revocation, signing-key rotation, JWKS caching/refresh, clock-skew limits, and fail-closed behavior when trust material is unavailable.
- [ ] `MC-015-T06` Map external identities into stable internal principal IDs so email/display-name changes do not rewrite authorization history.
- [ ] `MC-015-T07` Emit authentication outcome and principal metadata into the audit trail without logging credentials/tokens.
- [ ] `MC-015-T08` Add negative tests for forged tokens, wrong audience, expired/not-yet-valid tokens, revoked credentials, unknown CA, tenant mismatch, and credential replay.
- [ ] `MC-015-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-015-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-015-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-015-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-015-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-015-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-015-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-015-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-015-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-015-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-015-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-015-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-016 — Structured machine-readable error model

**Severity:** High  
**Related controls:** C026  
**Gap statement:** Denials are free-form strings rather than stable error codes with typed details and remediation metadata.  

### Implementation checklist

- [ ] `MC-016-T01` Define a stable namespaced error-code taxonomy separating validation, authentication, authorization, policy, provenance, quota, conflict, dependency, timeout, overload, and internal failures.
- [ ] `MC-016-T02` For each code, define HTTP/gRPC/WIT mapping, retryability, operator severity, client remediation guidance, and whether details are safe to expose.
- [ ] `MC-016-T03` Return machine-readable field violations with JSON pointer/path and bounded sanitized context for invalid requests.
- [ ] `MC-016-T04` Include correlation/request ID and dependency identifier where relevant, but never secret values, raw tokens, or cross-tenant data.
- [ ] `MC-016-T05` Keep human-readable messages non-normative; clients must branch on stable codes, not string matching.
- [ ] `MC-016-T06` Define nested causes only when they preserve abstraction boundaries and cannot leak infrastructure internals.
- [ ] `MC-016-T07` Version the error catalog and test backward compatibility for existing codes.
- [ ] `MC-016-T08` Add tests asserting every documented failure path maps to an approved code and unknown exceptions become a safe generic internal error.
- [ ] `MC-016-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-016-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-016-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-016-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-016-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-016-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-016-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-016-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-016-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-016-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-016-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-016-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-017 — Idempotency, timeout, cancellation, retry, and backpressure contract

**Severity:** High  
**Related controls:** C025, C028, C053-C054  
**Gap statement:** No request IDs/idempotency keys, deadlines, retry classifications, queue semantics, or overload protocol are defined.  

### Implementation checklist

- [ ] `MC-017-T01` Define globally unique request IDs and client-supplied idempotency keys, including scope, retention window, collision behavior, and replayed-response semantics.
- [ ] `MC-017-T02` Define end-to-end deadlines and per-dependency timeout budgets derived from the p99 admission SLO rather than independent arbitrary defaults.
- [ ] `MC-017-T03` Propagate cancellation to in-flight dependency calls when safe, while preserving already-committed authoritative audit/state writes.
- [ ] `MC-017-T04` Classify each remote operation as safely retryable, conditionally retryable with idempotency, or non-retryable; encode this in client middleware.
- [ ] `MC-017-T05` Define bounded exponential backoff with jitter, maximum attempts/time, and retry budgets to prevent synchronized retry storms.
- [ ] `MC-017-T06` Define admission queues/backpressure, maximum queue depth, maximum age, overload rejection code, and client retry-after behavior.
- [ ] `MC-017-T07` Define duplicate forwarding prevention for INV-63 using idempotency keys/outbox semantics.
- [ ] `MC-017-T08` Create timeout/cancellation/retry tests that inject lost responses, partial commits, duplicate requests, slow dependencies, and overload.
- [ ] `MC-017-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-017-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-017-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-017-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-017-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-017-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-017-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-017-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-017-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-017-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-017-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-017-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-018 — Protocol/version compatibility matrix and negotiation

**Severity:** High  
**Related controls:** C016, C027, C093  
**Gap statement:** No supported-version matrix or cross-version test fixtures are bundled.  

### Implementation checklist

- [ ] `MC-018-T01` Maintain a version matrix for admission, RBAC, audit, INV-64 manifest schema, GAP-13 policy API, GAP-07 provenance API, INV-63 deployment API, and supported wasmCloud/Cosmonic releases.
- [ ] `MC-018-T02` Define minimum/maximum compatible versions and semantic differences that require translation adapters or block interoperability.
- [ ] `MC-018-T03` Implement explicit protocol negotiation or capability discovery where multiple wire versions may coexist.
- [ ] `MC-018-T04` Define rolling-upgrade rules so N and N-1 replicas do not make divergent security decisions on the same request.
- [ ] `MC-018-T05` Keep golden cross-version fixtures proving old clients can read required fields and new clients handle old responses safely.
- [ ] `MC-018-T06` Define deprecation lifecycle, telemetry for old-version use, warning period, and hard removal policy.
- [ ] `MC-018-T07` Pin dependency versions in release metadata and expose active protocol capabilities through the version/status endpoint.
- [ ] `MC-018-T08` Run the compatibility matrix in CI and block release when a claimed supported combination fails.
- [ ] `MC-018-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-018-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-018-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-018-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-018-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-018-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-018-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-018-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-018-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-018-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-018-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-018-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-019 — Real deployment-manager adapter

**Severity:** Critical  
**Related controls:** C003, C021, C030, C051  
**Gap statement:** Admitted manifests are appended to an in-memory `forwarded` list; no INV-63 client, transport, acknowledgement, failure handling, or delivery semantics exist.  
**Key cross-component dependencies:** MC-017, MC-038, MC-041  

### Implementation checklist

- [ ] `MC-019-T01` Implement an INV-63 client adapter behind an interface that can be replaced with test doubles without changing admission logic.
- [ ] `MC-019-T02` Define the exact INV-63 request schema, endpoint/service discovery, authentication identity, authorization capability, timeout, and TLS requirements.
- [ ] `MC-019-T03` Forward only after the authoritative admitted decision/audit record is durably committed; use transactional outbox or equivalent to avoid lost/duplicate delivery.
- [ ] `MC-019-T04` Attach admission event ID, manifest digest, tenant/lattice, desired-state revision, and idempotency key to downstream requests.
- [ ] `MC-019-T05` Define acknowledgement semantics distinguishing accepted-for-reconciliation from deployed/healthy.
- [ ] `MC-019-T06` Handle timeout, rejection, conflict, unavailable, and duplicate acknowledgements with typed state transitions and bounded retries.
- [ ] `MC-019-T07` Persist forwarding state and last error so restart/replay resumes safely without re-authorizing a different artifact under the same request.
- [ ] `MC-019-T08` Add integration tests against a real or protocol-faithful INV-63 test service covering success, duplicate delivery, lost ack, rejection, restart, and backpressure.
- [ ] `MC-019-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-019-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-019-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-019-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-019-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-019-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-019-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-019-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-019-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-019-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-019-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-019-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-020 — Adjacent-layer integration adapters/tests

**Severity:** Critical  
**Related controls:** C003, C030, C083  
**Gap statement:** No executable integrations exist for INV-64 application model, GAP-13 policy engine, GAP-07 provenance/signing, identity, registry, or audit storage.  
**Key cross-component dependencies:** MC-012, MC-015, MC-033, MC-019  

### Implementation checklist

- [ ] `MC-020-T01` Create an adapter boundary and executable integration contract for INV-64 application model, GAP-13 policy engine, GAP-07 provenance/signing, identity provider, registry metadata, audit storage, and INV-63 deployment manager.
- [ ] `MC-020-T02` For each adapter, document ownership, request/response schema, authentication identity, timeout, retryability, consistency requirement, and failure classification.
- [ ] `MC-020-T03` Use protocol-faithful test containers/fakes generated from the actual schema; avoid mocks that bypass serialization, authentication, or error behavior.
- [ ] `MC-020-T04` Create a dependency matrix that states which adapters are required for admission and which can degrade without violating security or durability.
- [ ] `MC-020-T05` Propagate request/trace/correlation IDs and stable tenant/workload identifiers across every adapter call.
- [ ] `MC-020-T06` Pin supported adapter/protocol versions and prove version-skew behavior.
- [ ] `MC-020-T07` Create end-to-end negative tests where each dependency returns malformed, stale, unauthorized, unavailable, slow, or conflicting data.
- [ ] `MC-020-T08` Add CI jobs that execute all supported adjacent-layer integrations and retain machine-readable evidence.
- [ ] `MC-020-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-020-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-020-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-020-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-020-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-020-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-020-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-020-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-020-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-020-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-020-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-020-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-021 — GitOps ingestion/change-controller integration

**Severity:** High  
**Related controls:** C011-C012, C021, C030  
**Gap statement:** The source function names enterprise management/GitOps, but no Git repository watcher, desired-state ingestion interface, webhook, change-set model, or handoff to reconciliation is present.  

### Implementation checklist

- [ ] `MC-021-T01` Define a GitOps source abstraction covering repository URL/project identity, branch/ref, path, commit SHA, change-set ID, author, signature status, and desired-state revision.
- [ ] `MC-021-T02` Support secure ingestion by webhook and/or polling with authenticated source events, replay protection, and deduplication by immutable commit/change ID.
- [ ] `MC-021-T03` Parse desired state using the authoritative INV-64 application model and reject ambiguous or mutable artifact references before admission.
- [ ] `MC-021-T04` Define reconciliation handoff semantics: detect new revision, validate, authorize, admit, persist, forward, and record terminal/retry state.
- [ ] `MC-021-T05` Handle force-push, branch deletion, superseded commits, revert commits, and concurrent changes deterministically.
- [ ] `MC-021-T06` Define repository credentials as secret references and enforce least-privilege read-only access where write-back is not required.
- [ ] `MC-021-T07` Expose GitOps status linked to commit SHA, admission event, deployment-manager acknowledgement, and live inventory.
- [ ] `MC-021-T08` Add integration tests using an actual Git server fixture for webhook replay, invalid signature, rapid successive commits, rollback commit, and repository outage.
- [ ] `MC-021-T09` Document the trust boundary, caller/callee identity, required capability, data classification, and network exposure for the interface.
- [ ] `MC-021-T10` Define deterministic timeouts, limits, backpressure, idempotency/retry rules, and dependency-failure behavior.
- [ ] `MC-021-T11` Propagate request/correlation/trace identifiers and record the protocol/schema version used for each security-sensitive operation.
- [ ] `MC-021-T12` Instrument rate/error/latency/saturation metrics and structured error/log events for the interface without leaking secrets.
- [ ] `MC-021-T13` Provide schema-driven contract tests, malicious/negative fixtures, compatibility tests, and protocol-faithful integration tests.

### Definition of done / acceptance evidence

- [ ] `MC-021-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-021-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-021-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-021-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-021-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-021-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-021-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Configuration and state management

## MC-022 — Declarative production configuration schema/loader

**Severity:** Critical  
**Related controls:** C033-C035  
**Gap statement:** RBAC, registries, signers, limits, endpoints, and environment/site overrides are constructor arguments only.  
**Key cross-component dependencies:** MC-023, MC-024, MC-027  

### Implementation checklist

- [ ] `MC-022-T01` Define a versioned declarative configuration schema for identity, policy, RBAC store, registry/signer policy, audit store, deployment adapter, limits, telemetry, retention, and site/environment metadata.
- [ ] `MC-022-T02` Separate non-secret configuration values from secret references; prohibit inline credentials in normal config.
- [ ] `MC-022-T03` Provide secure defaults with deny-by-default trust policy, bounded limits, disabled unauthenticated admin surfaces, and explicit production-mode requirements.
- [ ] `MC-022-T04` Implement layered configuration precedence (built-in defaults < environment/site profile < deployment override) with deterministic merge semantics.
- [ ] `MC-022-T05` Validate syntax, types, ranges, endpoint schemes, duplicate/conflicting policy, and cross-field constraints before activation.
- [ ] `MC-022-T06` Reject unknown security-critical fields to prevent typo-driven bypass; define controlled forward-compatibility behavior for noncritical extensions.
- [ ] `MC-022-T07` Expose the active configuration version/digest while redacting secret references/values.
- [ ] `MC-022-T08` Add schema tests, invalid-fixture tests, and golden configuration examples for development, single-site production, and multi-site production.
- [ ] `MC-022-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-022-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-022-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-022-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-022-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-022-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-022-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-022-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-022-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-022-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-022-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-022-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-023 — Configuration provenance and version history

**Severity:** High  
**Related controls:** C036  
**Gap statement:** No author, source revision, approval, activation timestamp, or configuration digest is retained.  

### Implementation checklist

- [ ] `MC-023-T01` Assign every configuration revision a unique immutable ID and cryptographic digest over canonicalized non-secret content plus secret-reference identifiers.
- [ ] `MC-023-T02` Record author/principal, source system/repository, source revision/commit, approver(s), creation time, activation time, previous version, and reason/ticket.
- [ ] `MC-023-T03` Persist provenance independently of process memory and link every admission decision to the exact active configuration revision.
- [ ] `MC-023-T04` Retain historical versions for the defined audit/rollback period and prevent silent mutation of previously activated revisions.
- [ ] `MC-023-T05` Capture automated transformations/default injection so the stored effective configuration can be reproduced exactly.
- [ ] `MC-023-T06` Expose provenance through administrative query APIs with scope-aware authorization.
- [ ] `MC-023-T07` Add integrity checks that detect configuration history gaps or digest mismatch.
- [ ] `MC-023-T08` Produce release evidence showing the production config revision used for each environment/site.
- [ ] `MC-023-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-023-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-023-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-023-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-023-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-023-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-023-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-023-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-023-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-023-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-023-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-023-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-024 — Atomic configuration activation and rollback

**Severity:** Critical  
**Related controls:** C037-C038  
**Gap statement:** No transaction/staging mechanism protects partial policy updates or enables safe rollback.  

### Implementation checklist

- [ ] `MC-024-T01` Implement staged configuration lifecycle: draft -> validated -> approved -> staged -> activated, with atomic switch of the active revision.
- [ ] `MC-024-T02` Validate the complete candidate configuration and all referenced policy/secret/dependency prerequisites before changing active state.
- [ ] `MC-024-T03` Use transactional storage/CAS so partial writes across RBAC, registry/signer policy, and service settings cannot create mixed revisions.
- [ ] `MC-024-T04` Give every admission operation a consistent configuration snapshot/version so an in-flight request is not evaluated against multiple revisions.
- [ ] `MC-024-T05` Define automatic rollback triggers for activation failure and operator-driven rollback to a known prior revision.
- [ ] `MC-024-T06` Prevent rollback to cryptographically/semantically incompatible or revoked configuration without explicit break-glass approval.
- [ ] `MC-024-T07` Audit activation, rejection, rollback, and failed rollback with actor, reason, old/new digests, and correlation ID.
- [ ] `MC-024-T08` Create concurrency tests for simultaneous activations, stale-version writers, process crash mid-activation, and dependency failure during validation.
- [ ] `MC-024-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-024-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-024-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-024-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-024-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-024-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-024-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-024-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-024-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-024-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-024-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-024-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-025 — Persistent RBAC/policy store

**Severity:** Critical  
**Related controls:** C032-C038, C098  
**Gap statement:** Roles are process-local immutable mappings with no enterprise persistence, synchronization, review, or delegated administration.  
**Key cross-component dependencies:** MC-013, MC-032, MC-038  

### Implementation checklist

- [ ] `MC-025-T01` Select a durable RBAC/policy datastore with transactional updates, high availability, backup/restore, encryption, and supported consistency semantics.
- [ ] `MC-025-T02` Define normalized entities for organisations, tenants, principals, groups, service principals, lattices, roles/capabilities, conditions, bindings, denials, and expirations.
- [ ] `MC-025-T03` Enforce referential integrity and uniqueness rules that prevent ambiguous duplicate grants or orphaned principals/scopes.
- [ ] `MC-025-T04` Use optimistic concurrency or serializable transactions for administrative updates; reject stale writers.
- [ ] `MC-025-T05` Support delegated administration bounded by scope and capability, never by arbitrary record-level write access.
- [ ] `MC-025-T06` Publish change events or revision tokens so all admission replicas observe a controlled, monotonic policy version.
- [ ] `MC-025-T07` Implement cache invalidation/TTL behavior that never extends revoked privilege beyond an approved maximum window.
- [ ] `MC-025-T08` Add migration, backup/restore, audit, and multi-replica consistency tests including revocation propagation.
- [ ] `MC-025-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-025-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-025-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-025-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-025-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-025-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-025-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-025-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-025-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-025-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-025-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-025-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-026 — Approved registry/signer policy administration store

**Severity:** Critical  
**Related controls:** C032-C038, C045  
**Gap statement:** Registry and signer allowlists have no persistent control plane, approval workflow, versioning, or distribution mechanism.  
**Key cross-component dependencies:** MC-029, MC-030, MC-035  

### Implementation checklist

- [ ] `MC-026-T01` Define persistent entities for approved registries, repository namespaces, signer identities/keys/certificates, allowed artifact types, environments, scopes, and validity windows.
- [ ] `MC-026-T02` Support policy conditions such as exact registry host, namespace/repository prefix, immutable digest requirement, signer key ID, issuer, certificate constraints, and approved version ranges.
- [ ] `MC-026-T03` Require dual control or designated approval for trust-root/signer changes in production environments.
- [ ] `MC-026-T04` Record provenance, justification, ticket, author, approver, activation/expiry, and superseded revision for every policy change.
- [ ] `MC-026-T05` Implement atomic distribution/versioning so all admission replicas evaluate against a coherent registry/signer policy revision.
- [ ] `MC-026-T06` Handle signer/key rotation with overlap windows and explicit revocation semantics.
- [ ] `MC-026-T07` Provide a dry-run impact query showing which currently deployed/inventory artifacts would violate a proposed policy.
- [ ] `MC-026-T08` Add tests for namespace confusion, registry case/canonicalization, expired signer, revoked key, overlapping rotations, and stale replica policy.
- [ ] `MC-026-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-026-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-026-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-026-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-026-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-026-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-026-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-026-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-026-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-026-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-026-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-026-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-027 — Secret-management integration

**Severity:** Critical  
**Related controls:** C039, C047-C048  
**Gap statement:** No KMS/Vault/secret provider integration or secret-reference model exists.  

### Implementation checklist

- [ ] `MC-027-T01` Define a provider-agnostic secret-reference interface for KMS/Vault/cloud secret managers and workload identity based retrieval.
- [ ] `MC-027-T02` Keep secret material out of environment dumps, config files, command-line arguments, logs, traces, metrics labels, audit payloads, and crash reports.
- [ ] `MC-027-T03` Grant each service identity only the exact secret/key paths required and separate read, unwrap/sign, and administrative capabilities.
- [ ] `MC-027-T04` Define secret caching in memory, TTL, zeroization/best-effort lifecycle, renewal, and behavior when the provider is unavailable.
- [ ] `MC-027-T05` Support rotation without service restart where practical and verify old credentials stop being accepted after the overlap window.
- [ ] `MC-027-T06` Differentiate secret references from ordinary strings in configuration schemas to prevent accidental inline values.
- [ ] `MC-027-T07` Audit secret-reference configuration changes and access failures without recording secret contents.
- [ ] `MC-027-T08` Add tests using ephemeral secret-manager fixtures for rotation, revoked access, expired lease, provider outage, and log-redaction guarantees.
- [ ] `MC-027-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-027-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-027-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-027-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-027-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-027-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-027-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-027-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-027-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-027-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-027-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-027-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-028 — Deterministic bootstrap/install packaging

**Severity:** High  
**Related controls:** C031, C040  
**Gap statement:** No `pyproject.toml`, dependency lock/constraints, install command, container image, service unit, or reproducible bootstrap artifact is bundled.  

### Implementation checklist

- [ ] `MC-028-T01` Add `pyproject.toml` with explicit package metadata, supported Python versions, dependency groups, entry points, and deterministic build backend configuration.
- [ ] `MC-028-T02` Pin direct dependencies and produce a lock/constraints artifact with hashes; document controlled update workflow.
- [ ] `MC-028-T03` Build a minimal production container/image or equivalent service package with non-root execution, read-only filesystem where feasible, and explicit runtime user/group.
- [ ] `MC-028-T04` Provide reproducible build commands and record compiler/interpreter/base-image versions plus artifact digests.
- [ ] `MC-028-T05` Add service bootstrap manifests (container orchestration/system service as applicable), health checks, resource requests/limits, and required volumes/network policies.
- [ ] `MC-028-T06` Provide environment bootstrap validation for DNS, certificates, storage, KMS, identity, policy, and deployment-manager reachability.
- [ ] `MC-028-T07` Generate SBOM and provenance/attestation for the built artifact and sign the release artifact.
- [ ] `MC-028-T08` Add CI that installs from a clean environment and proves the produced package starts and passes smoke tests without undeclared local dependencies.
- [ ] `MC-028-T09` Define ownership and durability class for the data, including source of truth, consistency, retention, backup, restore, and migration requirements.
- [ ] `MC-028-T10` Validate all inputs before activation/commit and fail closed on security-critical ambiguity or partial state.
- [ ] `MC-028-T11` Record immutable revision/digest/provenance metadata and link active versions to admission/audit decisions.
- [ ] `MC-028-T12` Provide concurrency control, atomicity, rollback/recovery, and startup-integrity checks appropriate to the state.
- [ ] `MC-028-T13` Instrument state age/version, update failures, lag/backlog, storage saturation, and rollback/recovery events.

### Definition of done / acceptance evidence

- [ ] `MC-028-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-028-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-028-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-028-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-028-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-028-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-028-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Security, trust, and isolation

## MC-029 — Cryptographic artifact signature verification

**Severity:** Critical  
**Related controls:** C045  
**Gap statement:** Admission trusts the manifest’s signer string; it does not verify an actual signature, certificate/key identity, transparency record, or signing policy.  
**Key cross-component dependencies:** MC-026, MC-030, MC-034  

### Implementation checklist

- [ ] `MC-029-T01` Define accepted signature formats and trust roots for Wasm/components/manifests, including signer identity binding, algorithm policy, key IDs, and certificate/attestation chains.
- [ ] `MC-029-T02` Resolve the actual artifact bytes or immutable digest before verification; never accept a manifest `signer` string as evidence.
- [ ] `MC-029-T03` Verify signature cryptographically against the exact digest/content and enforce approved algorithm/key-size/curve requirements.
- [ ] `MC-029-T04` Validate signer authorization for tenant/environment/repository/artifact scope and validity window.
- [ ] `MC-029-T05` Check revocation/expiration and signer trust-root rotation; define offline behavior when revocation or trust services are unavailable.
- [ ] `MC-029-T06` Protect against signature wrapping/substitution and canonicalization ambiguity by signing/verifying a precisely defined payload format.
- [ ] `MC-029-T07` Record verification result, signer key/cert fingerprint, algorithm, trust policy revision, and artifact digest in the admission audit event.
- [ ] `MC-029-T08` Add negative tests for forged signature, altered artifact, wrong key, expired/revoked cert, unapproved signer, algorithm downgrade, and replayed metadata.
- [ ] `MC-029-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-029-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-029-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-029-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-029-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-029-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-029-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-029-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-029-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-029-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-029-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-029-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-030 — Artifact digest/provenance verification

**Severity:** Critical  
**Related controls:** C045  
**Gap statement:** The engine hashes the admission manifest but does not resolve/verify immutable artifact digests, SBOM/provenance attestations, approved versions, or registry metadata.  
**Key cross-component dependencies:** MC-029, MC-062  

### Implementation checklist

- [ ] `MC-030-T01` Require immutable artifact references by digest for production admission or resolve tags to immutable digests before policy evaluation.
- [ ] `MC-030-T02` Fetch and validate registry metadata using authenticated registry clients with tenant-scoped credentials and TLS verification.
- [ ] `MC-030-T03` Verify artifact digest against downloaded/resolved content and reject digest mismatch or mutable-reference race conditions.
- [ ] `MC-030-T04` Consume signed provenance attestations (for example SLSA/in-toto compatible) and verify builder identity, source revision, build recipe, and subject digest.
- [ ] `MC-030-T05` Associate SBOMs with artifact digest and enforce required SBOM/provenance presence, freshness, and policy constraints.
- [ ] `MC-030-T06` Validate approved version/channel policy without trusting unverified semantic-version labels embedded in manifests.
- [ ] `MC-030-T07` Cache verified metadata by immutable digest with bounded lifetime and revocation invalidation.
- [ ] `MC-030-T08` Add TOCTOU tests where tag contents change between resolution and forwarding, plus malformed provenance/SBOM and registry compromise simulations.
- [ ] `MC-030-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-030-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-030-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-030-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-030-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-030-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-030-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-030-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-030-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-030-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-030-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-030-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-031 — Enterprise identity federation

**Severity:** Critical  
**Related controls:** C023, C044  
**Gap statement:** No OIDC/SAML/workload identity integration, token audience/issuer validation, session policy, or identity lifecycle exists.  
**Key cross-component dependencies:** MC-015, MC-032  

### Implementation checklist

- [ ] `MC-031-T01` Integrate supported enterprise identity providers using OIDC/OAuth2 and/or SAML for human administrators and workload identity for services.
- [ ] `MC-031-T02` Define tenant/organisation discovery and claim mapping rules; prohibit arbitrary caller-controlled tenant selection without authorization.
- [ ] `MC-031-T03` Use stable immutable subject IDs plus issuer rather than mutable usernames/email addresses as authorization keys.
- [ ] `MC-031-T04` Validate token audience, issuer, signature, lifetime, authentication strength/AMR where required, and group/role claims against approved mappings.
- [ ] `MC-031-T05` Define joiner/mover/leaver lifecycle, account disable propagation, group-change latency, and emergency revocation targets.
- [ ] `MC-031-T06` Support service principals/non-human identities with independent credentials and lifecycle controls.
- [ ] `MC-031-T07` Define session duration, refresh, step-up authentication for privileged admin operations, and break-glass accounts with enhanced audit.
- [ ] `MC-031-T08` Add federation tests against representative identity providers and negative fixtures for tenant confusion, stale groups, token substitution, and deprovisioned users.
- [ ] `MC-031-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-031-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-031-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-031-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-031-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-031-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-031-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-031-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-031-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-031-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-031-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-031-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-032 — Organisation/tenant RBAC hierarchy and capability model

**Severity:** Critical  
**Related controls:** C006, C024, C042, C046  
**Gap statement:** The current `(user, lattice) -> role` map does not implement organisation scope, tenant delegation, groups, service principals, capability scoping, or deny policy.  

### Implementation checklist

- [ ] `MC-032-T01` Define hierarchy and inheritance across organisation -> tenant -> environment/site -> lattice -> workload/resource scopes.
- [ ] `MC-032-T02` Define roles as explicit capability sets; avoid hard-coded role-name checks inside decision code where capability evaluation is required.
- [ ] `MC-032-T03` Support groups, service principals, automation identities, temporary elevation, scoped delegation, and explicit deny rules.
- [ ] `MC-032-T04` Define inheritance/override semantics and deny precedence so grants at broader scope cannot silently bypass narrower restrictions.
- [ ] `MC-032-T05` Enforce least privilege and separation of duties for policy admin, deployment, audit read, security admin, and emergency control capabilities.
- [ ] `MC-032-T06` Define privilege-escalation prevention: administrators may not grant capabilities they do not possess unless explicitly authorized by a higher-level control.
- [ ] `MC-032-T07` Provide access-review queries showing effective permissions and the complete chain of grants/denials that produced them.
- [ ] `MC-032-T08` Add property tests and adversarial tests for cross-tenant access, scope confusion, wildcard abuse, group nesting, expired grants, and delegation escalation.
- [ ] `MC-032-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-032-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-032-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-032-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-032-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-032-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-032-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-032-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-032-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-032-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-032-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-032-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-033 — External policy-engine enforcement

**Severity:** Critical  
**Related controls:** C019, C030, C048  
**Gap statement:** GAP-13 is declared as a dependency but is not queried, cached, version-pinned, or failure-handled.  
**Key cross-component dependencies:** MC-010, MC-011, MC-040  

### Implementation checklist

- [ ] `MC-033-T01` Define the GAP-13 policy decision contract including input document, policy bundle/version/digest, decision, obligations, reason codes, and evaluation metadata.
- [ ] `MC-033-T02` Pass authenticated principal, tenant/lattice/environment, artifact digest/provenance, registry/signer results, quotas, topology/site, and desired operation into policy evaluation.
- [ ] `MC-033-T03` Pin or record the exact policy revision used for every admission; do not permit untraceable “latest” policy during decision evaluation.
- [ ] `MC-033-T04` Define fail-closed behavior when the policy engine is unavailable for security-critical decisions and explicitly identify any safe cached-policy mode.
- [ ] `MC-033-T05` If caching compiled policy, verify bundle signature/digest, maximum age, revocation, and deterministic evaluation equivalence.
- [ ] `MC-033-T06` Prevent policy-engine responses from granting capabilities beyond the authenticated request context or bypassing non-overridable control-plane invariants.
- [ ] `MC-033-T07` Propagate policy reason/obligation data into machine-readable decisions and the operator explain view.
- [ ] `MC-033-T08` Add integration and differential tests comparing local/cached vs remote evaluation, stale policy, malformed response, engine timeout, and conflicting policy versions.
- [ ] `MC-033-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-033-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-033-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-033-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-033-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-033-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-033-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-033-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-033-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-033-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-033-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-033-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-034 — Transport/storage encryption and key rotation

**Severity:** Critical  
**Related controls:** C047  
**Gap statement:** There is no network transport or durable storage layer and therefore no implemented TLS/mTLS, at-rest encryption, managed keys, or rotation workflow.  

### Implementation checklist

- [ ] `MC-034-T01` Require TLS 1.2+ or approved organisational baseline for every remote boundary and prefer mTLS for service-to-service control-plane traffic.
- [ ] `MC-034-T02` Define certificate identities, trust roots, SAN expectations, rotation cadence, revocation, and automated renewal for each service.
- [ ] `MC-034-T03` Encrypt durable RBAC/config/audit/inventory data at rest using managed KMS keys and document envelope-encryption design where applicable.
- [ ] `MC-034-T04` Separate keys by environment/tenant/data class where risk and compliance require it; restrict decrypt/sign capabilities by workload identity.
- [ ] `MC-034-T05` Define key rotation and re-encryption process, overlap window, rollback, and handling of unavailable/revoked keys.
- [ ] `MC-034-T06` Disable insecure protocols/ciphers and enforce hostname/service-identity verification; prohibit plaintext downgrade paths.
- [ ] `MC-034-T07` Expose key/certificate expiry health signals without exposing private material.
- [ ] `MC-034-T08` Add automated TLS configuration tests, expired/revoked certificate tests, wrong-service identity tests, and restore tests for encrypted backups.
- [ ] `MC-034-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-034-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-034-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-034-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-034-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-034-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-034-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-034-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-034-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-034-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-034-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-034-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-035 — Durable tamper-evident audit anchoring

**Severity:** Critical  
**Related controls:** C049  
**Gap statement:** The local SHA-256 chain detects accidental mutation but an actor able to rewrite all in-memory records can recompute it; no signed/WORM/remote anchor exists.  
**Key cross-component dependencies:** MC-014, MC-038, MC-070  

### Implementation checklist

- [ ] `MC-035-T01` Persist audit records in append-only/WORM-capable storage or an append-only log whose mutation controls are stronger than the service actor.
- [ ] `MC-035-T02` Anchor batches/segments using signed Merkle roots/hash-chain heads to an independent trust domain or transparency/timestamp service.
- [ ] `MC-035-T03` Use a dedicated audit-signing key protected by KMS/HSM with restricted signing policy and no general application read access to private key material.
- [ ] `MC-035-T04` Define segment rotation, checkpoint frequency, chain continuity across replicas/restarts, and immutable export verification.
- [ ] `MC-035-T05` Ensure an administrator who can modify application data cannot rewrite both records and anchors without detection.
- [ ] `MC-035-T06` Implement periodic background verification and alert on chain discontinuity, anchor mismatch, missing segment, timestamp anomaly, or verification failure.
- [ ] `MC-035-T07` Define recovery behavior when the audit sink/anchor is unavailable; security-sensitive operations must follow documented durability rules.
- [ ] `MC-035-T08` Create tamper tests that delete/reorder/edit/re-chain records, compromise one storage layer, replay old segments, and verify independent validation still detects manipulation.
- [ ] `MC-035-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-035-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-035-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-035-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-035-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-035-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-035-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-035-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-035-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-035-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-035-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-035-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-036 — Formal threat model

**Severity:** High  
**Related controls:** C041  
**Gap statement:** No STRIDE/attack-tree/abuse-case artifact covers malicious tenants, compromised control-plane actors, replay, confused deputy, dependency compromise, or supply-chain attacks.  

### Implementation checklist

- [ ] `MC-036-T01` Create a formal threat model with assets, trust boundaries, data flows, entry points, actors, attacker capabilities, and security assumptions.
- [ ] `MC-036-T02` Cover malicious tenant/admin, compromised service identity, compromised admission replica, registry compromise, signer-key compromise, policy-engine compromise, storage compromise, and network attacker scenarios.
- [ ] `MC-036-T03` Use STRIDE plus abuse cases/attack trees for spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege, replay, confused deputy, and supply-chain attacks.
- [ ] `MC-036-T04` Identify security invariants such as “unadmitted manifests are never forwarded” and “cross-tenant data is never disclosed.”
- [ ] `MC-036-T05` Map each threat to preventative, detective, and recovery controls and to concrete test IDs.
- [ ] `MC-036-T06` Rate residual risk using the organisation’s approved methodology and create owned remediation items for unacceptable risk.
- [ ] `MC-036-T07` Include boundary-specific threats for OIDC/mTLS, GitOps webhooks, registry resolution, provenance verification, policy calls, audit export, and admin APIs.
- [ ] `MC-036-T08` Review the threat model on material architecture/interface changes and before every production exit gate.
- [ ] `MC-036-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-036-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-036-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-036-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-036-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-036-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-036-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-036-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-036-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-036-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-036-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-036-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-037 — Security adversarial and fuzz suite

**Severity:** High  
**Related controls:** C050, C085, C087  
**Gap statement:** No fuzzing or dedicated tests cover replay, spoofing, injection, privilege escalation, side channels, parser bombs, or resource exhaustion.  

### Implementation checklist

- [ ] `MC-037-T01` Create grammar/schema-aware fuzzers for admission manifests, RBAC/admin payloads, audit query parameters, configuration documents, and any protocol decoders.
- [ ] `MC-037-T02` Add property-based tests for authorization monotonicity, tenant isolation, idempotency, deterministic canonicalization, and audit-chain invariants.
- [ ] `MC-037-T03` Build replay/spoofing tests for tokens, webhooks, idempotency keys, signed artifacts, policy responses, and downstream acknowledgements.
- [ ] `MC-037-T04` Create injection tests for JSON/string fields, log forging, path/URL parsing, registry references, Unicode confusables, and control characters.
- [ ] `MC-037-T05` Create resource-exhaustion cases: oversized/deep JSON, huge lists, compression bombs if supported, slow clients, many concurrent requests, and pathological policy sets.
- [ ] `MC-037-T06` Exercise privilege-escalation paths including scope confusion, wildcard roles, stale caches, race conditions, and admin API abuse.
- [ ] `MC-037-T07` Run sanitizers/static analysis/dependency scanning appropriate to implementation languages and retain crash corpora/minimized reproducers.
- [ ] `MC-037-T08` Gate releases on zero unresolved high-severity fuzz/security findings or a time-bounded approved waiver with compensating controls.
- [ ] `MC-037-T09` Define attacker capabilities, protected assets, trust roots, security invariants, and fail-closed conditions specific to this control.
- [ ] `MC-037-T10` Apply least privilege, explicit scopes, tenant isolation, secure defaults, and separation of duties to every administrative and runtime identity involved.
- [ ] `MC-037-T11` Use approved cryptography/key management where authenticity, integrity, or confidentiality is required; define rotation and revocation.
- [ ] `MC-037-T12` Ensure security-sensitive successes and failures produce tamper-evident audit records with stable reason codes and correlation IDs.
- [ ] `MC-037-T13` Derive negative/adversarial tests directly from the threat model and retain machine-readable results as release evidence.

### Definition of done / acceptance evidence

- [ ] `MC-037-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-037-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-037-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-037-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-037-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-037-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-037-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Resilience and distributed-systems behavior

## MC-038 — Durable state store with crash recovery/replay

**Severity:** Critical  
**Related controls:** C057, C095  
**Gap statement:** Audit and forwarded state disappear on process restart; no journal, transaction log, snapshot, or replay protocol exists.  
**Key cross-component dependencies:** MC-005, MC-039, MC-063  

### Implementation checklist

- [ ] `MC-038-T01` Persist admission decisions, audit events, forwarding/outbox state, config/policy revision references, and inventory state in durable storage before acknowledging committed operations.
- [ ] `MC-038-T02` Define transaction boundaries that prevent an admitted decision from existing without its corresponding authoritative audit/state record.
- [ ] `MC-038-T03` Implement write-ahead journal/outbox semantics for downstream forwarding and replay unfinished deliveries after restart.
- [ ] `MC-038-T04` Define snapshot/checkpoint creation and deterministic replay from log plus snapshot, including schema-version migration.
- [ ] `MC-038-T05` Use fsync/commit durability settings consistent with stated RPO; document acknowledged-loss guarantees explicitly.
- [ ] `MC-038-T06` Detect and reject corrupted/incomplete journal segments rather than silently skipping them.
- [ ] `MC-038-T07` Implement startup recovery that verifies state integrity before becoming ready for traffic.
- [ ] `MC-038-T08` Add crash-point tests at every persistence/forwarding boundary and prove restart yields exactly-once logical state even when physical delivery is at-least-once.
- [ ] `MC-038-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- [ ] `MC-038-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- [ ] `MC-038-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- [ ] `MC-038-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- [ ] `MC-038-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment.

### Definition of done / acceptance evidence

- [ ] `MC-038-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-038-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-038-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-038-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-038-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-038-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-038-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-039 — HA replication/consensus/leader election

**Severity:** Critical  
**Related controls:** C055, C058  
**Gap statement:** No multi-instance coordination, fencing, epoch/lease model, duplicate-owner protection, or split-brain handling exists.  
**Key cross-component dependencies:** MC-038, MC-043, MC-058  

### Implementation checklist

- [ ] `MC-039-T01` Define whether admission replicas are stateless over a shared strongly consistent store or coordinate through leader/partition ownership; document the chosen consistency model.
- [ ] `MC-039-T02` If leaders/owners exist, implement leases/epochs/fencing tokens so stale controllers cannot commit after losing ownership.
- [ ] `MC-039-T03` Define replication factor, quorum/consistency settings, placement across failure domains, and behavior during quorum loss.
- [ ] `MC-039-T04` Prevent duplicate forwarding and duplicate config activation across replicas using durable idempotency/outbox coordination.
- [ ] `MC-039-T05` Define read consistency for policy/config changes and maximum propagation delay for revocation-sensitive data.
- [ ] `MC-039-T06` Define split-brain detection and safe mode; never allow both partitions to make mutually incompatible authoritative changes when consistency is required.
- [ ] `MC-039-T07` Expose leader/epoch/replica health and replication lag metrics.
- [ ] `MC-039-T08` Create multi-node tests for leader loss, delayed packets, asymmetric partition, clock skew, stale owner, concurrent writers, and healing after split-brain.
- [ ] `MC-039-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- [ ] `MC-039-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- [ ] `MC-039-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- [ ] `MC-039-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- [ ] `MC-039-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment.

### Definition of done / acceptance evidence

- [ ] `MC-039-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-039-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-039-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-039-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-039-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-039-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-039-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-040 — Dependency health and degraded-mode controller

**Severity:** High  
**Related controls:** C052, C056  
**Gap statement:** No health model tracks identity, policy, registry, signing, deployment, or storage dependencies or decides safe degraded behavior.  

### Implementation checklist

- [ ] `MC-040-T01` Create a dependency registry describing criticality, endpoint, active protocol version, health method, timeout budget, and degraded-mode policy for each external dependency.
- [ ] `MC-040-T02` Implement active/passive health checks that distinguish unreachable, unauthorized, stale, overloaded, semantically unhealthy, and version-incompatible states.
- [ ] `MC-040-T03` Aggregate dependency state into readiness without marking the service ready when a security-critical dependency cannot support safe admission.
- [ ] `MC-040-T04` Define explicit degraded capabilities: e.g., audit queries available while new admissions are blocked, or cached read-only inventory while deployment forwarding is unavailable.
- [ ] `MC-040-T05` Use hysteresis/debounce to prevent readiness flapping and synchronized reconnect storms.
- [ ] `MC-040-T06` Expose last-success/last-error, latency, breaker state, and staleness age without leaking sensitive details.
- [ ] `MC-040-T07` Emit audit/operator events when entering or leaving degraded mode.
- [ ] `MC-040-T08` Add tests for each dependency failing independently and correlated failures, verifying readiness and allowed operation set match policy.
- [ ] `MC-040-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- [ ] `MC-040-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- [ ] `MC-040-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- [ ] `MC-040-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- [ ] `MC-040-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment.

### Definition of done / acceptance evidence

- [ ] `MC-040-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-040-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-040-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-040-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-040-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-040-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-040-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-041 — Bounded retry/circuit breaker/load shedding

**Severity:** High  
**Related controls:** C053-C054  
**Gap statement:** No remote calls exist yet, and no reusable retry/backoff/jitter, breaker, queue, or shedding policy is implemented for future adapters.  

### Implementation checklist

- [ ] `MC-041-T01` Implement shared retry middleware with operation-specific policy, exponential backoff, full/equal jitter, retry budget, maximum elapsed time, and cancellation support.
- [ ] `MC-041-T02` Retry only idempotent operations or operations protected by idempotency keys/transaction IDs; document exceptions explicitly.
- [ ] `MC-041-T03` Implement circuit breakers per dependency/endpoint with closed/open/half-open states and bounded probe traffic.
- [ ] `MC-041-T04` Add concurrency and queue limits per dependency to stop slow downstreams from exhausting worker/thread/socket pools.
- [ ] `MC-041-T05` Implement load shedding before resource exhaustion and return stable overload errors plus safe retry-after hints.
- [ ] `MC-041-T06` Honor upstream deadlines so retries cannot exceed the caller’s end-to-end budget.
- [ ] `MC-041-T07` Export retry count, breaker transitions, shed requests, queue depth, wait time, and dependency saturation metrics.
- [ ] `MC-041-T08` Create failure-injection tests for timeouts, resets, 429/503, lost acknowledgements, partial outages, and recovery without retry amplification.
- [ ] `MC-041-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- [ ] `MC-041-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- [ ] `MC-041-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- [ ] `MC-041-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- [ ] `MC-041-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment.

### Definition of done / acceptance evidence

- [ ] `MC-041-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-041-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-041-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-041-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-041-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-041-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-041-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-042 — Quarantine/freeze/emergency-disable control

**Severity:** High  
**Related controls:** C059, C092  
**Gap statement:** README mentions package removal, but no runtime administrative freeze, tenant/lattice quarantine, kill switch, or audited emergency action exists.  

### Implementation checklist

- [ ] `MC-042-T01` Implement audited administrative controls to freeze all admissions, quarantine a tenant/organisation, quarantine a lattice/site, disable forwarding, and revoke a specific artifact/signer/registry.
- [ ] `MC-042-T02` Define separate capabilities for invoking, approving, and clearing emergency controls; use dual control for high-impact production actions where required.
- [ ] `MC-042-T03` Persist emergency state durably and replicate it consistently so a restart or failover cannot silently clear the control.
- [ ] `MC-042-T04` Define precedence so emergency deny/freeze controls override ordinary allow policy and cached decisions.
- [ ] `MC-042-T05` Include reason, incident/ticket, actor, approver, activation time, expiry/TTL, scope, and recovery criteria in every action.
- [ ] `MC-042-T06` Expose current emergency state prominently through health/status and operator interfaces.
- [ ] `MC-042-T07` Define safe unfreeze procedure including policy/config refresh and verification that the unsafe condition is resolved.
- [ ] `MC-042-T08` Add tests proving quarantined scopes cannot forward while unaffected tenants remain isolated and operational as intended.
- [ ] `MC-042-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- [ ] `MC-042-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- [ ] `MC-042-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- [ ] `MC-042-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- [ ] `MC-042-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment.

### Definition of done / acceptance evidence

- [ ] `MC-042-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-042-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-042-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-042-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-042-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-042-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-042-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-043 — Fault-injection/recovery test suite

**Severity:** High  
**Related controls:** C060, C089  
**Gap statement:** No dependency failure, crash, disk-full, timeout, partition, reconnect, or stale-controller tests exist.  

### Implementation checklist

- [ ] `MC-043-T01` Build a deterministic fault-injection harness capable of failing each dependency with timeout, connection reset, stale data, malformed response, authorization error, overload, and partial success.
- [ ] `MC-043-T02` Inject process crash/kill at persistence boundaries, config activation, audit append, outbox enqueue, forwarding send, and acknowledgement handling.
- [ ] `MC-043-T03` Test storage failure modes including disk/full quota, read-only volume, corruption, high latency, lost quorum, and restore from backup.
- [ ] `MC-043-T04` Test network partitions, asymmetric reachability, DNS failure, certificate expiry, KMS outage, and clock skew/time-service loss.
- [ ] `MC-043-T05` Define expected safe state, data-loss bound, recovery-time objective, and operator signal for every fault scenario.
- [ ] `MC-043-T06` Automate recovery assertions so tests verify no unauthorized forward, no silent audit gap, no cross-tenant leakage, and no duplicate logical operation.
- [ ] `MC-043-T07` Run representative chaos tests in a production-like multi-replica environment rather than only unit-test mocks.
- [ ] `MC-043-T08` Retain machine-readable fault-injection results and link them to resilience requirements in the RTM.
- [ ] `MC-043-T09` Define RPO/RTO, consistency, availability, ordering, duplicate-handling, and failover behavior for each relevant failure domain.
- [ ] `MC-043-T10` Bound retries, queues, memory, concurrency, and recovery work to prevent cascades during dependency or site failure.
- [ ] `MC-043-T11` Preserve authorization, isolation, audit integrity, and idempotency invariants during crash, replay, failover, partition, and reconnect.
- [ ] `MC-043-T12` Expose health/degraded/lag/backlog/ownership state and give operators an audited safe-control action when automation is insufficient.
- [ ] `MC-043-T13` Prove the design using repeatable multi-process/fault-injection tests in a production-like environment.

### Definition of done / acceptance evidence

- [ ] `MC-043-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-043-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-043-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-043-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-043-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-043-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-043-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Performance and resource efficiency

## MC-044 — Reproducible benchmark/load/soak suite

**Severity:** High  
**Related controls:** C061-C064, C088  
**Gap statement:** No latency, throughput, startup, CPU, memory, storage, network, burst, overload, recovery, or fleet-scale measurements are packaged.  
**Key cross-component dependencies:** MC-045, MC-047  

### Implementation checklist

- [ ] `MC-044-T01` Create a reproducible benchmark harness with fixed hardware/runtime metadata, dataset seeds, dependency versions, and workload profiles.
- [ ] `MC-044-T02` Measure admission end-to-end and internal-stage latency (authn, authz, policy, provenance, persistence, forwarding enqueue), throughput, CPU, RSS/heap, I/O, network, and storage write rates.
- [ ] `MC-044-T03` Cover cold start, warm steady state, burst, overload, scale-out, scale-in, dependency slowdown, restart/recovery, and multi-tenant noisy-neighbor scenarios.
- [ ] `MC-044-T04` Include manifest-size/component-count distributions representative of expected production workloads plus adversarial boundary sizes.
- [ ] `MC-044-T05` Run soak tests long enough to expose leaks, queue growth, compaction pauses, key/token refresh effects, and periodic background tasks.
- [ ] `MC-044-T06` Record p50/p95/p99/p99.9/max and confidence/sample counts; do not report only averages.
- [ ] `MC-044-T07` Publish baseline artifacts and compare new runs against an approved reference using statistical/absolute regression thresholds.
- [ ] `MC-044-T08` Automate execution in a controlled CI/performance environment and store raw results plus environment fingerprints.
- [ ] `MC-044-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- [ ] `MC-044-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- [ ] `MC-044-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- [ ] `MC-044-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- [ ] `MC-044-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.

### Definition of done / acceptance evidence

- [ ] `MC-044-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-044-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-044-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-044-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-044-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-044-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-044-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-045 — Performance thresholds and regression gate

**Severity:** High  
**Related controls:** C062, C070  
**Gap statement:** The contract declares p99 <50 ms, but no benchmark enforces p50/p95/p99/worst-case or blocks regressions.  

### Implementation checklist

- [ ] `MC-045-T01` Define explicit latency thresholds for successful admission, policy denial, authentication denial, dependency-degraded denial, and administrative operations.
- [ ] `MC-045-T02` Derive a stage budget from the contract p99 <50 ms target, reserving margin for network and storage variability.
- [ ] `MC-045-T03` Define minimum sustained throughput and maximum resource cost at target load, plus overload behavior and recovery thresholds.
- [ ] `MC-045-T04` Define startup/readiness, failover, config-propagation, and revocation-propagation performance objectives where operationally relevant.
- [ ] `MC-045-T05` Use both absolute ceilings and percentage regression limits so a fast baseline cannot degrade materially while remaining under a loose maximum.
- [ ] `MC-045-T06` Gate on tail latency with sufficient sample size and stable environment; exclude warmup using documented methodology rather than cherry-picking.
- [ ] `MC-045-T07` Create waiver workflow for intentional regressions with owner, rationale, expiry, and compensating capacity plan.
- [ ] `MC-045-T08` Publish pass/fail benchmark evidence into the release acceptance bundle.
- [ ] `MC-045-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- [ ] `MC-045-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- [ ] `MC-045-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- [ ] `MC-045-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- [ ] `MC-045-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.

### Definition of done / acceptance evidence

- [ ] `MC-045-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-045-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-045-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-045-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-045-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-045-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-045-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-046 — Bounded audit/forwarded retention

**Severity:** Critical  
**Related controls:** C067  
**Gap statement:** Both in-memory collections grow without retention, compaction, persistence, or backpressure, creating unbounded memory growth.  

### Implementation checklist

- [ ] `MC-046-T01` Remove unbounded process-local `_audit` and `_forwarded` growth from production code paths; replace with durable bounded interfaces/projections.
- [ ] `MC-046-T02` Define audit retention tiers, hot-query window, archival policy, compaction/index lifecycle, and legal-hold exceptions.
- [ ] `MC-046-T03` Define forwarded/outbox retention by terminal acknowledgement, retry horizon, deduplication window, and incident-forensics needs.
- [ ] `MC-046-T04` Apply hard memory/queue bounds and backpressure before process memory can grow with traffic indefinitely.
- [ ] `MC-046-T05` Use streaming/paginated audit export instead of loading entire history into memory.
- [ ] `MC-046-T06` Expose retained count/bytes, queue depth, oldest pending age, compaction lag, and storage capacity/saturation metrics.
- [ ] `MC-046-T07` Define behavior when retention/archival sinks are full or unavailable; never silently drop security audit events.
- [ ] `MC-046-T08` Add long-duration tests proving memory reaches steady state under sustained load and retention/compaction does not break audit verification.
- [ ] `MC-046-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- [ ] `MC-046-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- [ ] `MC-046-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- [ ] `MC-046-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- [ ] `MC-046-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.

### Definition of done / acceptance evidence

- [ ] `MC-046-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-046-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-046-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-046-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-046-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-046-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-046-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-047 — Capacity/saturation model

**Severity:** High  
**Related controls:** C069  
**Gap statement:** No capacity formula or signal identifies safe admission QPS, queue depth, audit growth, tenant count, or scaling thresholds.  

### Implementation checklist

- [ ] `MC-047-T01` Derive a capacity model from per-admission CPU time, memory, external-call concurrency, audit write throughput, outbox throughput, and datastore limits.
- [ ] `MC-047-T02` Model capacity by tenant count, lattices, active policies/bindings, manifest size, admission QPS, audit events/sec, inventory objects, and query load.
- [ ] `MC-047-T03` Define saturation indicators such as CPU, runnable queue, request queue depth/age, connection pool utilization, datastore latency, replication lag, breaker state, and audit backlog.
- [ ] `MC-047-T04` Define scale-up/out trigger thresholds with hysteresis and minimum/maximum replica bounds.
- [ ] `MC-047-T05` Account for dependency bottlenecks so control-plane replicas are not scaled beyond safe identity/policy/registry/store throughput.
- [ ] `MC-047-T06` Include failure-headroom requirements (for example N+1/N+AZ-loss capacity) in sizing.
- [ ] `MC-047-T07` Validate the model using measured benchmark data and document known nonlinearities.
- [ ] `MC-047-T08` Create an operator capacity dashboard and runbook mapping saturation signals to scaling/remediation actions.
- [ ] `MC-047-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- [ ] `MC-047-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- [ ] `MC-047-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- [ ] `MC-047-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- [ ] `MC-047-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.

### Definition of done / acceptance evidence

- [ ] `MC-047-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-047-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-047-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-047-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-047-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-047-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-047-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-048 — Edge power/thermal characterization

**Severity:** Low/conditional  
**Related controls:** C068  
**Gap statement:** No constrained-edge power or thermal measurements establish whether this central control-plane component is suitable where C068 applies.  

### Implementation checklist

- [ ] `MC-048-T01` Determine whether INV-66 is ever deployed on constrained near/far-edge nodes; if not, document C068 as not applicable with architecture approval.
- [ ] `MC-048-T02` If applicable, define representative hardware classes, ambient/thermal conditions, power modes, and baseline idle/load measurements.
- [ ] `MC-048-T03` Measure incremental CPU package/system power, energy per admission, memory pressure, storage I/O, and thermal throttling under representative loads.
- [ ] `MC-048-T04` Measure cold-start and reconnect behavior under battery/power-saving modes where relevant.
- [ ] `MC-048-T05` Define power/thermal budgets and overload/thermal-throttling behavior that preserves security semantics.
- [ ] `MC-048-T06` Compare local admission vs remote-control-plane architecture to quantify energy/network tradeoffs for disconnected sites.
- [ ] `MC-048-T07` Record measurement tooling, calibration, sampling period, and environmental conditions for reproducibility.
- [ ] `MC-048-T08` Add the resulting applicability decision or benchmark evidence to the production acceptance bundle.
- [ ] `MC-048-T09` Define representative workload distributions, environment fingerprints, warmup, run length, sample count, and statistical reporting methodology.
- [ ] `MC-048-T10` Measure end-to-end and per-stage latency plus throughput, CPU, memory, I/O/network/storage, queueing, and saturation.
- [ ] `MC-048-T11` Define hard bounds for memory/queue/concurrency and verify graceful overload rather than unbounded degradation.
- [ ] `MC-048-T12` Link measured capacity to autoscaling/resource sizing and document dependency bottlenecks/assumptions.
- [ ] `MC-048-T13` Publish raw benchmark artifacts and enforce approved regression thresholds in CI/release gating.

### Definition of done / acceptance evidence

- [ ] `MC-048-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-048-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-048-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-048-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-048-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-048-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-048-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Observability and explainability

## MC-049 — Health/readiness/version/config/dependency endpoint

**Severity:** High  
**Related controls:** C071  
**Gap statement:** No operator endpoint exposes health, readiness, active version, config digest, dependency state, or capability set.  
**Key cross-component dependencies:** MC-050, MC-051, MC-052  

### Implementation checklist

- [ ] `MC-049-T01` Implement unauthenticated-minimal liveness and authenticated/appropriately exposed readiness/status endpoints with clearly separated semantics.
- [ ] `MC-049-T02` Report service build/version, protocol versions, active config/policy revision digests, feature/capability set, replica/site identity, and start time.
- [ ] `MC-049-T03` Report dependency health for identity, policy, provenance/registry, audit store, config/RBAC store, deployment manager, KMS, and telemetry/export sinks.
- [ ] `MC-049-T04` Include degraded-mode flags, emergency freeze/quarantine status, replication/leader state if applicable, and last successful authoritative write.
- [ ] `MC-049-T05` Keep readiness fail-closed when the service cannot safely admit/record/forward according to production requirements.
- [ ] `MC-049-T06` Bound endpoint latency and output size; do not perform unbounded dependency fan-out per scrape.
- [ ] `MC-049-T07` Redact secrets, tokens, internal credentials, and cross-tenant data; expose only operator-safe diagnostic metadata.
- [ ] `MC-049-T08` Add conformance tests for healthy, degraded, dependency-failed, stale-config, audit-store-failed, and emergency-freeze states.
- [ ] `MC-049-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- [ ] `MC-049-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- [ ] `MC-049-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- [ ] `MC-049-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- [ ] `MC-049-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.

### Definition of done / acceptance evidence

- [ ] `MC-049-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-049-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-049-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-049-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-049-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-049-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-049-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-050 — Metrics instrumentation/export

**Severity:** High  
**Related controls:** C072  
**Gap statement:** Contract signal names are declarations only; no counters/histograms/gauges or Prometheus/OTel exporter exist.  

### Implementation checklist

- [ ] `MC-050-T01` Instrument request counters by operation/outcome/reason class, authorization denials, policy denials, provenance failures, audit appends, forwarding outcomes, retries, and dependency errors.
- [ ] `MC-050-T02` Instrument histograms for end-to-end admission and each major stage, using buckets appropriate to the <50 ms p99 target.
- [ ] `MC-050-T03` Export gauges for in-flight requests, queue depth/age, outbox backlog, policy/config age, cache size/hit ratio, replication lag, and dependency breaker state.
- [ ] `MC-050-T04` Export process/runtime CPU, memory, GC, file descriptor/socket, thread/task, network, and storage metrics.
- [ ] `MC-050-T05` Use OpenTelemetry/Prometheus-compatible naming, units, descriptions, and stable semantic conventions.
- [ ] `MC-050-T06` Control label cardinality: tenant/workload identifiers must not be unbounded default labels; use exemplars/log correlation for high-cardinality detail.
- [ ] `MC-050-T07` Add metric schema/version tests and dashboard queries that fail visibly if required series disappear.
- [ ] `MC-050-T08` Validate instrumentation overhead under benchmark load and ensure metrics export failure cannot block admission.
- [ ] `MC-050-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- [ ] `MC-050-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- [ ] `MC-050-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- [ ] `MC-050-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- [ ] `MC-050-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.

### Definition of done / acceptance evidence

- [ ] `MC-050-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-050-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-050-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-050-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-050-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-050-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-050-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-051 — Structured operational logging

**Severity:** High  
**Related controls:** C073, C075  
**Gap statement:** No stable tenant/lattice/workload/request identifiers, structured log schema, redaction policy, or sink integration exists.  

### Implementation checklist

- [ ] `MC-051-T01` Define a structured JSON/log schema with timestamp, severity, event name, service/version, site/replica, request ID, trace/span ID, tenant/lattice/workload IDs, principal ID, and stable error/reason code.
- [ ] `MC-051-T02` Use explicit event IDs rather than free-form-only messages for security and operational state transitions.
- [ ] `MC-051-T03` Create redaction rules for tokens, secrets, headers, manifest sensitive fields, repository credentials, and PII; default to omission rather than masking unknown fields.
- [ ] `MC-051-T04` Prevent log forging by structured encoding and sanitizing embedded control characters/newlines from untrusted fields.
- [ ] `MC-051-T05` Define sampling rules that never sample away required security/audit events while controlling high-volume success logs.
- [ ] `MC-051-T06` Route logs to approved sinks with buffering/backpressure that cannot exhaust application memory.
- [ ] `MC-051-T07` Include enough correlation to reconstruct an admission across authn, policy, provenance, persistence, and forwarding without logging entire sensitive payloads.
- [ ] `MC-051-T08` Add tests that inspect emitted logs for required fields, tenant isolation, secret absence, bounded field lengths, and malformed-input safety.
- [ ] `MC-051-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- [ ] `MC-051-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- [ ] `MC-051-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- [ ] `MC-051-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- [ ] `MC-051-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.

### Definition of done / acceptance evidence

- [ ] `MC-051-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-051-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-051-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-051-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-051-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-051-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-051-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-052 — Distributed tracing/context propagation

**Severity:** High  
**Related controls:** C074  
**Gap statement:** No trace/span propagation is present across admission, policy, provenance, audit, or deployment boundaries.  

### Implementation checklist

- [ ] `MC-052-T01` Adopt W3C Trace Context/OpenTelemetry or organisational standard and propagate trace/span context through admission, identity, policy, provenance/registry, storage, audit, and INV-63 calls.
- [ ] `MC-052-T02` Create spans for major stages with stable names and attributes such as outcome/reason class, dependency, protocol version, and bounded manifest metadata.
- [ ] `MC-052-T03` Never attach tokens, full manifests, secrets, or unbounded/high-cardinality payloads to spans.
- [ ] `MC-052-T04` Propagate baggage only for explicitly approved low-cardinality context; do not use baggage as an authorization source.
- [ ] `MC-052-T05` Link asynchronous outbox/forwarding spans to the originating admission trace/event using span links or persisted correlation IDs.
- [ ] `MC-052-T06` Define trace sampling that keeps errors/security denials at adequate rates while controlling ordinary high-volume traffic.
- [ ] `MC-052-T07` Export trace IDs in structured logs and audit metadata where policy permits correlation.
- [ ] `MC-052-T08` Add integration tests proving context survives each protocol boundary and is not trusted when supplied by unauthenticated callers.
- [ ] `MC-052-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- [ ] `MC-052-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- [ ] `MC-052-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- [ ] `MC-052-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- [ ] `MC-052-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.

### Definition of done / acceptance evidence

- [ ] `MC-052-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-052-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-052-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-052-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-052-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-052-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-052-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-053 — Decision explainability/policy linkage view

**Severity:** High  
**Related controls:** C076-C078  
**Gap statement:** Reasons exist, but there is no operator explain view linking a decision to authenticated principal, exact policy/config version, provenance result, topology, and constraints.  
**Key cross-component dependencies:** MC-014, MC-033, MC-069  

### Implementation checklist

- [ ] `MC-053-T01` Define an explain record keyed by admission/audit event ID that links authenticated principal, requested operation, tenant/lattice/workload, manifest/artifact digest, and source/GitOps revision.
- [ ] `MC-053-T02` Capture exact RBAC bindings/capabilities and policy bundle/config revision that were evaluated, including deny/allow precedence.
- [ ] `MC-053-T03` Capture registry/signer/provenance checks with immutable digest and verifier result, without exposing secrets or unnecessary certificate content.
- [ ] `MC-053-T04` Capture quota/capacity decisions, dependency/degraded state, topology/site constraints, and forwarding disposition.
- [ ] `MC-053-T05` Provide a bounded operator query/view that renders machine reason codes into a human-readable decision tree while retaining raw structured evidence.
- [ ] `MC-053-T06` Enforce tenant/scope-aware authorization for explain data because it may reveal policy and infrastructure metadata.
- [ ] `MC-053-T07` Make explain data immutable or derived from immutable audit/event state so retrospective explanations cannot drift after policy changes.
- [ ] `MC-053-T08` Add tests verifying every denial and admission can be explained completely and the explanation references the exact versions used at decision time.
- [ ] `MC-053-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- [ ] `MC-053-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- [ ] `MC-053-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- [ ] `MC-053-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- [ ] `MC-053-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.

### Definition of done / acceptance evidence

- [ ] `MC-053-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-053-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-053-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-053-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-053-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-053-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-053-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-054 — Telemetry retention/privacy/export policy and dashboards/alerts

**Severity:** High  
**Related controls:** C079-C080  
**Gap statement:** No retention/sampling/privacy configuration, dashboards, alerts, or incident-oriented signal separation exists.  

### Implementation checklist

- [ ] `MC-054-T01` Classify telemetry by data sensitivity and define retention periods separately for metrics, logs, traces, audit events, and explain/inventory data.
- [ ] `MC-054-T02` Define tenant/PII handling, hashing/pseudonymization, permitted attributes, geographic residency, and access controls for telemetry backends.
- [ ] `MC-054-T03` Define sampling rules for traces/logs and guarantee required security/audit evidence is not sampled away.
- [ ] `MC-054-T04` Configure export buffering, retry, disk spool limits, and drop policy so telemetry outages cannot cause unbounded resource growth or silently discard mandated audit data.
- [ ] `MC-054-T05` Create dashboards for admission volume/latency, denials by class, dependency health, audit/outbox backlog, saturation, policy/config revision, and emergency state.
- [ ] `MC-054-T06` Create alerts that distinguish capacity load, dependency degradation, policy rejection spikes, authentication attack signals, audit-integrity failure, and software defects.
- [ ] `MC-054-T07` Define alert thresholds, routing, severity, deduplication, runbook links, and SLO burn-rate alerts.
- [ ] `MC-054-T08` Periodically test dashboard queries and synthetic alerts in CI/staging to detect observability drift.
- [ ] `MC-054-T09` Define a stable telemetry schema with data classification, tenant isolation, privacy/redaction, retention, and export controls.
- [ ] `MC-054-T10` Correlate metrics/logs/traces/audit/explain records using bounded stable identifiers without making high-cardinality values default metric labels.
- [ ] `MC-054-T11` Instrument normal, denied, degraded, dependency-failed, overloaded, security-attack, and software-defect states distinctly.
- [ ] `MC-054-T12` Ensure telemetry/export failure cannot block security-critical processing or cause unbounded resource growth; audit data follows its stronger durability rule.
- [ ] `MC-054-T13` Provide dashboards/alerts or operator views with explicit ownership and linked runbooks, then test them synthetically.

### Definition of done / acceptance evidence

- [ ] `MC-054-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-054-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-054-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-054-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-054-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-054-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-054-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Testing, certification, release, and operations

## MC-055 — Public-interface contract test suite

**Severity:** High  
**Related controls:** C082  
**Gap statement:** Local unit tests now cover the engine, but no schema-driven contract tests exist for admit/RBAC/audit APIs.  

### Implementation checklist

- [ ] `MC-055-T01` Generate contract tests directly from the published admission, RBAC, audit, status, and administrative schemas.
- [ ] `MC-055-T02` Test every required field, optional field, boundary size/count, enum, version, unknown-field rule, and canonicalization constraint.
- [ ] `MC-055-T03` Include authorization matrices proving each operation denies principals missing required capability/scope.
- [ ] `MC-055-T04` Include stable error-code assertions for validation, authn/authz, conflict, quota, timeout, dependency, overload, and internal failures.
- [ ] `MC-055-T05` Run the same fixtures against in-process handlers and deployed service endpoints to detect adapter/serialization drift.
- [ ] `MC-055-T06` Maintain golden compatibility fixtures for supported older protocol versions.
- [ ] `MC-055-T07` Include malformed-wire and truncated-message cases rather than testing only deserialized application objects.
- [ ] `MC-055-T08` Publish machine-readable contract-test results and fail release on any externally claimed interface mismatch.
- [ ] `MC-055-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-055-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-055-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-055-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-055-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-055-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-055-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-055-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-055-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-055-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-055-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-055-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-056 — End-to-end integration suite

**Severity:** Critical  
**Related controls:** C030, C083  
**Gap statement:** No tests exercise a real identity provider, policy engine, provenance verifier, registry, audit store, deployment manager, or wasmCloud lattice.  
**Key cross-component dependencies:** MC-019, MC-020, MC-025, MC-029, MC-033, MC-038  

### Implementation checklist

- [ ] `MC-056-T01` Stand up an end-to-end test environment containing a real/test identity provider, GAP-13 policy engine, registry, GAP-07 provenance verifier, durable stores, INV-63 deployment manager, and representative wasmCloud lattice.
- [ ] `MC-056-T02` Exercise the entire path from authenticated GitOps/API request through admission, durable audit, downstream forwarding, reconciliation acknowledgement, and inventory visibility.
- [ ] `MC-056-T03` Verify a policy/registry/signer/RBAC denial never reaches the deployment manager and produces complete audit/explain evidence.
- [ ] `MC-056-T04` Verify admitted artifacts are identified by immutable digest and the same digest reaches the downstream deployment path.
- [ ] `MC-056-T05` Inject each adjacent dependency failure and assert documented degraded/fail-closed behavior.
- [ ] `MC-056-T06` Exercise configuration/RBAC/signer rotation and prove new revisions propagate without inconsistent mixed decisions.
- [ ] `MC-056-T07` Run tenant-isolation scenarios with at least two organisations/tenants/lattices concurrently.
- [ ] `MC-056-T08` Retain service logs/traces/audit exports plus machine test results as release evidence.
- [ ] `MC-056-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-056-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-056-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-056-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-056-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-056-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-056-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-056-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-056-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-056-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-056-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-056-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-057 — Compatibility/platform test matrix

**Severity:** High  
**Related controls:** C084, C093  
**Gap statement:** No CI matrix validates supported Python/runtime versions, OS/CPU architectures, wasmCloud/Cosmonic versions, or protocol combinations.  

### Implementation checklist

- [ ] `MC-057-T01` Define the supported matrix for Python/runtime versions, OS distributions, CPU architectures, container runtime/orchestrator, wasmCloud/Cosmonic versions, and all adjacent protocol versions.
- [ ] `MC-057-T02` Classify combinations as fully supported, limited/experimental, or explicitly unsupported; do not imply support from untested portability.
- [ ] `MC-057-T03` Run unit/contract/integration smoke tests on every supported baseline combination in CI.
- [ ] `MC-057-T04` Include at least the architectures/sites actually used in production, including ARM64 if edge deployments depend on it.
- [ ] `MC-057-T05` Validate TLS/crypto/provider behavior across platforms where library/backend differences can affect security.
- [ ] `MC-057-T06` Run schema/protocol compatibility tests across N/N-1 rolling upgrade combinations.
- [ ] `MC-057-T07` Record matrix results and exact dependency versions in release metadata.
- [ ] `MC-057-T08` Block publication of a support claim when its matrix job is missing, skipped, or failing.
- [ ] `MC-057-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-057-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-057-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-057-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-057-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-057-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-057-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-057-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-057-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-057-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-057-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-057-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-058 — Distributed concurrency/race suite

**Severity:** High  
**Related controls:** C086  
**Gap statement:** v4.2.0 adds an in-process concurrency test, but no multi-process/multi-node race, failover, duplicate-delivery, or stale-leader suite exists.  

### Implementation checklist

- [ ] `MC-058-T01` Build multi-process/multi-node tests against the real durable coordination/store layer rather than only Python threads.
- [ ] `MC-058-T02` Test concurrent admissions for the same idempotency key, same manifest, different tenants, and conflicting policy/config revisions.
- [ ] `MC-058-T03` Test concurrent RBAC/config mutations with stale revision tokens and verify one deterministic outcome without lost updates.
- [ ] `MC-058-T04` Test leader failover/lease expiry/fencing where applicable, including delayed stale leader writes after failover.
- [ ] `MC-058-T05` Test duplicate downstream sends, lost acknowledgements, outbox replay, and deduplication across process restart.
- [ ] `MC-058-T06` Test concurrent audit appends/query/export and preserve global/partition ordering guarantees as specified.
- [ ] `MC-058-T07` Use stress/race tooling and repeated randomized scheduling to increase probability of exposing timing defects.
- [ ] `MC-058-T08` Assert invariants automatically: no unauthorized forward, no duplicate logical transition, no audit gap, no cross-tenant state leak.
- [ ] `MC-058-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-058-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-058-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-058-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-058-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-058-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-058-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-058-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-058-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-058-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-058-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-058-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-059 — Disaster/partition/reconnect certification suite

**Severity:** High  
**Related controls:** C089  
**Gap statement:** No restore, region/site loss, network partition, reconnect, or degraded-control-plane acceptance tests exist.  

### Implementation checklist

- [ ] `MC-059-T01` Define certified recovery scenarios for process/node loss, datastore replica loss, zone/site loss, network partition, dependency region loss, and complete control-plane restore.
- [ ] `MC-059-T02` Specify RTO/RPO and acceptable degraded capabilities for each scenario.
- [ ] `MC-059-T03` Test backup restore into clean infrastructure and verify audit chain, policy/config revisions, RBAC, inventory, and pending outbox state.
- [ ] `MC-059-T04` Test site partition where local control continues only within documented leases/staleness limits, then reconcile deterministically on reconnect.
- [ ] `MC-059-T05` Test DNS/time/KMS/identity/policy outages and recovery sequencing without security bypass.
- [ ] `MC-059-T06` Test stale controller and duplicate event conditions after reconnect/failover.
- [ ] `MC-059-T07` Validate operator runbooks by having a separate operator execute them from documented instructions rather than test-author knowledge.
- [ ] `MC-059-T08` Produce signed/machine-readable disaster-test evidence with timestamps, environment build, achieved RTO/RPO, and any deviations.
- [ ] `MC-059-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-059-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-059-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-059-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-059-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-059-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-059-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-059-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-059-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-059-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-059-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-059-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-060 — Full machine-readable production acceptance evidence bundle

**Severity:** High  
**Related controls:** C090  
**Gap statement:** v4.2.0 now includes `VERIFICATION.json` for local checks, but no generated 100-item production acceptance evidence exists; the bundled full conformance tests require external `pk_core` and skip when it is absent.  
**Key cross-component dependencies:** MC-007, MC-055, MC-056, MC-057, MC-058, MC-059  

### Implementation checklist

- [ ] `MC-060-T01` Define a versioned acceptance-evidence schema covering all C001-C100 items and MC closure status.
- [ ] `MC-060-T02` For each control, include status, evidence type, artifact URI/path, cryptographic digest, test/run ID, environment, timestamp, tool version, and responsible owner/reviewer.
- [ ] `MC-060-T03` Distinguish PASS, FAIL, NOT_APPLICABLE, WAIVED, and BLOCKED states; require rationale/approval/expiry for non-PASS dispositions.
- [ ] `MC-060-T04` Generate evidence automatically from CI, security scans, benchmarks, compatibility matrix, chaos/disaster tests, and documentation checks where possible.
- [ ] `MC-060-T05` Include `pk_core` conformance evidence or vendor the required runtime so production certification cannot silently skip unavailable tests.
- [ ] `MC-060-T06` Chain/sign the evidence bundle or include it in signed release provenance to prevent post-release editing.
- [ ] `MC-060-T07` Validate that every normative SHALL and every C001-C100 control is covered before producing a production gate result.
- [ ] `MC-060-T08` Archive evidence per release with enough environment metadata to reproduce or investigate the result.
- [ ] `MC-060-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-060-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-060-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-060-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-060-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-060-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-060-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-060-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-060-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-060-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-060-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-060-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-061 — CI/CD release pipeline and staged rollout artifacts

**Severity:** Critical  
**Related controls:** C092  
**Gap statement:** No pipeline configuration, signed build, canary/staged rollout, deployment manifest, or automated rollback integration is included.  
**Key cross-component dependencies:** MC-060, MC-062, MC-068  

### Implementation checklist

- [ ] `MC-061-T01` Create CI stages for lint/static analysis, unit/property/fuzz tests, schema/contract tests, integration tests, security scans, SBOM/provenance, compatibility matrix, performance gates, packaging, and evidence generation.
- [ ] `MC-061-T02` Build release artifacts from a clean, pinned environment and sign/attest them; never promote locally built untracked binaries.
- [ ] `MC-061-T03` Define environment promotion dev -> test -> staging -> canary -> production with immutable artifact digests.
- [ ] `MC-061-T04` Implement staged/canary rollout using health/SLO/security signals and automatic halt/rollback thresholds.
- [ ] `MC-061-T05` Pin deployment manifests/config schema versions and record exact config/policy revisions per rollout.
- [ ] `MC-061-T06` Implement automated rollback that restores the prior known-good artifact/config without bypassing audit or authorization.
- [ ] `MC-061-T07` Require protected-branch/code-owner approvals and production release authorization by designated roles.
- [ ] `MC-061-T08` Emit machine-readable pipeline/release metadata into the acceptance evidence bundle.
- [ ] `MC-061-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-061-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-061-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-061-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-061-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-061-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-061-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-061-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-061-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-061-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-061-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-061-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-062 — Vulnerability/SBOM/patch/EOL program artifacts

**Severity:** High  
**Related controls:** C094  
**Gap statement:** No SBOM, dependency vulnerability policy, patch SLA, supported-version policy, or EOL schedule is packaged.  

### Implementation checklist

- [ ] `MC-062-T01` Generate SPDX or CycloneDX SBOMs for application dependencies, base image/OS packages, and bundled tools for every release artifact.
- [ ] `MC-062-T02` Run SCA/vulnerability scanning with an approved severity/EPSS/exploitability policy and fail builds according to defined thresholds.
- [ ] `MC-062-T03` Define patch SLAs by severity and exposure, including emergency out-of-band release procedures for actively exploited vulnerabilities.
- [ ] `MC-062-T04` Track supported release branches, minimum dependency versions, end-of-standard-support, and end-of-life dates.
- [ ] `MC-062-T05` Monitor new CVEs continuously against released SBOMs, not only at build time.
- [ ] `MC-062-T06` Define exception/false-positive workflow with owner, technical rationale, compensating control, expiry, and re-evaluation.
- [ ] `MC-062-T07` Include license/third-party notice compliance scanning and provenance verification in dependency update workflows.
- [ ] `MC-062-T08` Publish vulnerability/SBOM status and unresolved approved exceptions into release evidence.
- [ ] `MC-062-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-062-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-062-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-062-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-062-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-062-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-062-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-062-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-062-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-062-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-062-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-062-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-063 — Backup/restore/migration/reconstruction runbook

**Severity:** Critical  
**Related controls:** C095  
**Gap statement:** No procedure or tooling exists because durable state itself is absent.  
**Key cross-component dependencies:** MC-038, MC-005  

### Implementation checklist

- [ ] `MC-063-T01` Inventory every durable dataset: audit/event log, RBAC/policy data, registry/signer policy, configuration history, inventory projections, outbox/pending operations, and cryptographic metadata.
- [ ] `MC-063-T02` Define backup frequency, retention, encryption, immutability, geographic location, RPO/RTO, and dependency ordering for each dataset.
- [ ] `MC-063-T03` Implement automated backups with success/failure monitoring and independent verification that backup objects are readable and complete.
- [ ] `MC-063-T04` Document restore sequencing, including keys/certificates, datastore schemas, snapshots/log replay, config activation, and dependency reattachment.
- [ ] `MC-063-T05` Define schema migration forward/backward compatibility and rollback strategy for persisted data.
- [ ] `MC-063-T06` Provide reconstruction procedure from authoritative event log when projections/indexes are lost.
- [ ] `MC-063-T07` Perform periodic clean-room restore tests and verify audit integrity plus pending/idempotency state after recovery.
- [ ] `MC-063-T08` Record backup/restore test evidence, achieved RPO/RTO, and operator sign-off.
- [ ] `MC-063-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-063-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-063-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-063-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-063-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-063-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-063-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-063-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-063-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-063-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-063-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-063-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-064 — Complete day-0/day-1/day-2 operational runbooks

**Severity:** High  
**Related controls:** C096  
**Gap statement:** README provides only brief commands; production bootstrap, deployment, rotation, failure handling, capacity, restore, and maintenance procedures are missing.  

### Implementation checklist

- [ ] `MC-064-T01` Create Day-0 runbook for infrastructure prerequisites, IAM/service identities, certificates, KMS/secrets, stores, DNS/network policy, installation, bootstrap config, and initial trust roots.
- [ ] `MC-064-T02` Create Day-1 runbook for deployment, smoke validation, staged rollout, config/policy activation, initial RBAC/registry/signer setup, and production readiness verification.
- [ ] `MC-064-T03` Create Day-2 runbooks for upgrades, scaling, certificate/key rotation, policy changes, tenant onboarding/offboarding, capacity management, backup verification, and routine maintenance.
- [ ] `MC-064-T04` Add troubleshooting procedures keyed to stable error codes, alerts, dependency health states, and common failure signatures.
- [ ] `MC-064-T05` Include explicit commands/API examples with expected outputs and safety checks; avoid destructive commands without preconditions/rollback.
- [ ] `MC-064-T06` Include rollback and emergency freeze/quarantine procedures, plus criteria for resuming normal operation.
- [ ] `MC-064-T07` Link every alert/dashboard to the relevant runbook section and owner/escalation route.
- [ ] `MC-064-T08` Test runbooks during game days and update them from observed operator gaps.
- [ ] `MC-064-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-064-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-064-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-064-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-064-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-064-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-064-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-064-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-064-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-064-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-064-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-064-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-065 — Incident response/on-call runbook

**Severity:** High  
**Related controls:** C097  
**Gap statement:** No severity model, paging rules, containment steps, evidence preservation, recovery criteria, or communications workflow exists.  

### Implementation checklist

- [ ] `MC-065-T01` Define incident severity levels using customer/security/data-integrity/availability impact and examples specific to unauthorized forwarding, audit integrity failure, identity compromise, and multi-tenant exposure.
- [ ] `MC-065-T02` Define paging targets, primary/secondary rotations, acknowledgement/escalation timers, and dependency-team engagement paths.
- [ ] `MC-065-T03` Create containment playbooks for global admission freeze, tenant/lattice quarantine, signer/registry revocation, credential rotation, and deployment forwarding disable.
- [ ] `MC-065-T04` Define evidence-preservation steps for audit anchors, logs, traces, config/policy snapshots, identity records, and affected artifact digests.
- [ ] `MC-065-T05` Define recovery criteria and required verification before clearing emergency controls or returning to normal traffic.
- [ ] `MC-065-T06` Define communications roles/channels, customer/compliance notification decision process, and status cadence.
- [ ] `MC-065-T07` Require post-incident review with root cause, control failures, corrective actions, owners, due dates, and threat-model/runbook updates.
- [ ] `MC-065-T08` Exercise the runbook with tabletop and live game-day scenarios at a scheduled cadence.
- [ ] `MC-065-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-065-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-065-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-065-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-065-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-065-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-065-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-065-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-065-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-065-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-065-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-065-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-066 — Recurring review automation/evidence

**Severity:** Medium  
**Related controls:** C098  
**Gap statement:** No scheduled access, policy, dependency, configuration, and architecture review mechanism or retained results are present.  

### Implementation checklist

- [ ] `MC-066-T01` Define review frequencies and owners for access/RBAC, elevated grants, break-glass accounts, registry/signer trust, policy bundles, dependencies, config drift, architecture, threat model, and capacity.
- [ ] `MC-066-T02` Automate extraction of current state and diffs so reviewers assess effective configuration rather than manually assembled screenshots.
- [ ] `MC-066-T03` Flag stale/unused privileges, expired temporary grants, unknown signers/registries, old protocol versions, unsupported dependencies, and unowned exceptions.
- [ ] `MC-066-T04` Require reviewer disposition, remediation owner, due date, and evidence for every finding.
- [ ] `MC-066-T05` Retain immutable review results and link material findings to tickets/waivers/incidents.
- [ ] `MC-066-T06` Escalate overdue critical findings and block production exit when required recurring reviews are stale.
- [ ] `MC-066-T07` Add review status to governance dashboards and acceptance evidence.
- [ ] `MC-066-T08` Periodically validate the automation itself against source systems to detect blind spots or partial data extraction.
- [ ] `MC-066-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-066-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-066-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-066-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-066-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-066-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-066-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-066-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-066-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-066-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-066-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-066-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-067 — Exception/waiver/technical-debt register

**Severity:** Medium  
**Related controls:** C099  
**Gap statement:** No machine-readable waiver owner, rationale, expiry, compensating control, or deprecation register exists.  

### Implementation checklist

- [ ] `MC-067-T01` Create a machine-readable register with unique waiver/debt ID, affected requirement/control, scope/environment, owner, approver, rationale, risk rating, compensating controls, creation date, expiry, and remediation plan.
- [ ] `MC-067-T02` Prohibit indefinite waivers; require explicit expiry/review date and automated notification before expiration.
- [ ] `MC-067-T03` Differentiate temporary security exceptions, functional limitations, technical debt, and deprecation commitments.
- [ ] `MC-067-T04` Link each register entry to RTM rows and production gate results so waived controls cannot appear as ordinary PASS.
- [ ] `MC-067-T05` Block release on expired waivers or waivers missing required approval for their risk level.
- [ ] `MC-067-T06` Provide trend reporting for open/aging debt and repeated extensions.
- [ ] `MC-067-T07` Require closure evidence demonstrating the underlying control is implemented and verified before marking a waiver resolved.
- [ ] `MC-067-T08` Archive historical entries without deleting their relationship to prior releases.
- [ ] `MC-067-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-067-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-067-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-067-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-067-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-067-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-067-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-067-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-067-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-067-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-067-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-067-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-068 — Formal production exit gate artifact

**Severity:** Critical  
**Related controls:** C100  
**Gap statement:** No signed/generated gate proves architecture, security, resilience, performance, observability, testing, rollback, and ownership readiness; current generic checklist satisfaction is insufficient production evidence.  
**Key cross-component dependencies:** MC-007, MC-060, MC-061, MC-064, MC-065  

### Implementation checklist

- [ ] `MC-068-T01` Define a signed/generated production exit-gate schema with independent sections for architecture, requirements, interfaces, implementation/config, security, resilience, performance, observability, testing, rollback, operations, ownership, and governance.
- [ ] `MC-068-T02` Require every C001-C100 item to resolve to PASS, approved NOT_APPLICABLE, or unexpired approved waiver; BLOCKED/FAIL prevents production GO.
- [ ] `MC-068-T03` Consume evidence from the RTM/acceptance bundle by immutable digest rather than manually copying status into a report.
- [ ] `MC-068-T04` Require named approvals from service owner, architecture, security, SRE/operations, and release authority according to organisational policy.
- [ ] `MC-068-T05` Include exact artifact digest, source revision, deployment manifest version, config/policy revision, compatibility matrix, and evidence-bundle digest.
- [ ] `MC-068-T06` Automate objective checks and isolate subjective approvals so humans cannot override missing machine evidence without a formal waiver.
- [ ] `MC-068-T07` Generate a reproducible gate report with timestamp and decision inputs and retain it with the release.
- [ ] `MC-068-T08` Prevent deployment/promotion automation from bypassing a non-GO gate except through an explicitly audited break-glass process.
- [ ] `MC-068-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-068-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-068-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-068-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-068-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-068-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-068-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-068-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-068-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-068-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-068-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-068-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-069 — Cross-lattice inventory service

**Severity:** High  
**Related controls:** C002, C011, C021  
**Gap statement:** `contract.py` says INV-66 owns cross-lattice inventory, but the implementation only retains admitted manifest copies and offers no queryable, durable inventory model.  
**Key cross-component dependencies:** MC-019, MC-038  

### Implementation checklist

- [ ] `MC-069-T01` Define a durable cross-lattice inventory model with organisation/tenant, site, lattice, workload/application, component/provider, artifact digest, desired revision, observed revision/state, and timestamps.
- [ ] `MC-069-T02` Distinguish desired/admitted state from downstream observed runtime state; record source and freshness for each field.
- [ ] `MC-069-T03` Ingest updates from INV-63/wasmCloud reconciliation using authenticated event/query mechanisms with idempotent versioned updates.
- [ ] `MC-069-T04` Provide scoped query APIs for tenant/lattice/workload/artifact/revision and pagination suitable for large fleets.
- [ ] `MC-069-T05` Enforce tenant isolation and administrative scope on inventory reads; avoid global inventory disclosure by default.
- [ ] `MC-069-T06` Define stale/offline semantics and last-observed timestamps for disconnected sites.
- [ ] `MC-069-T07` Correlate inventory entries with admission event, GitOps commit, policy/config revision, and deployment acknowledgement.
- [ ] `MC-069-T08` Add reconciliation tests for out-of-order/duplicate updates, site reconnect, deletion/tombstone, drift, and projection rebuild from source events.
- [ ] `MC-069-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-069-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-069-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-069-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-069-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-069-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-069-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-069-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-069-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-069-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-069-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-069-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-070 — Audit query/retention/export service

**Severity:** High  
**Related controls:** C049, C079, C095  
**Gap statement:** The local audit snapshot has no retention class, index/query API, immutable export, SIEM integration, legal hold, or archival lifecycle.  
**Key cross-component dependencies:** MC-014, MC-035, MC-038  

### Implementation checklist

- [ ] `MC-070-T01` Implement durable indexed audit storage and a read/query service independent from the in-process `audit` snapshot.
- [ ] `MC-070-T02` Define retention classes by event type/tenant/regulatory need, hot vs archive tiers, legal hold, and immutable deletion governance.
- [ ] `MC-070-T03` Index common dimensions such as time, tenant, lattice, principal, workload, action/outcome, request/trace ID, artifact digest, and event ID while controlling cost/cardinality.
- [ ] `MC-070-T04` Provide cursor-based pagination and bounded query ranges; protect service with authorization, rate limits, and query-cost controls.
- [ ] `MC-070-T05` Provide cryptographically verifiable export bundles including event segment roots/anchors, schema version, and manifest digest.
- [ ] `MC-070-T06` Implement SIEM/security-lake export with durable checkpointing, idempotent delivery, retries, backpressure, and dead-letter visibility.
- [ ] `MC-070-T07` Ensure retention/archival operations preserve tamper-evident chain/anchor verification and legal-hold records.
- [ ] `MC-070-T08` Add tests for large-range queries, tenant access control, archived retrieval, export verification, SIEM outage/recovery, and restore from backup.
- [ ] `MC-070-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-070-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-070-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-070-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-070-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-070-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-070-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-070-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-070-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-070-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-070-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-070-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

## MC-071 — Repository license/notice metadata

**Severity:** Medium  
**Related controls:** repository governance  
**Gap statement:** No `LICENSE` or `NOTICE` is bundled, so redistribution and third-party compliance terms are not established by this archive. *(repository governance artifact; not represented by a dedicated checklist item)*  

### Implementation checklist

- [ ] `MC-071-T01` Select and document the repository/project license with legal/owner approval and add the complete `LICENSE` text at repository root.
- [ ] `MC-071-T02` Add `NOTICE` when required by the chosen license or bundled third-party works and include copyright/attribution information.
- [ ] `MC-071-T03` Inventory third-party dependencies/assets and verify their licenses are compatible with distribution and intended deployment.
- [ ] `MC-071-T04` Generate/maintain third-party notices from the dependency lock/SBOM to prevent manual drift.
- [ ] `MC-071-T05` Add source-file headers only where organisational policy/license requires them; avoid inconsistent or misleading headers.
- [ ] `MC-071-T06` Add packaging rules ensuring LICENSE/NOTICE/third-party notices ship in source and binary/container distributions where required.
- [ ] `MC-071-T07` Add CI compliance checks for missing/forbidden licenses and new dependency-license changes.
- [ ] `MC-071-T08` Record license metadata in `pyproject.toml`, SBOM, release manifest, and README.
- [ ] `MC-071-T09` Assign a stable test/evidence ID to each acceptance condition and link it to the RTM and release evidence bundle.
- [ ] `MC-071-T10` Automate the control in CI/CD or scheduled operations wherever objective verification is possible; treat skipped tests as non-evidence unless explicitly approved.
- [ ] `MC-071-T11` Exercise positive, negative, boundary, security, failure, recovery, and upgrade/rollback paths appropriate to the component.
- [ ] `MC-071-T12` Retain machine-readable results, environment/tool versions, raw logs where needed, and cryptographic digests of critical evidence.
- [ ] `MC-071-T13` Define ownership, review/renewal cadence, waiver handling, and release-blocking conditions for stale or failed evidence.

### Definition of done / acceptance evidence

- [ ] `MC-071-D01` Implementation/artifact is stored in version control at a documented path, included in the release BOM where applicable, and protected by normal review controls.
- [ ] `MC-071-D02` All referenced schemas/configs/tests are version-pinned; no acceptance claim depends on an unversioned “latest” external artifact.
- [ ] `MC-071-D03` RTM entries identify the implementation artifact, verification test/evidence IDs, owner, release version, and any approved waiver.
- [ ] `MC-071-D04` Automated verification passes in a clean CI or production-like environment; required tests are not silently skipped because an external tool/dependency is absent.
- [ ] `MC-071-D05` Security/architecture/operations review is complete at the level required by severity, with unresolved risks captured in the waiver/debt register.
- [ ] `MC-071-D06` Release acceptance evidence contains immutable hashes/IDs for the artifacts and test runs that close this component.
- [ ] `MC-071-D07` Documentation/runbooks are updated so an operator can inspect status, diagnose failure, and perform rollback/recovery without relying on implementation-author memory.

---

# Program-level closure gate

The 71-component remediation program is complete only when all applicable component checklists satisfy their Definition of Done and the following aggregate gates pass:

- [ ] `INV66-PROG-01` All 71 MC IDs have an RTM disposition and no Critical/High item is silently omitted.
- [ ] `INV66-PROG-02` All C001-C100 controls have machine-readable evidence or an approved, unexpired N/A/waiver disposition.
- [ ] `INV66-PROG-03` Admission, RBAC, audit, inventory, configuration, and administrative interfaces are versioned typed contracts with compatibility tests.
- [ ] `INV66-PROG-04` Authentication, capability-based authorization, policy evaluation, artifact signature/provenance verification, and tenant isolation are enforced end to end.
- [ ] `INV66-PROG-05` Authoritative state and audit data are durable, recoverable, tamper-evident, replicated as required, and validated by crash/partition/restore tests.
- [ ] `INV66-PROG-06` No unadmitted manifest can be forwarded under success, failure, retry, restart, failover, stale-leader, or partition scenarios.
- [ ] `INV66-PROG-07` Performance and capacity tests demonstrate the approved latency/throughput/resource thresholds and release regression gates pass.
- [ ] `INV66-PROG-08` Health, metrics, logs, traces, explain views, dashboards, alerts, retention/privacy controls, and runbook links are operationally validated.
- [ ] `INV66-PROG-09` E2E, compatibility, fuzz/security, concurrency, fault-injection, disaster/reconnect, benchmark/soak, backup/restore, and rollout/rollback suites pass in production-like environments.
- [ ] `INV66-PROG-10` SBOM, vulnerability status, license/notice, signed build/provenance, deployment artifacts, config/policy revisions, and full acceptance evidence are attached to the release.
- [ ] `INV66-PROG-11` Day-0/1/2 and incident runbooks have been exercised by operators; ownership/escalation rotations are live.
- [ ] `INV66-PROG-12` MC-068 production exit gate yields GO with the exact release artifact and evidence-bundle digests intended for production promotion.

## Checklist metrics

- Missing components covered: **71 / 71**
- Critical components: **26**
- High components: **39**
- Medium components: **5**
- Low/conditional components: **1**
- Component-level checkboxes generated: **1,420**
- Program-level gates: **12**
