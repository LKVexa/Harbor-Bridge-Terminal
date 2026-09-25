# SCH-01 v4.2.0 — Comprehensive Missing-Component Implementation Checklist

**Scope:** Every missing/incomplete SCH-01-owned component identified by the 4.2.0 post-update audit, plus every unresolved external prerequisite required for standalone production certification.

**Backlog semantics:** Every checkbox is deliberately **unchecked**. Planning/document creation does not close the underlying production gap. Stable IDs (`MC-xx.Tnn`, `.Vnn`, `.Enn`, `.Dnn`) are suitable for issue tracking, commit messages, evidence manifests, and gate automation.

## Execution conventions

- **Completion:** implementation + automated verification + required evidence; prose intent alone is insufficient.
- **Evidence:** skipped, unavailable, not-run, or unknown verification is not pass.
- **Safety:** authentication, authorization, tenant isolation, attestation, residency, fencing, quota/capacity, and hard execution constraints fail closed.
- **Determinism:** identical immutable input/state/policy snapshots must yield reproducible classification/placement unless a normative requirement explicitly permits otherwise.
- **Atomicity:** decisions that reserve quota/capacity/device/runtime state must be transactionally committed or fenced against distributed races.
- **Traceability:** completion updates the requirements-to-evidence matrix and release-evidence bundle.
- **Compatibility:** public schemas/errors/state/policy/telemetry/audit changes obey the supported-version policy.
- **Waivers:** any deferred mandatory item requires owner, scope, risk, compensating control, approver, and finite expiry; waived is never displayed as passed.

## Recommended dependency order

1. MC-01..MC-06 — provenance, packaging, ownership, ADRs, SHALL requirements, and RTM.
2. MC-07..MC-16 — deployment/lifecycle/version semantics and complete placement capability.
3. MC-17..MC-28 — typed contracts, configuration, identity, authorization, attestation, audit, and adversarial security.
4. MC-29..MC-34 — failure model, resilience controls, durable state, fencing, quarantine, and fault injection.
5. MC-35..MC-36 — reproducible performance/capacity baseline and release thresholds.
6. MC-37..MC-42 — health, metrics, structured logs, traces, explainability, telemetry governance.
7. MC-43..MC-49 — contract/integration/compatibility/fuzz/race/scale evidence and signed release evidence.
8. MC-50..MC-60 — support, rollout, patch/EOL, recovery, runbooks, incident response, review, waivers, exit gate, CI, and supply-chain provenance.
9. EXT-01..EXT-08 — certify external dependencies end-to-end for the intended deployment profile.

## Phase 0 — Provenance, governance, and normative baseline

### MC-01 — Original MASTER.md evidence

**Audit finding:** README 4.1.0 claimed 100 master prompt/workflow documents were carried verbatim, but the supplied archive contains no `MASTER.md`. 4.2.0 corrects the claim and does not fabricate the source.

**Original control coverage:** Evidence provenance; supports C020/C090/C100

#### Engineering implementation checklist

- [ ] **MC-01.T01** — Locate the canonical MASTER.md from the authoritative source repository, release package, artifact store, or signed archival location; do not reconstruct or fabricate missing source evidence.
- [ ] **MC-01.T02** — Record source URI/path, repository commit or release ID, retrieval date, retriever, and chain-of-custody notes.
- [ ] **MC-01.T03** — Compute SHA-256 and verify any available upstream signature or signed release manifest before accepting the artifact.
- [ ] **MC-01.T04** — Compare recovered MASTER.md against CHECKLIST.json and identify additions, omissions, semantic drift, reordered controls, or normalization changes.
- [ ] **MC-01.T05** — Create a machine-readable provenance record linking MASTER.md, CHECKLIST.json, repository version, and the checklist derivation procedure.
- [ ] **MC-01.T06** — Define whether MASTER.md is normative, informative, or historical and document conflict precedence against SHALL requirements, CHECKLIST.json, ADRs, and released code.
- [ ] **MC-01.T07** — Store the evidence as immutable/content-addressed release input rather than mutable runtime configuration.
- [ ] **MC-01.T08** — Add an automated verifier that fails on absence, digest mismatch, substitution, or checklist/provenance mismatch.
- [ ] **MC-01.T09** — Add CI coverage that prevents documentation from claiming verbatim inclusion when the evidence is absent.
- [ ] **MC-01.T10** — Add release-evidence pointers for the applicable controls and exact artifact digest.
- [ ] **MC-01.T11** — If the source cannot be recovered, create a formally approved evidence-gap waiver with owner, impact, compensating evidence, and expiry.
- [ ] **MC-01.T12** — Define archival retention so every supported release can resolve the exact source evidence revision.

#### Component-specific acceptance gates

- [ ] **MC-01.V01** — Canonical source evidence is present and cryptographically identified, or a signed waiver explicitly records the unresolved provenance gap.
- [ ] **MC-01.V02** — Automated verification detects deletion, modification, substitution, or derivation mismatch.
- [ ] **MC-01.V03** — Release evidence traces claimed source controls to an immutable artifact without manual interpretation.

#### Required deliverables / evidence

- [ ] **MC-01.E01** — Produce, version, and reference in release evidence: `MASTER.md or immutable external reference`.
- [ ] **MC-01.E02** — Produce, version, and reference in release evidence: `evidence/master_provenance.json`.
- [ ] **MC-01.E03** — Produce, version, and reference in release evidence: `tools/verify_master_provenance.py`.
- [ ] **MC-01.E04** — Produce, version, and reference in release evidence: `CI provenance/evidence record`.

#### Definition of done

- [ ] **MC-01.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-01.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-01.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-01.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-01.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-01.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-01.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-02 — Reproducible package/install manifest

**Audit finding:** No `pyproject.toml`, lock file, pinned dependency manifest, wheel/sdist metadata, or approved install recipe is present.

**Original control coverage:** C031, C040, C093

#### Engineering implementation checklist

- [ ] **MC-02.T01** — Create pyproject.toml as the canonical build/install manifest with package metadata, Python support window, build backend, and package discovery.
- [ ] **MC-02.T02** — Choose a reproducible dependency strategy using a pinned lock or constraints file with hashes for all production/build/test dependencies.
- [ ] **MC-02.T03** — Separate runtime, optional pk_core integration, development, test, benchmark, and documentation dependency groups.
- [ ] **MC-02.T04** — Enforce supported interpreter versions in package metadata and CI.
- [ ] **MC-02.T05** — Build wheel and sdist from a clean checkout and install each into clean virtual environments without undeclared local dependencies.
- [ ] **MC-02.T06** — Provide hash-verified and offline installation instructions for restricted/disconnected sites.
- [ ] **MC-02.T07** — Single-source the package version so VERSION, import metadata, wheel metadata, tags, and changelog cannot drift.
- [ ] **MC-02.T08** — Verify package contents so required docs/schemas are not accidentally omitted from release artifacts.
- [ ] **MC-02.T09** — Apply reproducible-build controls such as stable archive ordering/timestamps and captured build environment.
- [ ] **MC-02.T10** — Generate dependency inventory/SBOM during packaging.
- [ ] **MC-02.T11** — Add clean-install smoke tests for engine-only and optional pk_core-enabled modes.
- [ ] **MC-02.T12** — Document Windows/Linux installation, virtual environment, upgrade, rollback, and uninstall behavior.
- [ ] **MC-02.T13** — Block release if dependencies are unlocked, hashes missing, metadata inconsistent, or clean-install tests fail.

#### Component-specific acceptance gates

- [ ] **MC-02.V01** — A clean machine can build, install, import, test, and uninstall using only committed manifests and approved artifact sources.
- [ ] **MC-02.V02** — Repeated builds from the same revision produce equivalent package contents/provenance.
- [ ] **MC-02.V03** — CI proves supported Python versions and detects undeclared dependency leakage.

#### Required deliverables / evidence

- [ ] **MC-02.E01** — Produce, version, and reference in release evidence: `pyproject.toml`.
- [ ] **MC-02.E02** — Produce, version, and reference in release evidence: `dependency lock/constraints file`.
- [ ] **MC-02.E03** — Produce, version, and reference in release evidence: `build/install verification scripts`.
- [ ] **MC-02.E04** — Produce, version, and reference in release evidence: `wheel/sdist evidence`.
- [ ] **MC-02.E05** — Produce, version, and reference in release evidence: `packaging guide`.

#### Definition of done

- [ ] **MC-02.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-02.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-02.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-02.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-02.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-02.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-02.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-03 — Accountable owner and escalation record

**Audit finding:** No named service owner, backup owner, escalation path, or on-call mapping exists.

**Original control coverage:** C009, C097

#### Engineering implementation checklist

- [ ] **MC-03.T01** — Register SCH-01 in the service/component catalog with a stable identifier and lifecycle status.
- [ ] **MC-03.T02** — Assign primary accountable owner, backup owner, owning team, architecture authority, and security escalation authority.
- [ ] **MC-03.T03** — Define an on-call/operations contact path for production-impacting failures and security incidents.
- [ ] **MC-03.T04** — Create a RACI for architecture, code, policy, configuration, security, release, incident command, and waivers.
- [ ] **MC-03.T05** — Define ownership boundaries with PLN-02, PLN-04, PLN-05, GAP-02, GAP-03, GAP-10, INV-33, and pk_core.
- [ ] **MC-03.T06** — Define acknowledgement/escalation targets for high-severity incidents and production-gate failures.
- [ ] **MC-03.T07** — Add CODEOWNERS or equivalent controls for policy, schemas, release workflows, security controls, and evidence manifests.
- [ ] **MC-03.T08** — Require designated review for trust-boundary, authorization, placement-policy, attestation, and release-gate changes.
- [ ] **MC-03.T09** — Record owner identifiers in governed metadata without embedding secrets or ephemeral personal data.
- [ ] **MC-03.T10** — Make release readiness fail when required ownership metadata is missing or expired.
- [ ] **MC-03.T11** — Schedule recurring ownership review and require handoff documentation when roles change.
- [ ] **MC-03.T12** — Define who can invoke emergency disable, approve waivers, accept risk, and declare restoration.

#### Component-specific acceptance gates

- [ ] **MC-03.V01** — Every production function and release/security decision has one accountable role and a backup path.
- [ ] **MC-03.V02** — A tabletop incident reaches the correct owner/escalation chain without repository archaeology.
- [ ] **MC-03.V03** — Release automation detects missing ownership metadata.

#### Required deliverables / evidence

- [ ] **MC-03.E01** — Produce, version, and reference in release evidence: `OWNERSHIP.md/service catalog entry`.
- [ ] **MC-03.E02** — Produce, version, and reference in release evidence: `CODEOWNERS`.
- [ ] **MC-03.E03** — Produce, version, and reference in release evidence: `RACI matrix`.
- [ ] **MC-03.E04** — Produce, version, and reference in release evidence: `on-call/escalation record`.

#### Definition of done

- [ ] **MC-03.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-03.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-03.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-03.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-03.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-03.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-03.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-04 — Approved architecture decision record

**Audit finding:** `ARCHITECTURE.md` documents the current design, but there is no approval record, decision status, approver, supersession chain, or governed ADR covering the full source function.

**Original control coverage:** C010, C098

#### Engineering implementation checklist

- [ ] **MC-04.T01** — Create a governed ADR covering classifier, runtime selector, placement engine, policy input, topology/data/accelerator awareness, and execution-boundary responsibilities.
- [ ] **MC-04.T02** — Record ADR status, date, scope, owner, approvers, review date, and supersession metadata.
- [ ] **MC-04.T03** — Document decision drivers including isolation, determinism, latency, locality, data residency, fairness, accelerators, disconnected operation, observability, and failure containment.
- [ ] **MC-04.T04** — Document considered alternatives and rejection rationale for centralized/distributed placement, hard-coded/policy-driven rules, and in-memory/durable state.
- [ ] **MC-04.T05** — Define authoritative sources of truth for workload intent, node capabilities/attestation, topology, quotas, runtime registry, policy, and occupancy/leases.
- [ ] **MC-04.T06** — Define consistency assumptions and transaction boundaries between scheduler selection and execution-side admission.
- [ ] **MC-04.T07** — Capture trust boundaries, identities, authentication/authorization, attestation, and fail-closed behavior.
- [ ] **MC-04.T08** — Capture durability, fencing, restart, partition, degraded-mode, and recovery decisions.
- [ ] **MC-04.T09** — Define extension points for new runtimes, accelerators, policy revisions, providers, and schemas.
- [ ] **MC-04.T10** — Record performance/operational tradeoffs, known limitations, and explicit non-goals.
- [ ] **MC-04.T11** — Link ADR claims to SHALL requirements and verification evidence.
- [ ] **MC-04.T12** — Require architecture/security approval before Accepted status and superseding ADRs for material design changes.

#### Component-specific acceptance gates

- [ ] **MC-04.V01** — The ADR is formally Accepted by designated architecture/security approvers.
- [ ] **MC-04.V02** — Code/requirements are consistent with the ADR or explicitly covered by tracked deviations.
- [ ] **MC-04.V03** — A reviewer can derive ownership, trust boundaries, state authority, and failure strategy from the ADR.

#### Required deliverables / evidence

- [ ] **MC-04.E01** — Produce, version, and reference in release evidence: `docs/adr/ADR-SCH01.md`.
- [ ] **MC-04.E02** — Produce, version, and reference in release evidence: `approval record`.
- [ ] **MC-04.E03** — Produce, version, and reference in release evidence: `ADR index/supersession chain`.
- [ ] **MC-04.E04** — Produce, version, and reference in release evidence: `requirements trace links`.

#### Definition of done

- [ ] **MC-04.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-04.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-04.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-04.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-04.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-04.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-04.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-05 — System-specific SHALL requirements specification

**Audit finding:** `CHECKLIST.json` contains generic requirements, not a normalized SCH-01 functional/nonfunctional SHALL specification with identifiers and acceptance criteria.

**Original control coverage:** C011-C013

#### Engineering implementation checklist

- [ ] **MC-05.T01** — Create a normative SCH-01 requirements specification using stable SHALL/SHALL NOT IDs separate from the generic audit controls.
- [ ] **MC-05.T02** — Define classification, candidate eligibility, scoring, deterministic tie-breaking, runtime selection, isolation tier, accelerator selection, data path, and placement-output requirements.
- [ ] **MC-05.T03** — Define workload input invariants for identity, tenant, provenance, capabilities, latency class, site affinity, trust class, and resources.
- [ ] **MC-05.T04** — Define node-report invariants for identity, site, tiers, capabilities, occupancy, freshness, attestation, topology, accelerators, thermal state, and health.
- [ ] **MC-05.T05** — Specify precedence for security, residency, topology, SLO/latency, fairness, thermal, cost, and optional optimization conflicts.
- [ ] **MC-05.T06** — Define deterministic behavior for equivalent candidates and ordering across supported platforms.
- [ ] **MC-05.T07** — Specify failure semantics for no candidate, stale telemetry, invalid policy, unavailable trust services, duplicates, and state conflicts.
- [ ] **MC-05.T08** — Define NFRs for latency, throughput, availability, recovery, consistency, resource bounds, and telemetry overhead.
- [ ] **MC-05.T09** — Define cloud/datacenter/near-edge/far-edge/disconnected requirements.
- [ ] **MC-05.T10** — Define tenant isolation, diagnostic redaction, authorization, auditability, and residency requirements.
- [ ] **MC-05.T11** — Define compatibility/version-negotiation requirements for every public/adjacent contract.
- [ ] **MC-05.T12** — Give every requirement acceptance criteria, test method, evidence type, and owner.
- [ ] **MC-05.T13** — Classify requirements as mandatory, optional optimization, conditional, or unsupported and remove ambiguous normative language.
- [ ] **MC-05.T14** — Review/baseline the requirements against the accepted ADR and source function.

#### Component-specific acceptance gates

- [ ] **MC-05.V01** — Every production behavior has a stable normative requirement and measurable acceptance criterion.
- [ ] **MC-05.V02** — No implementation behavior is orphaned from requirements and no mandatory requirement is untestable.
- [ ] **MC-05.V03** — Architecture, security, test, and operations roles approve the baseline.

#### Required deliverables / evidence

- [ ] **MC-05.E01** — Produce, version, and reference in release evidence: `REQUIREMENTS.md or requirements.yaml`.
- [ ] **MC-05.E02** — Produce, version, and reference in release evidence: `requirement ID registry`.
- [ ] **MC-05.E03** — Produce, version, and reference in release evidence: `approved baseline`.
- [ ] **MC-05.E04** — Produce, version, and reference in release evidence: `generated reference docs`.

#### Definition of done

- [ ] **MC-05.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-05.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-05.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-05.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-05.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-05.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-05.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-06 — Requirements-to-evidence traceability matrix

**Audit finding:** There is no generated matrix mapping each of the 100 checks to concrete code, test, runtime evidence, owner, and release gate result.

**Original control coverage:** C020, C090, C100

#### Engineering implementation checklist

- [ ] **MC-06.T01** — Create a machine-readable RTM mapping SCH-01-C001..C100 and all SCH-01 SHALL requirements to code, tests, evidence, owners, and gate status.
- [ ] **MC-06.T02** — Represent one-to-many and many-to-many relationships explicitly.
- [ ] **MC-06.T03** — Record evidence type, artifact digest/version, run ID, environment, timestamp, and pass/fail/waived status.
- [ ] **MC-06.T04** — Reference local implementation at file/symbol level where appropriate.
- [ ] **MC-06.T05** — Reference adjacent-plane integration evidence rather than falsely claiming external controls are local.
- [ ] **MC-06.T06** — Link waivers with owner, rationale, compensating controls, approval, and expiry.
- [ ] **MC-06.T07** — Generate human-readable trace tables from the machine-readable source.
- [ ] **MC-06.T08** — Validate orphan requirements/tests, duplicate IDs, missing owners, stale evidence, expired waivers, and broken references.
- [ ] **MC-06.T09** — Use immutable commit/digest evidence references rather than mutable branch URLs.
- [ ] **MC-06.T10** — Run RTM validation in CI and production exit gate.
- [ ] **MC-06.T11** — Generate coverage summaries by architecture, interfaces, security, resilience, performance, observability, testing, and operations.
- [ ] **MC-06.T12** — Snapshot the RTM per release for reproducibility.

#### Component-specific acceptance gates

- [ ] **MC-06.V01** — Every C001-C100 control and every SHALL requirement resolves to current evidence or approved unexpired waiver.
- [ ] **MC-06.V02** — CI fails on broken/orphaned/stale traceability.
- [ ] **MC-06.V03** — The release bundle contains the exact RTM used for the decision.

#### Required deliverables / evidence

- [ ] **MC-06.E01** — Produce, version, and reference in release evidence: `traceability/rtm.yaml`.
- [ ] **MC-06.E02** — Produce, version, and reference in release evidence: `generated RTM report`.
- [ ] **MC-06.E03** — Produce, version, and reference in release evidence: `RTM validator`.
- [ ] **MC-06.E04** — Produce, version, and reference in release evidence: `release RTM snapshot`.

#### Definition of done

- [ ] **MC-06.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-06.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-06.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-06.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-06.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-06.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-06.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 1 — Deployment semantics and placement capabilities

### MC-07 — Deployment-context semantics

**Audit finding:** Cloud, datacenter, near-edge, far-edge, disconnected-site, and site-boundary behavior are not fully specified.

**Original control coverage:** C012, C018

#### Engineering implementation checklist

- [ ] **MC-07.T01** — Define a canonical deployment-context model for cloud, datacenter, near-edge, far-edge, disconnected site, multi-site, and single-site operation.
- [ ] **MC-07.T02** — Model site/region/jurisdiction, connectivity class, latency/bandwidth envelope, clock quality, central control reachability, and local authority.
- [ ] **MC-07.T03** — Define which inputs remain authoritative when disconnected and which become unavailable, stale, cached, or locally overridden.
- [ ] **MC-07.T04** — Define node-report freshness bounds by deployment context where needed.
- [ ] **MC-07.T05** — Specify fail-open/fail-closed behavior during policy/topology/identity/control-plane outages.
- [ ] **MC-07.T06** — Define reconnect synchronization and conflict resolution for leases, quotas, policy revisions, and audit events.
- [ ] **MC-07.T07** — Define residency/egress restrictions for disconnected or jurisdiction-bound sites.
- [ ] **MC-07.T08** — Define expected runtime/accelerator availability and resource ceilings for constrained edge deployments.
- [ ] **MC-07.T09** — Define context-specific SLOs and degraded modes.
- [ ] **MC-07.T10** — Encode deployment context in typed schemas and decision/explain metadata.
- [ ] **MC-07.T11** — Add positive fixtures for supported contexts and negative fixtures for unsupported combinations.
- [ ] **MC-07.T12** — Document unsupported deployment patterns and operator action.

#### Component-specific acceptance gates

- [ ] **MC-07.V01** — The same request has documented deterministic behavior in every supported deployment context.
- [ ] **MC-07.V02** — Disconnect/reconnect tests prove no duplicate execution, isolation breach, stale-policy acceptance beyond bounds, or residency violation.
- [ ] **MC-07.V03** — Unsupported contexts fail with stable machine-readable errors.

#### Required deliverables / evidence

- [ ] **MC-07.E01** — Produce, version, and reference in release evidence: `deployment-context schema`.
- [ ] **MC-07.E02** — Produce, version, and reference in release evidence: `DEPLOYMENT_CONTEXTS.md`.
- [ ] **MC-07.E03** — Produce, version, and reference in release evidence: `context fixtures`.
- [ ] **MC-07.E04** — Produce, version, and reference in release evidence: `offline/reconnect tests`.

#### Definition of done

- [ ] **MC-07.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-07.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-07.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-07.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-07.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-07.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-07.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-08 — Complete result/failure/lifecycle state machine

**Audit finding:** Success, partial success, degraded operation, retryable failure, terminal failure, lifecycle states, and legal transitions are not formally modeled.

**Original control coverage:** C014, C015

#### Engineering implementation checklist

- [ ] **MC-08.T01** — Model request/decision/lease lifecycle as a finite state machine with stable state IDs.
- [ ] **MC-08.T02** — Represent received, validated, classified, candidate-evaluated, selected, lease-pending, placed, degraded, retry-wait, refused, cancelled, expired, terminal-failed, and released states where applicable.
- [ ] **MC-08.T03** — Define legal transitions, preconditions, authoritative actor, side effects, and idempotency for each transition.
- [ ] **MC-08.T04** — Define success, partial success, degraded success, retryable failure, and terminal failure as machine-readable outcomes.
- [ ] **MC-08.T05** — Specify cancellation before/after external side effects.
- [ ] **MC-08.T06** — Specify timeout/expiry and late acknowledgement behavior.
- [ ] **MC-08.T07** — Prevent impossible combinations such as terminal+retryable or placed-without-valid-lease.
- [ ] **MC-08.T08** — Define restart/replay reconstruction rules.
- [ ] **MC-08.T09** — Emit transition events with request/lease IDs and reason codes.
- [ ] **MC-08.T10** — Generate lifecycle diagrams from the machine-readable state model.
- [ ] **MC-08.T11** — Add property/model tests enumerating transitions and rejecting illegal paths.
- [ ] **MC-08.T12** — Define state-model migration rules across versions.

#### Component-specific acceptance gates

- [ ] **MC-08.V01** — Every external outcome maps to exactly one defined state/transition path.
- [ ] **MC-08.V02** — Illegal transitions are rejected before mutable/external side effects.
- [ ] **MC-08.V03** — Property tests cover all transitions and restart/replay preserves valid state.

#### Required deliverables / evidence

- [ ] **MC-08.E01** — Produce, version, and reference in release evidence: `state-machine model/schema`.
- [ ] **MC-08.E02** — Produce, version, and reference in release evidence: `generated lifecycle diagram`.
- [ ] **MC-08.E03** — Produce, version, and reference in release evidence: `transition implementation`.
- [ ] **MC-08.E04** — Produce, version, and reference in release evidence: `state/property tests`.

#### Definition of done

- [ ] **MC-08.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-08.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-08.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-08.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-08.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-08.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-08.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-09 — Versioning/backward-compatibility policy

**Audit finding:** A version exists, but there is no supported-version policy, deprecation window, schema compatibility rule, or migration contract.

**Original control coverage:** C016, C027, C093

#### Engineering implementation checklist

- [ ] **MC-09.T01** — Document component versioning and how code, schema, API, policy, evidence, and state versions relate.
- [ ] **MC-09.T02** — Define supported compatibility window for clients, adjacent planes, schemas, and stored state.
- [ ] **MC-09.T03** — Define backward-compatible vs breaking changes for payloads, error codes, policies, reports, state, metrics, and audit events.
- [ ] **MC-09.T04** — Define deprecation period, removal criteria, and migration guidance.
- [ ] **MC-09.T05** — Add explicit version fields to external contracts and deterministic negotiation/rejection.
- [ ] **MC-09.T06** — Define unknown-field and unknown-enum behavior.
- [ ] **MC-09.T07** — Define upgrade/downgrade rules for durable state, occupancy, policy, and evidence formats.
- [ ] **MC-09.T08** — Maintain fixtures for every supported historical version.
- [ ] **MC-09.T09** — Add bidirectional compatibility tests and negative tests beyond the support window.
- [ ] **MC-09.T10** — Define rolling-upgrade behavior with mixed scheduler/execution versions.
- [ ] **MC-09.T11** — Document rollback constraints for non-backward-readable state changes.
- [ ] **MC-09.T12** — Publish a machine-readable supported-version matrix updated by release automation.

#### Component-specific acceptance gates

- [ ] **MC-09.V01** — Supported mixed-version combinations pass automated compatibility tests and unsupported versions fail explicitly.
- [ ] **MC-09.V02** — Breaking changes cannot merge without version-policy enforcement and migration evidence.
- [ ] **MC-09.V03** — Rolling upgrade and rollback paths are tested.

#### Required deliverables / evidence

- [ ] **MC-09.E01** — Produce, version, and reference in release evidence: `VERSIONING.md`.
- [ ] **MC-09.E02** — Produce, version, and reference in release evidence: `compatibility matrix`.
- [ ] **MC-09.E03** — Produce, version, and reference in release evidence: `historical fixtures`.
- [ ] **MC-09.E04** — Produce, version, and reference in release evidence: `migration/rolling-upgrade tests`.

#### Definition of done

- [ ] **MC-09.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-09.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-09.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-09.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-09.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-09.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-09.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-10 — Quota/fair-share accounting

**Audit finding:** The engine has slot capacity and local tenant isolation, but no persistent quota ledger, reservation model, starvation guard, or fair-share policy.

**Original control coverage:** C017, C058

#### Engineering implementation checklist

- [ ] **MC-10.T01** — Define tenant/project quota dimensions for workloads, slots, CPU, memory, accelerator units, sites/runtimes, and reserved capacity.
- [ ] **MC-10.T02** — Define hard/soft quota, burst allowance, reservation, borrowing, and overcommit semantics.
- [ ] **MC-10.T03** — Select/document a fair-share algorithm and invariants suitable to the resource model.
- [ ] **MC-10.T04** — Define starvation prevention, aging, priority inversion handling, and maximum wait objectives.
- [ ] **MC-10.T05** — Model per-tenant weights and administrative priority without tenant self-escalation.
- [ ] **MC-10.T06** — Persist quota usage/reservations in authoritative transactional state.
- [ ] **MC-10.T07** — Make placement and quota reservation atomic/fenced across concurrent schedulers.
- [ ] **MC-10.T08** — Define release/reclamation for cancel, failure, expiry, and orphan cases.
- [ ] **MC-10.T09** — Make reservations idempotent by stable request/workload identity.
- [ ] **MC-10.T10** — Expose safe quota decision metadata without leaking another tenant's allocation.
- [ ] **MC-10.T11** — Emit quota/fairness metrics including utilization, denial, wait, starvation, borrowing, and reconciliation.
- [ ] **MC-10.T12** — Simulate many tenants with skewed demand, bursts, reservations, and long-running jobs.
- [ ] **MC-10.T13** — Run distributed race tests for final quota unit/capacity slot.
- [ ] **MC-10.T14** — Provide authorized, audited, expiring operator quota overrides.

#### Component-specific acceptance gates

- [ ] **MC-10.V01** — Concurrent/distributed tests never exceed hard quota/capacity or double-reserve resources.
- [ ] **MC-10.V02** — Fair-share simulations meet documented fairness/starvation bounds.
- [ ] **MC-10.V03** — Quota overrides are authenticated, authorized, audited, time-bounded, and reversible.

#### Required deliverables / evidence

- [ ] **MC-10.E01** — Produce, version, and reference in release evidence: `quota/fair-share policy`.
- [ ] **MC-10.E02** — Produce, version, and reference in release evidence: `transactional quota ledger`.
- [ ] **MC-10.E03** — Produce, version, and reference in release evidence: `fair-share implementation`.
- [ ] **MC-10.E04** — Produce, version, and reference in release evidence: `fairness/race tests`.
- [ ] **MC-10.E05** — Produce, version, and reference in release evidence: `quota telemetry`.

#### Definition of done

- [ ] **MC-10.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-10.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-10.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-10.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-10.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-10.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-10.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-11 — Runtime/execution-target selector

**Audit finding:** Placement selects a node and tier, but does not select a concrete runtime implementation/execution target beyond the tier label.

**Original control coverage:** C010, C011, C031

#### Engineering implementation checklist

- [ ] **MC-11.T01** — Define a runtime registry schema with runtime ID, implementation, version, execution tier, workload formats, CPU architectures, isolation properties, capabilities, site/provider availability, and lifecycle status.
- [ ] **MC-11.T02** — Require immutable runtime artifact digests plus provenance/attestation metadata.
- [ ] **MC-11.T03** — Map classified workload requirements to explicit runtime requirements rather than using only a tier label.
- [ ] **MC-11.T04** — Filter runtime eligibility deterministically on compatibility, policy, version, health, architecture, and isolation.
- [ ] **MC-11.T05** — Define deterministic runtime scoring/tie-breaking and explanation.
- [ ] **MC-11.T06** — Return runtime ID/version/digest and execution parameters in placement results.
- [ ] **MC-11.T07** — Verify the selected node can host the runtime and PLN-04 can enforce it.
- [ ] **MC-11.T08** — Define fallback when the preferred runtime is unavailable without silent security/isolation downgrade.
- [ ] **MC-11.T09** — Define runtime health, drain, disable, and retirement semantics.
- [ ] **MC-11.T10** — Version the registry and include its revision in decision/audit metadata.
- [ ] **MC-11.T11** — Add conformance fixtures for every supported runtime/tier.
- [ ] **MC-11.T12** — Test unsupported architecture/version, unhealthy/revoked runtime, missing capability, and fallback conflicts.
- [ ] **MC-11.T13** — Integrate runtime selection with compatibility/canary release controls.

#### Component-specific acceptance gates

- [ ] **MC-11.V01** — Every successful placement names a concrete approved runtime implementation/version/digest.
- [ ] **MC-11.V02** — Selection is deterministic and cannot silently choose a weaker runtime.
- [ ] **MC-11.V03** — End-to-end tests prove the execution plane launches exactly the selected runtime.

#### Required deliverables / evidence

- [ ] **MC-11.E01** — Produce, version, and reference in release evidence: `runtime registry schema/data`.
- [ ] **MC-11.E02** — Produce, version, and reference in release evidence: `runtime selector`.
- [ ] **MC-11.E03** — Produce, version, and reference in release evidence: `runtime compatibility fixtures`.
- [ ] **MC-11.E04** — Produce, version, and reference in release evidence: `end-to-end enforcement tests`.

#### Definition of done

- [ ] **MC-11.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-11.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-11.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-11.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-11.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-11.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-11.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-12 — Latency-aware placement policy

**Audit finding:** `latency_class` is classified but is not consumed by candidate filtering or scoring, so interactive and batch workloads currently place identically given the same other inputs.

**Original control coverage:** C011, C013, C061-C063

#### Engineering implementation checklist

- [ ] **MC-12.T01** — Define latency-class semantics as measurable scheduler/end-to-end objectives.
- [ ] **MC-12.T02** — Define authoritative measurements such as RTT, queue delay, startup, data-path latency, topology cost, or composite score.
- [ ] **MC-12.T03** — Add typed latency inputs with source, timestamp, quality/confidence, and freshness bounds.
- [ ] **MC-12.T04** — Treat hard latency ceilings as candidate constraints and softer targets as scoring terms.
- [ ] **MC-12.T05** — Normalize units and reject negative, NaN, infinite, or otherwise invalid values.
- [ ] **MC-12.T06** — Add smoothing/hysteresis for volatile telemetry where needed.
- [ ] **MC-12.T07** — Define behavior for missing, stale, contradictory, or partial latency data.
- [ ] **MC-12.T08** — Move weights/thresholds into versioned governed policy.
- [ ] **MC-12.T09** — Include latency factors and policy revision in safe decision explanations.
- [ ] **MC-12.T10** — Add deterministic fixtures where interactive and batch workloads produce different placement when conditions justify it.
- [ ] **MC-12.T11** — Test every threshold/freshness boundary.
- [ ] **MC-12.T12** — Benchmark latency-aware scoring overhead.
- [ ] **MC-12.T13** — Correlate decisions with observed post-placement latency for tuning and regression analysis.

#### Component-specific acceptance gates

- [ ] **MC-12.V01** — Latency class materially affects placement under controlled fixtures when expected.
- [ ] **MC-12.V02** — Stale/malformed latency data cannot influence placement.
- [ ] **MC-12.V03** — Latency-aware scoring is deterministic for a fixed snapshot and stays within performance budget.

#### Required deliverables / evidence

- [ ] **MC-12.E01** — Produce, version, and reference in release evidence: `latency policy/schema`.
- [ ] **MC-12.E02** — Produce, version, and reference in release evidence: `latency-aware scoring/filtering`.
- [ ] **MC-12.E03** — Produce, version, and reference in release evidence: `latency fixtures/tests`.
- [ ] **MC-12.E04** — Produce, version, and reference in release evidence: `latency decision telemetry`.

#### Definition of done

- [ ] **MC-12.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-12.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-12.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-12.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-12.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-12.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-12.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-13 — Topology-aware placement

**Audit finding:** No topology graph, hop/zone/NUMA locality input, cost function, or topology constraint is implemented in the local engine.

**Original control coverage:** C010, C019, C031, C066, C078

#### Engineering implementation checklist

- [ ] **MC-13.T01** — Define a versioned topology graph covering provider, region, site, zone, failure domain/rack, host, NUMA, and relevant network hierarchy.
- [ ] **MC-13.T02** — Assign stable IDs and distinguish physical, network, administrative, and failure-domain locality.
- [ ] **MC-13.T03** — Define topology source authority, revision, update mechanism, timestamp, and freshness.
- [ ] **MC-13.T04** — Represent required/forbidden site/zone, affinity, anti-affinity, spread, hop, and NUMA/device constraints.
- [ ] **MC-13.T05** — Apply mandatory topology constraints before optimization scoring.
- [ ] **MC-13.T06** — Define deterministic topology cost for soft locality.
- [ ] **MC-13.T07** — Prevent stale topology from overriding security/residency constraints.
- [ ] **MC-13.T08** — Handle node/site deletion, duplicate IDs, dangling edges, cycles/invalid hierarchy, and graph partition.
- [ ] **MC-13.T09** — Include topology revision and relevant cost/reason data in decision metadata.
- [ ] **MC-13.T10** — Apply graph updates atomically so decisions never see partial revisions.
- [ ] **MC-13.T11** — Add graph/property tests for integrity, tie-breaking, and conflict cases.
- [ ] **MC-13.T12** — Integrate with GAP-03 using multi-zone/multi-site fixtures.
- [ ] **MC-13.T13** — Benchmark graph evaluation and memory at fleet scale.

#### Component-specific acceptance gates

- [ ] **MC-13.V01** — Mandatory topology constraints are never violated during normal operation, update, or partition.
- [ ] **MC-13.V02** — Soft locality scoring is deterministic for an immutable graph revision.
- [ ] **MC-13.V03** — Fleet-scale topology evaluation stays within approved latency/memory limits.

#### Required deliverables / evidence

- [ ] **MC-13.E01** — Produce, version, and reference in release evidence: `topology schema/graph model`.
- [ ] **MC-13.E02** — Produce, version, and reference in release evidence: `topology provider adapter`.
- [ ] **MC-13.E03** — Produce, version, and reference in release evidence: `topology-aware placement`.
- [ ] **MC-13.E04** — Produce, version, and reference in release evidence: `GAP-03 integration tests`.

#### Definition of done

- [ ] **MC-13.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-13.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-13.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-13.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-13.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-13.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-13.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-14 — Data-path/residency selector

**Audit finding:** No data locality, residency jurisdiction, storage path, data-plane affinity, or data-path binding is represented.

**Original control coverage:** C010, C019, C031, C078

#### Engineering implementation checklist

- [ ] **MC-14.T01** — Define workload/data-set metadata for data identity, jurisdiction, sensitivity, authoritative storage location, replication state, and permitted egress.
- [ ] **MC-14.T02** — Define typed data-path representation for storage endpoint, network path, cache/replica, encryption boundary, and site/provider ownership.
- [ ] **MC-14.T03** — Enforce residency/sovereignty and forbidden egress as hard candidate constraints.
- [ ] **MC-14.T04** — Define compute-near-data scoring and precedence with latency, cost, topology, and fairness.
- [ ] **MC-14.T05** — Validate data-location claims against authoritative metadata rather than arbitrary caller strings.
- [ ] **MC-14.T06** — Track data-path revision/freshness and reject stale location metadata beyond policy bounds.
- [ ] **MC-14.T07** — Define behavior for missing replicas, degraded storage, unavailable paths, and conflicting residency rules.
- [ ] **MC-14.T08** — Require transport/storage encryption properties for sensitive data and propagate key/identity prerequisites.
- [ ] **MC-14.T09** — Redact sensitive data-set/location details from ordinary diagnostics.
- [ ] **MC-14.T10** — Return selected data-path reference and governing residency rule in explain metadata.
- [ ] **MC-14.T11** — Test multi-region/multi-jurisdiction prohibited egress.
- [ ] **MC-14.T12** — Test stale metadata, replica loss, link failure, and storage failover.
- [ ] **MC-14.T13** — Correlate data-path choice to infrastructure graph and application lineage.

#### Component-specific acceptance gates

- [ ] **MC-14.V01** — No placement crosses a declared residency/egress boundary under normal, failover, or reconnect scenarios.
- [ ] **MC-14.V02** — Data locality optimization runs only after hard security/residency constraints.
- [ ] **MC-14.V03** — Operators can identify the exact data-path revision/rule used for a decision.

#### Required deliverables / evidence

- [ ] **MC-14.E01** — Produce, version, and reference in release evidence: `data residency/path schemas`.
- [ ] **MC-14.E02** — Produce, version, and reference in release evidence: `data metadata provider adapter`.
- [ ] **MC-14.E03** — Produce, version, and reference in release evidence: `data-aware placement policy`.
- [ ] **MC-14.E04** — Produce, version, and reference in release evidence: `residency conformance tests`.

#### Definition of done

- [ ] **MC-14.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-14.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-14.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-14.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-14.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-14.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-14.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-15 — Accelerator allocator

**Audit finding:** Generic hardware capabilities are checked, but there is no accelerator identity, quantity, partition, exclusivity, locality, health, or lease allocation.

**Original control coverage:** C010, C011, C031, C064, C069

#### Engineering implementation checklist

- [ ] **MC-15.T01** — Define accelerator inventory fields: stable device ID, type/vendor/model, architecture, capacity/memory, partition profile, NUMA locality, health, firmware/driver/runtime compatibility, and isolation capabilities.
- [ ] **MC-15.T02** — Extend workload requirements with accelerator count, memory/capability minima, exclusivity/shareability, partition type, and affinity.
- [ ] **MC-15.T03** — Validate accelerator reports from authoritative discovery/attestation.
- [ ] **MC-15.T04** — Filter candidates on device type/count/capability/health/compatibility.
- [ ] **MC-15.T05** — Implement transactional allocation for exclusive/shared/partitioned devices.
- [ ] **MC-15.T06** — Represent partition identities generically enough for technologies such as MIG/SR-IOV without vendor-locking the core contract.
- [ ] **MC-15.T07** — Bind device lease to workload, tenant, node, runtime, fencing epoch/token, and expiry.
- [ ] **MC-15.T08** — Use NUMA/topology/data locality in accelerator scoring.
- [ ] **MC-15.T09** — Define leased-device health degradation response.
- [ ] **MC-15.T10** — Reclaim device capacity on completion, cancel, timeout, crash, orphan, and restart.
- [ ] **MC-15.T11** — Emit utilization/fragmentation and allocation-reason telemetry.
- [ ] **MC-15.T12** — Race simultaneous claims for the last device/partition.
- [ ] **MC-15.T13** — Test missing driver/runtime, insufficient memory, unhealthy/stale/revoked device reports.

#### Component-specific acceptance gates

- [ ] **MC-15.V01** — No physical/logical accelerator is double-leased under concurrency, restart, or distributed failover.
- [ ] **MC-15.V02** — Successful placements satisfy device quantity/capability/isolation/runtime compatibility.
- [ ] **MC-15.V03** — Device-loss/reclamation tests restore safe capacity without orphan/cross-tenant assignment.

#### Required deliverables / evidence

- [ ] **MC-15.E01** — Produce, version, and reference in release evidence: `accelerator schemas`.
- [ ] **MC-15.E02** — Produce, version, and reference in release evidence: `device allocator/lease logic`.
- [ ] **MC-15.E03** — Produce, version, and reference in release evidence: `accelerator compatibility matrix`.
- [ ] **MC-15.E04** — Produce, version, and reference in release evidence: `race/recovery tests`.

#### Definition of done

- [ ] **MC-15.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-15.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-15.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-15.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-15.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-15.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-15.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-16 — Governed policy-input engine

**Audit finding:** Provenance, site affinity, thermal exclusion, tier and capabilities are hard-coded model fields; there is no signed/versioned policy bundle, precedence engine, policy revision, or policy provenance.

**Original control coverage:** C019, C031-C037, C045, C076-C078

#### Engineering implementation checklist

- [ ] **MC-16.T01** — Define a signed versioned policy-bundle format with ID, revision, issuer, activation time, compatibility range, digest, and signature.
- [ ] **MC-16.T02** — Move tunable placement rules from hidden constants into explicit policy while retaining non-negotiable safety invariants in code.
- [ ] **MC-16.T03** — Define policy namespaces for provenance/trust, tier, site, topology, latency, fairness, accelerator, residency, thermal/power, and cost.
- [ ] **MC-16.T04** — Define rule precedence; optimization policy must never downgrade security/residency/isolation.
- [ ] **MC-16.T05** — Use a deterministic policy evaluator/language and prohibit unsafe dynamic code execution.
- [ ] **MC-16.T06** — Validate schema, signature, issuer trust, semantic constraints, and supported policy version before activation.
- [ ] **MC-16.T07** — Support dry-run/shadow evaluation without affecting placement.
- [ ] **MC-16.T08** — Activate/rollback policy atomically with revision fencing.
- [ ] **MC-16.T09** — Include policy revision/digest and matched rule IDs in decision/audit metadata.
- [ ] **MC-16.T10** — Define fail-closed/degraded behavior for absent, expired, revoked, corrupt, or incompatible policy.
- [ ] **MC-16.T11** — Create golden policy fixtures for boundary/precedence cases.
- [ ] **MC-16.T12** — Run differential tests between old/new revisions before rollout.
- [ ] **MC-16.T13** — Authorize policy publication/activation separately from workload submission and audit all changes.

#### Component-specific acceptance gates

- [ ] **MC-16.V01** — Each policy-dependent decision identifies exactly one immutable policy revision and matched rules.
- [ ] **MC-16.V02** — Invalid/untrusted/incompatible policy cannot partially activate.
- [ ] **MC-16.V03** — Policy can be shadow-tested, atomically activated, audited, and rolled back without safety downgrade.

#### Required deliverables / evidence

- [ ] **MC-16.E01** — Produce, version, and reference in release evidence: `policy schema/bundle`.
- [ ] **MC-16.E02** — Produce, version, and reference in release evidence: `policy evaluator`.
- [ ] **MC-16.E03** — Produce, version, and reference in release evidence: `sign/verify/activate tooling`.
- [ ] **MC-16.E04** — Produce, version, and reference in release evidence: `policy golden tests`.
- [ ] **MC-16.E05** — Produce, version, and reference in release evidence: `policy audit records`.

#### Definition of done

- [ ] **MC-16.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-16.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-16.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-16.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-16.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-16.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-16.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 2 — Contracts, configuration, identity, and security

### MC-17 — Formal machine-readable schema artifacts

**Audit finding:** `SCHEMAS.md` documents fields, but no JSON Schema/Protobuf/WIT/IDL files, schema validators, compatibility fixtures, or generated bindings are present.

**Original control coverage:** C021, C022, C027, C029, C082

#### Engineering implementation checklist

- [ ] **MC-17.T01** — Select canonical machine-readable contract formats for each boundary, such as JSON Schema, Protobuf, WIT/IDL, or a documented combination.
- [ ] **MC-17.T02** — Create versioned schemas for workload request/classification, node report, topology input, policy reference, placement decision, refusal/error, occupancy/lease state, status, and audit events.
- [ ] **MC-17.T03** — Encode types, ranges, formats, required/optional fields, enums, uniqueness, cardinality, and cross-field constraints where possible.
- [ ] **MC-17.T04** — Standardize timestamps/timezones, durations, IDs, digests, sizes, counts, and resource units.
- [ ] **MC-17.T05** — Define unknown-field/unknown-enum behavior for compatibility.
- [ ] **MC-17.T06** — Validate all payloads at trust boundaries before scheduler logic.
- [ ] **MC-17.T07** — Generate bindings/validators where practical and pin generator versions.
- [ ] **MC-17.T08** — Create positive/negative conformance fixtures for every schema version.
- [ ] **MC-17.T09** — Automate compatibility classification for schema changes.
- [ ] **MC-17.T10** — Prevent generated binding drift in CI.
- [ ] **MC-17.T11** — Document semantic constraints not expressible in schema and test them separately.
- [ ] **MC-17.T12** — Publish schema digests/revisions in release evidence.

#### Component-specific acceptance gates

- [ ] **MC-17.V01** — Every externally visible payload is validated by a versioned machine-readable schema.
- [ ] **MC-17.V02** — Compatibility checks detect breaking changes before merge.
- [ ] **MC-17.V03** — Generated bindings/validators reproduce from pinned tools.

#### Required deliverables / evidence

- [ ] **MC-17.E01** — Produce, version, and reference in release evidence: `schemas/*`.
- [ ] **MC-17.E02** — Produce, version, and reference in release evidence: `generated validators/bindings`.
- [ ] **MC-17.E03** — Produce, version, and reference in release evidence: `schema conformance fixtures`.
- [ ] **MC-17.E04** — Produce, version, and reference in release evidence: `schema compatibility tooling`.

#### Definition of done

- [ ] **MC-17.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-17.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-17.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-17.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-17.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-17.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-17.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-18 — Unified public error contract

**Audit finding:** `Unplaceable` now has `PK_SCHEDULER_ERROR/1`, but `ValueError`/`TypeError` remain out-of-band and there is no governed full error-code catalog with retryability and caller action.

**Original control coverage:** C026

#### Engineering implementation checklist

- [ ] **MC-18.T01** — Define a stable error-code namespace covering validation, authentication, authorization, policy, capability, topology, data, quota, capacity, freshness, attestation, timeout, cancellation, conflict, dependency, internal, and version failures.
- [ ] **MC-18.T02** — Assign each code a stable symbolic value, retryability, severity, caller action, and safe operator detail.
- [ ] **MC-18.T03** — Unify public ValueError/TypeError/Unplaceable behavior behind a governed error envelope.
- [ ] **MC-18.T04** — Define typed nested error details and redaction rules.
- [ ] **MC-18.T05** — Distinguish invalid request, transient dependency failure, resource exhaustion, policy refusal, and internal defect.
- [ ] **MC-18.T06** — Define transport mappings without making transport status the only semantic code.
- [ ] **MC-18.T07** — Preserve internal causal chain while hiding secrets, paths, stack traces, other-tenant IDs, and sensitive policy internals.
- [ ] **MC-18.T08** — Define retry/idempotency semantics per error code.
- [ ] **MC-18.T09** — Include request/correlation IDs and links to operator diagnostics/audit.
- [ ] **MC-18.T10** — Add exhaustive negative-path contract tests for exact error codes/details.
- [ ] **MC-18.T11** — Prevent error-code semantic reuse through compatibility tests.
- [ ] **MC-18.T12** — Document deprecation/migration mappings for retired codes.

#### Component-specific acceptance gates

- [ ] **MC-18.V01** — Every public failure returns a schema-valid stable error code/details envelope.
- [ ] **MC-18.V02** — Callers can decide retry/fix/escalate without parsing prose.
- [ ] **MC-18.V03** — The published error catalog is covered by negative-path contract tests.

#### Required deliverables / evidence

- [ ] **MC-18.E01** — Produce, version, and reference in release evidence: `ERRORS.md + machine-readable catalog`.
- [ ] **MC-18.E02** — Produce, version, and reference in release evidence: `error schema/types`.
- [ ] **MC-18.E03** — Produce, version, and reference in release evidence: `exception mapping layer`.
- [ ] **MC-18.E04** — Produce, version, and reference in release evidence: `error contract tests`.

#### Definition of done

- [ ] **MC-18.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-18.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-18.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-18.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-18.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-18.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-18.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-19 — Boundary authentication

**Audit finding:** No caller, node, peer, provider, or control-plane authentication mechanism is implemented in this archive.

**Original control coverage:** C023, C044, C048

#### Engineering implementation checklist

- [ ] **MC-19.T01** — Enumerate authentication boundaries for workload submitter, operator/admin, node reporter, topology provider, policy publisher, runtime/provider, execution plane, and gate/evidence actors.
- [ ] **MC-19.T02** — Choose identity mechanisms appropriate to each boundary such as mTLS/service identity, signed tokens, or node/device certificates.
- [ ] **MC-19.T03** — Bind authenticated identity to tenant, service role, node ID, site, and issuer; never trust unauthenticated caller labels.
- [ ] **MC-19.T04** — Define issuance, rotation, expiration, revocation, key storage, and compromise response.
- [ ] **MC-19.T05** — Require mutual authentication where both control-plane parties must be trusted.
- [ ] **MC-19.T06** — Validate issuer, audience, expiry, not-before, signature algorithm, key ID, and replay protections for tokens.
- [ ] **MC-19.T07** — Define secure bootstrap identity for new node/site without permanent shared secrets.
- [ ] **MC-19.T08** — Prevent downgrade to unauthenticated legacy paths unless explicitly isolated/waived.
- [ ] **MC-19.T09** — Define clock-skew and trusted-time failure behavior.
- [ ] **MC-19.T10** — Emit safe auth failure metrics/audit events.
- [ ] **MC-19.T11** — Test forged issuer, expired/revoked credentials, wrong audience, node/tenant mismatch, and key rotation.
- [ ] **MC-19.T12** — Feed authenticated identity into authorization and attestation validation.

#### Component-specific acceptance gates

- [ ] **MC-19.V01** — No production control-plane boundary accepts unauthenticated identity claims.
- [ ] **MC-19.V02** — Identity binding prevents spoofed tenant/node/site labels from gaining trust.
- [ ] **MC-19.V03** — Rotation/revocation and identity-mismatch tests fail closed.

#### Required deliverables / evidence

- [ ] **MC-19.E01** — Produce, version, and reference in release evidence: `authentication architecture`.
- [ ] **MC-19.E02** — Produce, version, and reference in release evidence: `identity verifier adapters`.
- [ ] **MC-19.E03** — Produce, version, and reference in release evidence: `PKI/token configuration`.
- [ ] **MC-19.E04** — Produce, version, and reference in release evidence: `authentication conformance tests`.

#### Definition of done

- [ ] **MC-19.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-19.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-19.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-19.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-19.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-19.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-19.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-20 — Authorization/capability enforcement

**Audit finding:** No caller permissions, tenant authorization, capability tokens, least-privilege identity model, or administrative authorization layer is implemented.

**Original control coverage:** C024, C042, C043

#### Engineering implementation checklist

- [ ] **MC-20.T01** — Define authorization subjects, resources, and actions for placement, explain/read, policy/config management, node registration, quarantine, overrides, evidence, and emergency controls.
- [ ] **MC-20.T02** — Use deny-by-default authorization with explicit grants.
- [ ] **MC-20.T03** — Bind authorization to authenticated identity and authoritative tenant membership.
- [ ] **MC-20.T04** — Prevent callers from reading, modifying, cancelling, explaining, or inferring another tenant's workloads/quotas/topology-sensitive data.
- [ ] **MC-20.T05** — Separate administrative roles from workload identities and minimize standing privilege.
- [ ] **MC-20.T06** — Select/document RBAC, ABAC, capability-token, or hybrid model.
- [ ] **MC-20.T07** — Enforce authorization at every external entry point and sensitive internal capability boundary.
- [ ] **MC-20.T08** — Support scoped, expiring delegated automation credentials instead of broad long-lived privilege.
- [ ] **MC-20.T09** — Require stronger approval for high-impact policy, quarantine, or gate-override actions where governance requires it.
- [ ] **MC-20.T10** — Audit administrative allow/deny decisions with subject/action/resource/policy revision/reason.
- [ ] **MC-20.T11** — Build an authorization matrix test suite across tenant, role, site, and admin scenarios.
- [ ] **MC-20.T12** — Test confused-deputy paths so SCH-01 cannot exercise downstream capabilities the caller lacks.

#### Component-specific acceptance gates

- [ ] **MC-20.V01** — All privileged APIs are deny-by-default and covered by an authorization matrix.
- [ ] **MC-20.V02** — Cross-tenant read/write/explain/override attempts fail safely and are audited.
- [ ] **MC-20.V03** — Delegated privileges expire and never exceed their allowed scope.

#### Required deliverables / evidence

- [ ] **MC-20.E01** — Produce, version, and reference in release evidence: `authorization model/policy`.
- [ ] **MC-20.E02** — Produce, version, and reference in release evidence: `authz enforcement layer`.
- [ ] **MC-20.E03** — Produce, version, and reference in release evidence: `role/capability matrix`.
- [ ] **MC-20.E04** — Produce, version, and reference in release evidence: `authorization tests`.

#### Definition of done

- [ ] **MC-20.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-20.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-20.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-20.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-20.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-20.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-20.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-21 — Timeout/cancellation/retry/idempotency/backpressure contract

**Audit finding:** The in-process calls are synchronous and bounded only by local execution; external request semantics and overload contracts are unspecified.

**Original control coverage:** C025, C028, C053, C054

#### Engineering implementation checklist

- [ ] **MC-21.T01** — Define request-level deadlines/timeouts and maximum permitted values for every boundary.
- [ ] **MC-21.T02** — Propagate deadlines to policy, topology, identity, quota, state, and execution calls rather than resetting timeouts at each hop.
- [ ] **MC-21.T03** — Define cancellation semantics and safe cancellation points before/after external side effects.
- [ ] **MC-21.T04** — Use stable idempotency/request/workload keys and persist deduplication where side effects occur.
- [ ] **MC-21.T05** — Classify operations as safe-to-retry, conditionally retryable, or non-retryable and bind that to error codes.
- [ ] **MC-21.T06** — Use bounded exponential backoff with jitter and total retry budget for transient idempotent failures only.
- [ ] **MC-21.T07** — Define queue, concurrency, candidate-fanout, and connection/resource limits.
- [ ] **MC-21.T08** — Implement admission control/backpressure before resource exhaustion.
- [ ] **MC-21.T09** — Provide retry-after guidance where appropriate and avoid synchronized retry storms.
- [ ] **MC-21.T10** — Audit timeout/cancel outcomes and distinguish caller cancellation from dependency timeout.
- [ ] **MC-21.T11** — Test races among success/cancel, timeout/commit, duplicate retries, and late downstream responses.
- [ ] **MC-21.T12** — Emit metrics for deadlines, cancellations, retries, deduplication, queue depth, shedding, and retry exhaustion.

#### Component-specific acceptance gates

- [ ] **MC-21.V01** — Duplicate/retried requests cannot create duplicate leases or quota consumption.
- [ ] **MC-21.V02** — Deadline/cancel races leave authoritative state consistent even with late acknowledgements.
- [ ] **MC-21.V03** — Overload tests shed work predictably without unbounded queues/memory.

#### Required deliverables / evidence

- [ ] **MC-21.E01** — Produce, version, and reference in release evidence: `request semantics specification`.
- [ ] **MC-21.E02** — Produce, version, and reference in release evidence: `deadline/idempotency implementation`.
- [ ] **MC-21.E03** — Produce, version, and reference in release evidence: `backpressure/admission control`.
- [ ] **MC-21.E04** — Produce, version, and reference in release evidence: `timeout/retry/race tests`.

#### Definition of done

- [ ] **MC-21.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-21.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-21.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-21.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-21.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-21.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-21.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-22 — Declarative configuration subsystem

**Audit finding:** No separate config schema/store/loader exists for policy, freshness, scoring, environment, site, or feature flags.

**Original control coverage:** C032-C035

#### Engineering implementation checklist

- [ ] **MC-22.T01** — Create a typed declarative configuration schema separate from immutable package artifacts and mutable scheduler state.
- [ ] **MC-22.T02** — Classify settings by global/environment/site/provider/runtime/feature scope and by startup-only versus hot-reloadable behavior.
- [ ] **MC-22.T03** — Define deterministic precedence across safe defaults, base config, environment/site overlays, and authorized emergency overrides.
- [ ] **MC-22.T04** — Keep safety invariants non-configurable where weakening them would violate the trust model.
- [ ] **MC-22.T05** — Reject unknown keys and invalid values before use with machine-readable validation errors.
- [ ] **MC-22.T06** — Represent secrets only by opaque secret references, never raw credential values.
- [ ] **MC-22.T07** — Standardize units for durations, sizes, percentages, and thresholds.
- [ ] **MC-22.T08** — Support dry-run validation and redacted effective-config rendering.
- [ ] **MC-22.T09** — Bind effective config to a revision/digest included in decision/status/log/evidence metadata.
- [ ] **MC-22.T10** — Ensure a single decision observes one immutable config snapshot.
- [ ] **MC-22.T11** — Create minimum, typical, boundary, deprecated, and invalid fixtures.
- [ ] **MC-22.T12** — Document safe defaults for freshness, limits, scoring, feature flags, telemetry, and dependency behavior.

#### Component-specific acceptance gates

- [ ] **MC-22.V01** — Invalid/unknown/security-weakening config cannot activate.
- [ ] **MC-22.V02** — Identical inputs produce identical effective configuration across supported environments.
- [ ] **MC-22.V03** — Every decision/status record identifies the exact effective config revision.

#### Required deliverables / evidence

- [ ] **MC-22.E01** — Produce, version, and reference in release evidence: `configuration schema/defaults`.
- [ ] **MC-22.E02** — Produce, version, and reference in release evidence: `config loader/validator`.
- [ ] **MC-22.E03** — Produce, version, and reference in release evidence: `effective-config renderer`.
- [ ] **MC-22.E04** — Produce, version, and reference in release evidence: `config fixtures/tests`.

#### Definition of done

- [ ] **MC-22.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-22.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-22.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-22.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-22.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-22.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-22.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-23 — Configuration provenance and transactional activation

**Audit finding:** No config author/version/activation timestamp, atomic apply, validation gate, or transactional rollback mechanism exists.

**Original control coverage:** C034, C036-C038

#### Engineering implementation checklist

- [ ] **MC-23.T01** — Assign immutable config revision IDs/digests and record author, source, approver, creation, validation, and activation timestamps.
- [ ] **MC-23.T02** — Integrity-protect or sign approved configuration revisions.
- [ ] **MC-23.T03** — Stage candidate config separately from active config and validate all dependencies before commit.
- [ ] **MC-23.T04** — Use compare-and-swap or transactional activation so workers never observe partial multi-file updates.
- [ ] **MC-23.T05** — Keep the previous known-good revision available and define rollback authorization.
- [ ] **MC-23.T06** — Fence concurrent activations and reject stale activation attempts.
- [ ] **MC-23.T07** — Emit tamper-evident audit events for stage, validate, approve, activate, reject, and rollback.
- [ ] **MC-23.T08** — Support shadow/canary validation for high-risk config changes.
- [ ] **MC-23.T09** — Persist enough activation history to reconstruct which config governed historical decisions.
- [ ] **MC-23.T10** — Expose staged/active revision safely in status.
- [ ] **MC-23.T11** — Fault-inject crashes during activation to prove atomicity/recovery.
- [ ] **MC-23.T12** — Require provenance/approval validation in release readiness.

#### Component-specific acceptance gates

- [ ] **MC-23.V01** — Crash/fault during activation never produces partial config.
- [ ] **MC-23.V02** — Historical decisions trace to immutable config revisions and activation records.
- [ ] **MC-23.V03** — Rollback restores a complete previous known-good revision deterministically.

#### Required deliverables / evidence

- [ ] **MC-23.E01** — Produce, version, and reference in release evidence: `config provenance schema`.
- [ ] **MC-23.E02** — Produce, version, and reference in release evidence: `transactional activation mechanism`.
- [ ] **MC-23.E03** — Produce, version, and reference in release evidence: `activation audit history`.
- [ ] **MC-23.E04** — Produce, version, and reference in release evidence: `rollback/fault tests`.

#### Definition of done

- [ ] **MC-23.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-23.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-23.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-23.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-23.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-23.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-23.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-24 — Secret/key management integration

**Audit finding:** No credential boundary, secret provider, key rotation policy, or safe unavailable-key behavior exists; no secrets are needed by the pure engine today, but production integrations would require this control.

**Original control coverage:** C039, C047, C048

#### Engineering implementation checklist

- [ ] **MC-24.T01** — Inventory current/future secrets and keys: identity credentials, signing roots, attestation roots, audit keys, state-store credentials, telemetry credentials, and encryption keys.
- [ ] **MC-24.T02** — Define a secret-provider abstraction backed by approved KMS/HSM/Vault/OS-protected stores rather than plaintext files.
- [ ] **MC-24.T03** — Use opaque secret references in configuration and prohibit secret values in effective-config output.
- [ ] **MC-24.T04** — Grant only the minimum key operation/secret scope needed by SCH-01.
- [ ] **MC-24.T05** — Define key generation/import, rotation, overlap, revocation, destruction, and emergency compromise handling.
- [ ] **MC-24.T06** — Cache secrets only when necessary with bounded TTL and rotation awareness.
- [ ] **MC-24.T07** — Prohibit secrets/tokens/private keys/decrypted material in logs, exceptions, fixtures, or release evidence.
- [ ] **MC-24.T08** — Define startup/steady-state/active-lease behavior when secret/KMS services are unavailable.
- [ ] **MC-24.T09** — Encrypt sensitive data in transit and at rest using approved managed keys.
- [ ] **MC-24.T10** — Audit secret/key access without recording material.
- [ ] **MC-24.T11** — Scan source/logs/artifacts for accidental secrets.
- [ ] **MC-24.T12** — Test rotation, overlap, revoked-key, and unavailable-key scenarios.

#### Component-specific acceptance gates

- [ ] **MC-24.V01** — No production secret appears in source, ordinary config, logs, or release evidence.
- [ ] **MC-24.V02** — Rotation/revocation tests preserve authorized service while rejecting revoked credentials.
- [ ] **MC-24.V03** — Unavailable-key behavior matches documented fail-closed/degraded semantics.

#### Required deliverables / evidence

- [ ] **MC-24.E01** — Produce, version, and reference in release evidence: `secret/key inventory`.
- [ ] **MC-24.E02** — Produce, version, and reference in release evidence: `secret-provider/KMS adapter`.
- [ ] **MC-24.E03** — Produce, version, and reference in release evidence: `rotation/compromise runbook`.
- [ ] **MC-24.E04** — Produce, version, and reference in release evidence: `secret scanning/rotation tests`.

#### Definition of done

- [ ] **MC-24.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-24.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-24.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-24.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-24.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-24.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-24.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-25 — Cryptographic node/workload/artifact attestation

**Audit finding:** `NodeReport` validation checks shape and clock sanity only. It does not authenticate the producer or verify signatures, digests, provenance attestations, approved versions, or anti-replay data.

**Original control coverage:** C041, C044, C045, C048

#### Engineering implementation checklist

- [ ] **MC-25.T01** — Define signed attestation envelopes for node reports, workload/artifact identity, runtime artifacts, policy bundles, and relevant provider assertions.
- [ ] **MC-25.T02** — Include issuer, subject, payload digest, issue/expiry time, nonce/counter, algorithm/key ID, and signature.
- [ ] **MC-25.T03** — Bind node attestation to node identity, site, hardware/firmware/runtime claims, and sequence.
- [ ] **MC-25.T04** — Validate issuer trust chain and reject unknown/revoked/expired issuers.
- [ ] **MC-25.T05** — Verify canonical serialization and signature before consuming attested fields.
- [ ] **MC-25.T06** — Implement anti-replay using nonce, monotonic sequence/counter, or bounded replay cache.
- [ ] **MC-25.T07** — Validate freshness independently from cryptographic validity.
- [ ] **MC-25.T08** — Define policy for TPM/TEE/secure-boot evidence where supported without vendor-coupling the core contract.
- [ ] **MC-25.T09** — Bind workload artifact digest/provenance to trust classification to prevent caller trust escalation.
- [ ] **MC-25.T10** — Include accepted attestation references/digests in decision/audit metadata rather than full evidence.
- [ ] **MC-25.T11** — Test tamper, signature substitution, wrong subject, replay, expiry, revocation, algorithm downgrade, and clock skew.
- [ ] **MC-25.T12** — Define fail-closed/degraded behavior when verification infrastructure is unavailable.

#### Component-specific acceptance gates

- [ ] **MC-25.V01** — Tampered, replayed, stale, revoked, or identity-mismatched evidence cannot influence placement.
- [ ] **MC-25.V02** — Every trust-sensitive decision references verified attestation evidence.
- [ ] **MC-25.V03** — Revocation takes effect within the documented bound.

#### Required deliverables / evidence

- [ ] **MC-25.E01** — Produce, version, and reference in release evidence: `attestation schema/envelope`.
- [ ] **MC-25.E02** — Produce, version, and reference in release evidence: `trust-store/verifier`.
- [ ] **MC-25.E03** — Produce, version, and reference in release evidence: `replay protection`.
- [ ] **MC-25.E04** — Produce, version, and reference in release evidence: `attestation negative/conformance tests`.

#### Definition of done

- [ ] **MC-25.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-25.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-25.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-25.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-25.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-25.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-25.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-26 — Rich occupancy/isolation metadata

**Audit finding:** Occupancy stores only workload->tenant. It lacks occupant trust class, tier instance, runtime identity, device assignment, namespace, and attestation needed to prove safe shared placement; 4.2.0 therefore fails cross-tenant placement closed.

**Original control coverage:** C046

#### Engineering implementation checklist

- [ ] **MC-26.T01** — Define occupancy/lease records with workload, tenant, trust class, isolation tier, runtime, node, sandbox/namespace identity, device assignments, data path, attestation reference, times, and fencing epoch/token.
- [ ] **MC-26.T02** — Distinguish desired, reserved, admitted, running, draining, and released states.
- [ ] **MC-26.T03** — Make occupancy authoritative in durable transactional state rather than a lossy workload-to-tenant map.
- [ ] **MC-26.T04** — Require execution acknowledgement to bind actual runtime/sandbox/device identity to the lease.
- [ ] **MC-26.T05** — Define co-location compatibility using both occupants' trust, tier, runtime, and device isolation properties.
- [ ] **MC-26.T06** — Permit cross-tenant sharing only when complete metadata and execution technology prove the boundary; otherwise fail closed.
- [ ] **MC-26.T07** — Prevent stale node occupancy reports from overriding the authoritative lease ledger.
- [ ] **MC-26.T08** — Reconcile scheduler ledger with execution/node observations.
- [ ] **MC-26.T09** — Redact cross-tenant occupant details from ordinary caller diagnostics.
- [ ] **MC-26.T10** — Version/migrate occupancy schema.
- [ ] **MC-26.T11** — Test mixed trust/tier/runtime/device, stale occupancy, orphan sandbox, and reconciliation conflict cases.
- [ ] **MC-26.T12** — Assert invariants such as no active lease without reservation and no incompatible duplicate device assignment.

#### Component-specific acceptance gates

- [ ] **MC-26.V01** — Cross-tenant sharing occurs only when complete metadata and enforceable compatibility rules prove safety.
- [ ] **MC-26.V02** — Authoritative occupancy survives restart and reconciles external observations.
- [ ] **MC-26.V03** — Property/invariant tests prevent orphan, duplicate, and contradictory lease/device state.

#### Required deliverables / evidence

- [ ] **MC-26.E01** — Produce, version, and reference in release evidence: `occupancy/lease schema`.
- [ ] **MC-26.E02** — Produce, version, and reference in release evidence: `durable occupancy store`.
- [ ] **MC-26.E03** — Produce, version, and reference in release evidence: `co-location compatibility policy`.
- [ ] **MC-26.E04** — Produce, version, and reference in release evidence: `reconciliation/invariant tests`.

#### Definition of done

- [ ] **MC-26.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-26.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-26.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-26.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-26.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-26.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-26.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-27 — Tamper-evident security audit ledger

**Audit finding:** No append-only/hash-chained signed audit stream is emitted for classification, refusal, placement, policy changes, or admin actions.

**Original control coverage:** C049, C073, C090

#### Engineering implementation checklist

- [ ] **MC-27.T01** — Define a versioned security audit event schema for classification, placement/refusal, authn/authz, policy/config changes, attestation, quarantine, overrides, gate actions, and evidence access.
- [ ] **MC-27.T02** — Include event ID, sequence, UTC time, actor, subject, tenant scope, operation, object refs, result, reason code, revisions, and correlation IDs.
- [ ] **MC-27.T03** — Use append-only integrity protection such as hash chaining, Merkle batching, signed checkpoints, WORM storage, or equivalent.
- [ ] **MC-27.T04** — Sign/checkpoint audit segments with managed rotating keys and publish verification metadata.
- [ ] **MC-27.T05** — Define ordering semantics within and across authority domains/sites.
- [ ] **MC-27.T06** — Minimize/redact secrets and sensitive tenant data while preserving forensic value.
- [ ] **MC-27.T07** — Define retention, access control, export, and secure deletion requirements.
- [ ] **MC-27.T08** — Make audit emission non-bypassable for privileged actions and define behavior when the sink is unavailable.
- [ ] **MC-27.T09** — Keep ordinary operational logs separate from the tamper-evident audit ledger.
- [ ] **MC-27.T10** — Provide an offline verifier for deletion/insertion/reorder/modification/signature/chain failures.
- [ ] **MC-27.T11** — Fault-test sink outage, disk full, crash between action/audit commit, and key rotation.
- [ ] **MC-27.T12** — Include ledger verification in release/incident evidence where relevant.

#### Component-specific acceptance gates

- [ ] **MC-27.V01** — Offline verification detects mutation/removal/reorder of committed audit events.
- [ ] **MC-27.V02** — Every defined security-sensitive action is auditable or fails according to policy.
- [ ] **MC-27.V03** — Audit access is authorized and sensitive cross-tenant content is minimized.

#### Required deliverables / evidence

- [ ] **MC-27.E01** — Produce, version, and reference in release evidence: `audit event schema`.
- [ ] **MC-27.E02** — Produce, version, and reference in release evidence: `tamper-evident ledger/store`.
- [ ] **MC-27.E03** — Produce, version, and reference in release evidence: `offline verifier`.
- [ ] **MC-27.E04** — Produce, version, and reference in release evidence: `retention/access policy`.
- [ ] **MC-27.E05** — Produce, version, and reference in release evidence: `audit fault tests`.

#### Definition of done

- [ ] **MC-27.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-27.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-27.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-27.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-27.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-27.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-27.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-28 — Adversarial security suite

**Audit finding:** No systematic tests for spoofing, replay, injection, malicious policy/artifact inputs, privilege escalation, escape, side channels, or resource exhaustion are present.

**Original control coverage:** C050, C085, C087

#### Engineering implementation checklist

- [ ] **MC-28.T01** — Derive a security test plan directly from the SCH-01 threat model and map each threat to automated tests.
- [ ] **MC-28.T02** — Test identity spoofing including tenant/node/site mismatch, forged issuer, and credential substitution.
- [ ] **MC-28.T03** — Test replay of node reports, workload submissions, policy/config activations, lease requests, and evidence/audit messages.
- [ ] **MC-28.T04** — Test injection/parser abuse across IDs, names, schemas, policy expressions, log fields, paths/URIs, and diagnostics.
- [ ] **MC-28.T05** — Test malicious policy/config bundles including pathological depth/count, conflicts, oversize input, invalid signatures, and algorithm downgrade.
- [ ] **MC-28.T06** — Test privilege escalation and confused-deputy paths across tenant/admin/policy/node/execution roles.
- [ ] **MC-28.T07** — Test resource exhaustion with huge candidate sets, capabilities, topologies, queue floods, retry storms, and slow dependencies.
- [ ] **MC-28.T08** — Test isolation/escape assumptions in integration with each real execution tier/device-sharing mode.
- [ ] **MC-28.T09** — Test explain/log/error surfaces for cross-tenant information leakage and side-channel inference.
- [ ] **MC-28.T10** — Fuzz untrusted parsers/state machines and preserve minimized failing corpus.
- [ ] **MC-28.T11** — Use sanitizers/instrumentation where native dependencies permit.
- [ ] **MC-28.T12** — Block release on unresolved high/critical findings absent approved waiver.

#### Component-specific acceptance gates

- [ ] **MC-28.V01** — Every threat-model entry has executable evidence or explicit non-applicability rationale.
- [ ] **MC-28.V02** — Spoof/replay/injection/privilege/resource-exhaustion scenarios fail safely and are auditable.
- [ ] **MC-28.V03** — Security regression suite runs automatically in CI/release certification.

#### Required deliverables / evidence

- [ ] **MC-28.E01** — Produce, version, and reference in release evidence: `security test plan/trace map`.
- [ ] **MC-28.E02** — Produce, version, and reference in release evidence: `adversarial test suite`.
- [ ] **MC-28.E03** — Produce, version, and reference in release evidence: `fuzz corpus`.
- [ ] **MC-28.E04** — Produce, version, and reference in release evidence: `security test report`.

#### Definition of done

- [ ] **MC-28.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-28.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-28.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-28.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-28.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-28.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-28.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 3 — Failure handling, durable state, and distributed safety

### MC-29 — Exhaustive failure model and health/stall thresholds

**Audit finding:** The contract lists four failure modes, but process/VM/node/site/network/provider/dependency/control-plane failure handling and health/stall thresholds are incomplete.

**Original control coverage:** C051, C052

#### Engineering implementation checklist

- [ ] **MC-29.T01** — Create a failure taxonomy for scheduler process, worker stall, state store, runtime/VM, node, accelerator, site, network, DNS, identity, policy, topology, telemetry, provider, execution plane, and control plane.
- [ ] **MC-29.T02** — For each failure define detector, threshold, impact radius, retryability, failover, degraded mode, and operator action.
- [ ] **MC-29.T03** — Define health, readiness, and liveness separately.
- [ ] **MC-29.T04** — Define stall thresholds for decision latency, state transactions, queue age, dependency latency, and reconciliation lag.
- [ ] **MC-29.T05** — Define clock-quality/skew failure handling for freshness and leases.
- [ ] **MC-29.T06** — Add hysteresis/debounce to avoid flapping and placement thrash.
- [ ] **MC-29.T07** — Model dependency states such as healthy, degraded, unavailable, recovering, and quarantined.
- [ ] **MC-29.T08** — Tie dependency/failure states to admission behavior so unsafe work is not accepted.
- [ ] **MC-29.T09** — Define recovery confirmation before resuming traffic.
- [ ] **MC-29.T10** — Expose failure/dependency state through status, metrics, logs, traces, and explainability.
- [ ] **MC-29.T11** — Create fault fixtures for every taxonomy category and expected error/state transitions.
- [ ] **MC-29.T12** — Align detection/remediation ownership with adjacent-plane boundaries.

#### Component-specific acceptance gates

- [ ] **MC-29.V01** — Every documented failure has deterministic detection and scheduler behavior.
- [ ] **MC-29.V02** — Stall/dependency tests enter degraded/unavailable states and recover within stated bounds.
- [ ] **MC-29.V03** — Safety-critical dependency failure never silently degrades into unsafe placement.

#### Required deliverables / evidence

- [ ] **MC-29.E01** — Produce, version, and reference in release evidence: `FAILURE_MODEL.md`.
- [ ] **MC-29.E02** — Produce, version, and reference in release evidence: `health/stall detection`.
- [ ] **MC-29.E03** — Produce, version, and reference in release evidence: `dependency state model`.
- [ ] **MC-29.E04** — Produce, version, and reference in release evidence: `failure fixtures/tests`.

#### Definition of done

- [ ] **MC-29.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-29.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-29.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-29.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-29.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-29.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-29.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-30 — Retry/load-shed/circuit-breaker/failover controls

**Audit finding:** There is no bounded retry policy, admission controller for scheduler request load, circuit breaker, failover algorithm, or formal degraded mode.

**Original control coverage:** C053-C056

#### Engineering implementation checklist

- [ ] **MC-30.T01** — Define retry budgets per dependency/operation and prohibit unbounded retries.
- [ ] **MC-30.T02** — Use bounded exponential backoff with jitter only for safe transient/idempotent operations.
- [ ] **MC-30.T03** — Implement admission control with bounded queues and per-tenant/global concurrency limits before expensive work.
- [ ] **MC-30.T04** — Define load-shedding priority so optional/low-value work is shed before safety-critical control traffic.
- [ ] **MC-30.T05** — Implement circuit breakers with explicit open/half-open/closed behavior and telemetry.
- [ ] **MC-30.T06** — Use bulkheads/separate pools where one slow dependency could exhaust scheduler capacity.
- [ ] **MC-30.T07** — Define failover targets and eligibility without violating isolation, residency, consistency, or compatibility.
- [ ] **MC-30.T08** — Define formal degraded modes and disabled capabilities for noncritical dependency loss.
- [ ] **MC-30.T09** — Prevent retry storms and provide caller backoff guidance.
- [ ] **MC-30.T10** — Make control values policy/configurable only within safe bounds and expose active values in status.
- [ ] **MC-30.T11** — Test dependency flapping, synchronized clients, cascading failure, partial site outage, and recovery.
- [ ] **MC-30.T12** — Alert on queue depth, shed rate, circuit-open duration, and retry exhaustion.

#### Component-specific acceptance gates

- [ ] **MC-30.V01** — Overload/dependency-failure tests stay within bounded CPU/memory/queue limits and do not create retry cascades.
- [ ] **MC-30.V02** — Failover/degraded modes preserve all hard constraints.
- [ ] **MC-30.V03** — Admission/circuit controls recover automatically with documented hysteresis.

#### Required deliverables / evidence

- [ ] **MC-30.E01** — Produce, version, and reference in release evidence: `resilience control policy`.
- [ ] **MC-30.E02** — Produce, version, and reference in release evidence: `admission/load-shed/circuit-breaker implementation`.
- [ ] **MC-30.E03** — Produce, version, and reference in release evidence: `degraded/failover modes`.
- [ ] **MC-30.E04** — Produce, version, and reference in release evidence: `cascade/overload tests`.

#### Definition of done

- [ ] **MC-30.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-30.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-30.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-30.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-30.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-30.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-30.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-31 — Durable scheduler state and restart/replay model

**Audit finding:** Placement mutates caller-owned in-memory `NodeReport` objects. There is no WAL/database, crash-consistent state, restart reconstruction, replay, or snapshot format.

**Original control coverage:** C057, C095

#### Engineering implementation checklist

- [ ] **MC-31.T01** — Define authoritative durable state for requests, classifications, reservations, leases, occupancy, quotas, revision references, and reconciliation checkpoints.
- [ ] **MC-31.T02** — Choose a transactional/replicated store meeting consistency, durability, conditional-update, and deployment-context requirements.
- [ ] **MC-31.T03** — Implement transactional/WAL semantics for reservation and external lease handoff.
- [ ] **MC-31.T04** — Use stable request/lease IDs and idempotent writes so replay cannot duplicate ownership.
- [ ] **MC-31.T05** — Define snapshots/checkpoints and log compaction with schema/version metadata.
- [ ] **MC-31.T06** — Define crash-consistency points and documented data-loss bounds.
- [ ] **MC-31.T07** — Implement restart recovery for in-flight work, uncertain leases, expiry, and reconciliation.
- [ ] **MC-31.T08** — Define deterministic side-effect-safe replay semantics.
- [ ] **MC-31.T09** — Encrypt sensitive state and apply least-privilege database credentials.
- [ ] **MC-31.T10** — Provide state-schema migration tooling and supported rollback strategy.
- [ ] **MC-31.T11** — Crash-inject at transaction boundaries and verify invariants after restart.
- [ ] **MC-31.T12** — Provide backup/restore hooks for MC-53.
- [ ] **MC-31.T13** — Expose state-store health, transaction latency, conflicts, recovery lag, and schema version.

#### Component-specific acceptance gates

- [ ] **MC-31.V01** — Forced crashes at every commit boundary recover without duplicate lease or hard-capacity corruption beyond documented RPO.
- [ ] **MC-31.V02** — Replay is idempotent and reconstructs the same authoritative state.
- [ ] **MC-31.V03** — Supported state-schema upgrades/rollbacks are automatically verified.

#### Required deliverables / evidence

- [ ] **MC-31.E01** — Produce, version, and reference in release evidence: `durable state schema/store adapter`.
- [ ] **MC-31.E02** — Produce, version, and reference in release evidence: `transaction/WAL model`.
- [ ] **MC-31.E03** — Produce, version, and reference in release evidence: `recovery/replay implementation`.
- [ ] **MC-31.E04** — Produce, version, and reference in release evidence: `crash-consistency tests`.

#### Definition of done

- [ ] **MC-31.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-31.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-31.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-31.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-31.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-31.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-31.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-32 — Distributed fencing/consensus

**Audit finding:** The new lock prevents in-process races only. Multiple scheduler processes can still race unless an external transactional owner/fencing mechanism exists.

**Original control coverage:** C058, C086

#### Engineering implementation checklist

- [ ] **MC-32.T01** — Choose/document distributed ownership model: elected single writer, consensus state machine, transactional fencing, or equivalent.
- [ ] **MC-32.T02** — Issue monotonically increasing lease epochs/fencing tokens for ownership grants.
- [ ] **MC-32.T03** — Require execution/resource owners to reject stale fencing tokens.
- [ ] **MC-32.T04** — Use compare-and-swap/conditional transactions for reservations and ownership transitions.
- [ ] **MC-32.T05** — Define leader election/quorum behavior and loss-of-quorum semantics.
- [ ] **MC-32.T06** — Do not rely on clock expiration alone for split-brain safety.
- [ ] **MC-32.T07** — Handle stale-controller restart, delayed/duplicated messages, network partition, and asymmetric partition.
- [ ] **MC-32.T08** — Protect against ABA so old lease/token cannot regain authority after release/reallocation.
- [ ] **MC-32.T09** — Reconcile divergent observations after partition heal without duplicate execution.
- [ ] **MC-32.T10** — Build multi-process/multi-node partition and leader-churn tests.
- [ ] **MC-32.T11** — Monitor invariants for duplicate owners, token regression, quorum loss, and stuck reconciliation.
- [ ] **MC-32.T12** — Document operator recovery for ambiguous ownership/stuck quorum.

#### Component-specific acceptance gates

- [ ] **MC-32.V01** — Partition/stale-writer tests prove at most one valid fenced owner.
- [ ] **MC-32.V02** — Execution plane rejects stale tokens even when stale schedulers continue sending commands.
- [ ] **MC-32.V03** — Reconnection resolves ambiguous state without duplicate execution or silent corruption.

#### Required deliverables / evidence

- [ ] **MC-32.E01** — Produce, version, and reference in release evidence: `distributed ownership/fencing design`.
- [ ] **MC-32.E02** — Produce, version, and reference in release evidence: `fencing token implementation`.
- [ ] **MC-32.E03** — Produce, version, and reference in release evidence: `partition/race harness`.
- [ ] **MC-32.E04** — Produce, version, and reference in release evidence: `split-brain runbook`.

#### Definition of done

- [ ] **MC-32.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-32.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-32.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-32.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-32.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-32.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-32.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-33 — Operator quarantine/freeze/disable control

**Audit finding:** A `quarantined` workload maps to the strongest tier, but there is no administrative freeze, node quarantine, scheduler disable, or kill-switch API.

**Original control coverage:** C059, C092

#### Engineering implementation checklist

- [ ] **MC-33.T01** — Define administrative controls for quarantining workload, node, runtime, site, accelerator, policy revision, or scheduler instance as applicable.
- [ ] **MC-33.T02** — Distinguish quarantine, drain, freeze-new-work, hard-disable, emergency-kill, and re-enable semantics.
- [ ] **MC-33.T03** — Implement authenticated/authorized API/CLI with reason, reference/ticket, actor, timestamp, and optional expiry.
- [ ] **MC-33.T04** — Persist/distribute controls so all scheduler instances enforce the same state.
- [ ] **MC-33.T05** — Check quarantine/disable before optimization scoring.
- [ ] **MC-33.T06** — Define handling for already-running workloads when a resource becomes quarantined.
- [ ] **MC-33.T07** — Provide emergency freeze that stops new placement without corrupting active leases.
- [ ] **MC-33.T08** — Prevent ordinary tenants from controlling administrative quarantine.
- [ ] **MC-33.T09** — Emit tamper-evident audit events and high-priority alerts for changes.
- [ ] **MC-33.T10** — Expose active controls safely in status/explain surfaces.
- [ ] **MC-33.T11** — Support expiring temporary controls with pre-expiry warning.
- [ ] **MC-33.T12** — Race placement against quarantine activation and define the exact commit boundary.

#### Component-specific acceptance gates

- [ ] **MC-33.V01** — Quarantined/disabled resources receive no new placements after committed activation.
- [ ] **MC-33.V02** — Emergency freeze is authorized, durable, auditable, reversible, and state-safe.
- [ ] **MC-33.V03** — Race tests prove no placement slips through after the control commit boundary.

#### Required deliverables / evidence

- [ ] **MC-33.E01** — Produce, version, and reference in release evidence: `quarantine/control schema`.
- [ ] **MC-33.E02** — Produce, version, and reference in release evidence: `admin API/CLI`.
- [ ] **MC-33.E03** — Produce, version, and reference in release evidence: `distributed control state`.
- [ ] **MC-33.E04** — Produce, version, and reference in release evidence: `quarantine race/audit tests`.

#### Definition of done

- [ ] **MC-33.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-33.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-33.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-33.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-33.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-33.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-33.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-34 — Fault-injection/recovery suite

**Audit finding:** No automated dependency failure, node loss, clock fault, partition, reconnect, controller loss, or recovery-objective tests are included.

**Original control coverage:** C060, C089

#### Engineering implementation checklist

- [ ] **MC-34.T01** — Build a deterministic fault-injection harness for CI/staging.
- [ ] **MC-34.T02** — Kill scheduler processes at state-transaction and external-handoff boundaries.
- [ ] **MC-34.T03** — Inject node disappearance, runtime failure, accelerator loss, site outage, dependency timeout, DNS failure, and provider rejection.
- [ ] **MC-34.T04** — Inject partition, delay, reorder, and duplication where the transport permits.
- [ ] **MC-34.T05** — Inject clock skew/jumps plus stale/future reports.
- [ ] **MC-34.T06** — Inject corrupt/partial state, failed config/policy activation, audit outage, and secret/attestation outage.
- [ ] **MC-34.T07** — Exercise reconnect/reconciliation after every outage/partition class.
- [ ] **MC-34.T08** — Measure detection time, recovery time, lost/duplicate work, and residual inconsistency against objectives.
- [ ] **MC-34.T09** — Assert isolation, residency, fencing, quota, and device exclusivity throughout faults.
- [ ] **MC-34.T10** — Automate pass/fail thresholds and capture fault timelines with telemetry.
- [ ] **MC-34.T11** — Add randomized chaos campaigns after deterministic cases are stable.
- [ ] **MC-34.T12** — Run on material resilience/state changes and before production certification.

#### Component-specific acceptance gates

- [ ] **MC-34.V01** — All documented failure classes have automated recovery evidence meeting stated bounds.
- [ ] **MC-34.V02** — No injected fault produces duplicate ownership, isolation/quota breach, or permanent unreconciled corruption.
- [ ] **MC-34.V03** — Fault runs produce reproducible evidence for the release bundle.

#### Required deliverables / evidence

- [ ] **MC-34.E01** — Produce, version, and reference in release evidence: `fault injection harness`.
- [ ] **MC-34.E02** — Produce, version, and reference in release evidence: `fault scenario catalog`.
- [ ] **MC-34.E03** — Produce, version, and reference in release evidence: `recovery assertions`.
- [ ] **MC-34.E04** — Produce, version, and reference in release evidence: `fault evidence reports`.

#### Definition of done

- [ ] **MC-34.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-34.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-34.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-34.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-34.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-34.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-34.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 4 — Performance and capacity certification

### MC-35 — Reproducible performance benchmark suite

**Audit finding:** No committed baseline harness or stored baseline covers decision latency, throughput, startup, CPU, memory, storage/network overhead, or power.

**Original control coverage:** C061, C063-C068

#### Engineering implementation checklist

- [ ] **MC-35.T01** — Create a committed benchmark harness independent of ad-hoc audit scripts.
- [ ] **MC-35.T02** — Define canonical runner classes and capture CPU, memory, OS, Python, dependencies, power settings, and build digest.
- [ ] **MC-35.T03** — Use deterministic seeded workload/node/topology datasets spanning small, typical, and maximum fleet sizes.
- [ ] **MC-35.T04** — Measure decision latency distribution, throughput, startup/import, CPU time, RSS/peak memory, allocation rate, state/storage I/O, network/dependency overhead, and relevant power/thermal impact.
- [ ] **MC-35.T05** — Benchmark cold and warm paths separately.
- [ ] **MC-35.T06** — Benchmark rejection-heavy, tie-heavy, large capability/topology, accelerator, quota-constrained, and no-candidate paths.
- [ ] **MC-35.T07** — Measure single-thread, concurrent, and multi-process modes matching deployment architecture.
- [ ] **MC-35.T08** — Store raw samples machine-readably and compute reproducible statistical summaries.
- [ ] **MC-35.T09** — Repeat enough runs to characterize variance and reject invalid/noisy environments.
- [ ] **MC-35.T10** — Pin benchmark tools and dataset revisions.
- [ ] **MC-35.T11** — Compare against versioned baselines using MC-36 thresholds.
- [ ] **MC-35.T12** — Archive per-release benchmark results with source/build/config digests.

#### Component-specific acceptance gates

- [ ] **MC-35.V01** — A clean runner reproduces the benchmark suite and comparable raw/results artifacts.
- [ ] **MC-35.V02** — Evidence covers required latency/resource dimensions, not only one p99 sample.
- [ ] **MC-35.V03** — Baseline variance is quantified enough to distinguish regression from noise.

#### Required deliverables / evidence

- [ ] **MC-35.E01** — Produce, version, and reference in release evidence: `benchmarks/ harness`.
- [ ] **MC-35.E02** — Produce, version, and reference in release evidence: `seeded datasets`.
- [ ] **MC-35.E03** — Produce, version, and reference in release evidence: `environment capture`.
- [ ] **MC-35.E04** — Produce, version, and reference in release evidence: `raw/results schema`.
- [ ] **MC-35.E05** — Produce, version, and reference in release evidence: `baseline report`.

#### Definition of done

- [ ] **MC-35.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-35.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-35.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-35.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-35.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-35.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-35.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-36 — Full performance thresholds and release regression gate

**Audit finding:** Only a p99/1,000-node objective is declared. p50/p95/worst-case, saturation, capacity model, and machine-enforced regression thresholds are absent.

**Original control coverage:** C062, C067, C069, C070

#### Engineering implementation checklist

- [ ] **MC-36.T01** — Define p50, p95, p99, max/worst-case, throughput, startup, CPU, memory, state I/O, and relevant power/thermal thresholds by deployment class.
- [ ] **MC-36.T02** — Separate absolute SLO ceilings from relative release-regression budgets.
- [ ] **MC-36.T03** — Define saturation points for node count, concurrent requests, candidate count, policy/topology size, and tenant count.
- [ ] **MC-36.T04** — Specify statistical method, sample count, warmup, confidence/noise allowance, and outlier handling.
- [ ] **MC-36.T05** — Store thresholds in machine-readable versioned policy consumed by CI.
- [ ] **MC-36.T06** — Block releases on threshold regression unless a scoped approved waiver applies.
- [ ] **MC-36.T07** — Track path-specific performance so median gains cannot hide tail/no-candidate regressions.
- [ ] **MC-36.T08** — Include worst-case/adversarial inputs to bound algorithmic complexity.
- [ ] **MC-36.T09** — Gate memory/queue growth and saturation recovery as well as latency.
- [ ] **MC-36.T10** — Define constrained-edge thresholds separately where appropriate.
- [ ] **MC-36.T11** — Generate trend reports from the same raw gate evidence.
- [ ] **MC-36.T12** — Require review/traceability when thresholds change.

#### Component-specific acceptance gates

- [ ] **MC-36.V01** — Release automation deterministically fails on mandatory performance/capacity regression.
- [ ] **MC-36.V02** — Threshold changes are versioned/approved rather than edited to make a release pass.
- [ ] **MC-36.V03** — Worst-case/saturation runs recover without unbounded resource growth.

#### Required deliverables / evidence

- [ ] **MC-36.E01** — Produce, version, and reference in release evidence: `performance threshold policy`.
- [ ] **MC-36.E02** — Produce, version, and reference in release evidence: `benchmark regression gate`.
- [ ] **MC-36.E03** — Produce, version, and reference in release evidence: `trend report`.
- [ ] **MC-36.E04** — Produce, version, and reference in release evidence: `performance waiver mechanism`.

#### Definition of done

- [ ] **MC-36.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-36.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-36.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-36.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-36.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-36.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-36.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 5 — Health, telemetry, tracing, and explainability

### MC-37 — Runtime health/readiness/dependency status surface

**Audit finding:** There is no status endpoint or command exposing health, readiness, version, active configuration, external dependency health, and capability set.

**Original control coverage:** C071

#### Engineering implementation checklist

- [ ] **MC-37.T01** — Expose separate liveness, readiness, and detailed status surfaces for library/service deployment modes.
- [ ] **MC-37.T02** — Report component/build version, schema versions, active policy/config revisions, runtime registry revision, and state schema version.
- [ ] **MC-37.T03** — Report health for identity, policy, topology, state, quota, attestation, execution, audit, and telemetry dependencies as applicable.
- [ ] **MC-37.T04** — Report active capabilities and explicitly degraded/disabled capabilities.
- [ ] **MC-37.T05** — Define readiness so safety-critical dependency loss makes the service unready when required.
- [ ] **MC-37.T06** — Report relevant last-sync/reconciliation times and staleness.
- [ ] **MC-37.T07** — Provide CLI status for environments without an endpoint.
- [ ] **MC-37.T08** — Authorize detailed status and keep minimal liveness appropriately redacted.
- [ ] **MC-37.T09** — Never expose secrets, raw tokens, cross-tenant workload details, sensitive paths, or raw policy contents.
- [ ] **MC-37.T10** — Version/test the status schema.
- [ ] **MC-37.T11** — Use real readiness semantics in deployment probes rather than process existence.
- [ ] **MC-37.T12** — Document operator action for degraded/unready states.

#### Component-specific acceptance gates

- [ ] **MC-37.V01** — Health/readiness respond correctly under dependency fault injection and recovery.
- [ ] **MC-37.V02** — Status identifies exact running versions/revisions without leaking sensitive data.
- [ ] **MC-37.V03** — Orchestration can safely use readiness to gate traffic.

#### Required deliverables / evidence

- [ ] **MC-37.E01** — Produce, version, and reference in release evidence: `status schema/API/CLI`.
- [ ] **MC-37.E02** — Produce, version, and reference in release evidence: `dependency health registry`.
- [ ] **MC-37.E03** — Produce, version, and reference in release evidence: `status contract tests`.
- [ ] **MC-37.E04** — Produce, version, and reference in release evidence: `probe/runbook documentation`.

#### Definition of done

- [ ] **MC-37.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-37.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-37.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-37.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-37.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-37.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-37.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-38 — Metrics implementation

**Audit finding:** Metric names are declared in `contract.py`, but the engine emits no counters/histograms/gauges and has no exporter.

**Original control coverage:** C072

#### Engineering implementation checklist

- [ ] **MC-38.T01** — Instrument request/classification/placement rates, successes, refusals, validation failures, dependency failures, and internal errors.
- [ ] **MC-38.T02** — Emit latency histograms for total decision and major stages including validation, policy, state/quota, filtering, scoring, external calls, and commit.
- [ ] **MC-38.T03** — Emit gauges for queue/in-flight, candidate counts, capacity/reservations, reconciliation lag, and dependency degradation.
- [ ] **MC-38.T04** — Count rejection classes, retries, cancellations, timeouts, circuit events, shed load, stale reports, and fencing conflicts.
- [ ] **MC-38.T05** — Instrument quota/fairness and accelerator utilization/fragmentation when implemented.
- [ ] **MC-38.T06** — Define stable metric names, units, descriptions, and label-cardinality budgets.
- [ ] **MC-38.T07** — Avoid raw request/workload/tenant/node IDs or arbitrary text as unbounded labels.
- [ ] **MC-38.T08** — Export using OpenTelemetry/Prometheus or organization standard and version semantic conventions.
- [ ] **MC-38.T09** — Test metric changes on positive/negative paths.
- [ ] **MC-38.T10** — Benchmark instrumentation overhead.
- [ ] **MC-38.T11** — Ensure exporter failure does not block/corrupt placement.
- [ ] **MC-38.T12** — Create recording rules/SLO metrics for dashboards/alerts.

#### Component-specific acceptance gates

- [ ] **MC-38.V01** — Every major success/failure/saturation path changes expected low-cardinality metrics.
- [ ] **MC-38.V02** — Cardinality and instrumentation overhead remain within fleet-scale limits.
- [ ] **MC-38.V03** — Exporter outage does not block or corrupt decisions.

#### Required deliverables / evidence

- [ ] **MC-38.E01** — Produce, version, and reference in release evidence: `metrics instrumentation`.
- [ ] **MC-38.E02** — Produce, version, and reference in release evidence: `metric catalog/conventions`.
- [ ] **MC-38.E03** — Produce, version, and reference in release evidence: `exporter configuration`.
- [ ] **MC-38.E04** — Produce, version, and reference in release evidence: `metric tests`.

#### Definition of done

- [ ] **MC-38.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-38.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-38.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-38.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-38.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-38.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-38.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-39 — Structured operational logging

**Audit finding:** No stable structured log/event emission exists for workload, tenant, node, operation, decision, and error identifiers.

**Original control coverage:** C073

#### Engineering implementation checklist

- [ ] **MC-39.T01** — Define a versioned structured logging schema using JSON or organization standard.
- [ ] **MC-39.T02** — Include timestamp, severity, event code, build, operation, correlation IDs, safe workload/tenant/node refs, lease, revisions, outcome, and stable error code.
- [ ] **MC-39.T03** — Use stable event codes instead of requiring free-text parsing.
- [ ] **MC-39.T04** — Define mandatory/optional fields for decision, refusal, dependency, reconciliation, admin, startup, and shutdown events.
- [ ] **MC-39.T05** — Redact secrets, tokens, sensitive policy values, and cross-tenant details.
- [ ] **MC-39.T06** — Bound/sanitize untrusted strings to prevent log injection/control-character abuse.
- [ ] **MC-39.T07** — Define levels and rate limiting without suppressing security/audit-critical events.
- [ ] **MC-39.T08** — Propagate trace/span IDs when tracing is active.
- [ ] **MC-39.T09** — Add schema-validation and golden-log tests.
- [ ] **MC-39.T10** — Define safe sink-slow/unavailable behavior and hosting-layer rotation/transport expectations.
- [ ] **MC-39.T11** — Correlate operator-visible error IDs with logs while hiding stack traces from ordinary callers.
- [ ] **MC-39.T12** — Document separation between operational logs and security audit ledger.

#### Component-specific acceptance gates

- [ ] **MC-39.V01** — Major operation/error paths emit schema-valid logs with stable correlation fields.
- [ ] **MC-39.V02** — Untrusted input cannot forge log structure or leak secrets/cross-tenant data.
- [ ] **MC-39.V03** — Logging remains bounded during burst/overload.

#### Required deliverables / evidence

- [ ] **MC-39.E01** — Produce, version, and reference in release evidence: `logging schema/catalog`.
- [ ] **MC-39.E02** — Produce, version, and reference in release evidence: `structured logger`.
- [ ] **MC-39.E03** — Produce, version, and reference in release evidence: `redaction/sanitization`.
- [ ] **MC-39.E04** — Produce, version, and reference in release evidence: `logging tests`.

#### Definition of done

- [ ] **MC-39.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-39.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-39.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-39.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-39.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-39.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-39.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-40 — Distributed tracing

**Audit finding:** No trace/span context propagation or trace export exists.

**Original control coverage:** C074

#### Engineering implementation checklist

- [ ] **MC-40.T01** — Adopt distributed trace propagation such as W3C Trace Context with OpenTelemetry-compatible instrumentation.
- [ ] **MC-40.T02** — Create spans for validation, classification, policy, state/quota, filtering/scoring, topology/data/accelerator lookups, commit, and execution handoff.
- [ ] **MC-40.T03** — Propagate context across every supported RPC/event boundary.
- [ ] **MC-40.T04** — Define stable low-cardinality span names and bounded attributes.
- [ ] **MC-40.T05** — Include revision references needed for diagnosis without embedding sensitive payloads.
- [ ] **MC-40.T06** — Map unified error outcomes to trace status.
- [ ] **MC-40.T07** — Define head/tail sampling aligned with privacy/incident requirements.
- [ ] **MC-40.T08** — Treat baggage as diagnostic only; never trust it for identity/authorization.
- [ ] **MC-40.T09** — Test context propagation across adjacent-plane mocks/reference integrations.
- [ ] **MC-40.T10** — Measure tracing overhead/backpressure and make exporter failure non-blocking within bounds.
- [ ] **MC-40.T11** — Correlate traces with metrics, logs, and audit via shared IDs.
- [ ] **MC-40.T12** — Apply telemetry retention/access governance.

#### Component-specific acceptance gates

- [ ] **MC-40.V01** — End-to-end placement is traceable across supported boundaries with one trace context.
- [ ] **MC-40.V02** — Trace metadata cannot become an authorization source or leak prohibited tenant data.
- [ ] **MC-40.V03** — Tracing/exporter failure stays within resilience/performance budgets.

#### Required deliverables / evidence

- [ ] **MC-40.E01** — Produce, version, and reference in release evidence: `tracing instrumentation`.
- [ ] **MC-40.E02** — Produce, version, and reference in release evidence: `trace semantic conventions`.
- [ ] **MC-40.E03** — Produce, version, and reference in release evidence: `propagation tests`.
- [ ] **MC-40.E04** — Produce, version, and reference in release evidence: `sampling/export configuration`.

#### Definition of done

- [ ] **MC-40.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-40.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-40.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-40.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-40.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-40.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-40.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-41 — Production explainability surface

**Audit finding:** 4.2.0 adds deterministic decision metadata and aggregate refusal counts, but there is no operator explain API/UI linking decisions to policy revision, topology, data path, infrastructure graph, and release lineage.

**Original control coverage:** C075-C078

#### Engineering implementation checklist

- [ ] **MC-41.T01** — Define an operator explain schema keyed by immutable decision/request ID.
- [ ] **MC-41.T02** — Reference immutable input snapshots/digests so historical explanations remain reproducible.
- [ ] **MC-41.T03** — Explain canonical classification and why the selected isolation tier/runtime is required.
- [ ] **MC-41.T04** — Report candidate counts after each hard-filter stage using stable rejection reason codes.
- [ ] **MC-41.T05** — Explain winning score as named terms such as latency, topology, data locality, fairness, accelerator locality, and power/cost where used.
- [ ] **MC-41.T06** — Include policy/config/topology/runtime-registry revisions and verified attestation references.
- [ ] **MC-41.T07** — Include selected data-path, accelerator, and lease references when applicable.
- [ ] **MC-41.T08** — Link to application release lineage and infrastructure graph revision without exposing unauthorized tenant/resource details.
- [ ] **MC-41.T09** — Provide distinct caller-safe and privileged operator views with authorization/redaction.
- [ ] **MC-41.T10** — Persist or deterministically reconstruct explanations for the audit retention window.
- [ ] **MC-41.T11** — Test that explanation output matches actual engine behavior and decision metadata.
- [ ] **MC-41.T12** — Privacy-test explain surfaces for cross-tenant candidate inference/high-cardinality leakage.

#### Component-specific acceptance gates

- [ ] **MC-41.V01** — Authorized operators can reconstruct why a decision/refusal occurred from immutable revisions and stable reason codes.
- [ ] **MC-41.V02** — Explain output is consistent with the exact engine path.
- [ ] **MC-41.V03** — Caller-safe explanation never reveals another tenant, secret, or sensitive topology detail.

#### Required deliverables / evidence

- [ ] **MC-41.E01** — Produce, version, and reference in release evidence: `explain schema/API/CLI`.
- [ ] **MC-41.E02** — Produce, version, and reference in release evidence: `decision snapshot metadata`.
- [ ] **MC-41.E03** — Produce, version, and reference in release evidence: `explain renderer`.
- [ ] **MC-41.E04** — Produce, version, and reference in release evidence: `consistency/privacy tests`.

#### Definition of done

- [ ] **MC-41.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-41.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-41.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-41.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-41.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-41.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-41.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-42 — Telemetry governance, dashboards, and alerts

**Audit finding:** No retention/sampling/privacy/export policy, dashboards, or alerts distinguish load, degradation, rejection, dependency failure, attack, and software defect.

**Original control coverage:** C079, C080

#### Engineering implementation checklist

- [ ] **MC-42.T01** — Classify sensitive fields across metrics, logs, traces, audit events, and explain snapshots.
- [ ] **MC-42.T02** — Set retention by data class/environment and incident-hold policy.
- [ ] **MC-42.T03** — Define sampling for logs/traces and explicitly non-sampled security/audit events.
- [ ] **MC-42.T04** — Define encrypted export destinations, access controls, tenant separation, and allowed jurisdictions.
- [ ] **MC-42.T05** — Document deletion, retention exceptions, and governance ownership.
- [ ] **MC-42.T06** — Create dashboards for rate, latency percentiles, success/refusal, saturation, queue, capacity, fairness, dependencies, and reconciliation.
- [ ] **MC-42.T07** — Create separate alert classes for ordinary load, degradation, policy rejection, auth/security indicators, fencing/state anomalies, and software defects.
- [ ] **MC-42.T08** — Use SLO/error-budget burn alerts where appropriate rather than only static thresholds.
- [ ] **MC-42.T09** — Link actionable alerts to runbooks and owner/escalation path.
- [ ] **MC-42.T10** — Test alert rules using synthetic events and fault injection.
- [ ] **MC-42.T11** — Review dashboard/alert cardinality and storage/cost at fleet scale.
- [ ] **MC-42.T12** — Schedule recurring privacy/access/retention review.

#### Component-specific acceptance gates

- [ ] **MC-42.V01** — Dashboards distinguish capacity/load, policy rejection, dependency degradation, attack signals, and software defects.
- [ ] **MC-42.V02** — Synthetic/fault scenarios trigger the expected actionable alerts.
- [ ] **MC-42.V03** — Retention/export/access behavior matches governance policy.

#### Required deliverables / evidence

- [ ] **MC-42.E01** — Produce, version, and reference in release evidence: `TELEMETRY_GOVERNANCE.md`.
- [ ] **MC-42.E02** — Produce, version, and reference in release evidence: `dashboard definitions`.
- [ ] **MC-42.E03** — Produce, version, and reference in release evidence: `alert rules`.
- [ ] **MC-42.E04** — Produce, version, and reference in release evidence: `alert test fixtures`.

#### Definition of done

- [ ] **MC-42.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-42.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-42.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-42.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-42.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-42.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-42.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 6 — Verification, integration, compatibility, and release evidence

### MC-43 — Complete public contract tests

**Audit finding:** Core unit tests exercise behavior, but there are no schema-level conformance tests for every public payload/error/version transition.

**Original control coverage:** C082

#### Engineering implementation checklist

- [ ] **MC-43.T01** — Inventory every public callable, schema, error, status/explain surface, config/policy input, and adjacent-plane message.
- [ ] **MC-43.T02** — Create minimum/typical/maximal valid fixtures for every supported public version.
- [ ] **MC-43.T03** — Create negative fixtures for required-field absence, types, ranges, duplicates, stale/future time, enums, versions, and cross-field conflicts.
- [ ] **MC-43.T04** — Assert exact stable error codes/details rather than matching human prose.
- [ ] **MC-43.T05** — Test serialization/deserialization round trips and canonicalization.
- [ ] **MC-43.T06** — Test unknown-field/unknown-enum behavior according to version policy.
- [ ] **MC-43.T07** — Test current/N-1 version negotiation/interoperability.
- [ ] **MC-43.T08** — Assert deterministic outputs for canonical fixtures including tie-breaking/reason ordering.
- [ ] **MC-43.T09** — Test security redaction of errors/status/explain payloads.
- [ ] **MC-43.T10** — Generate schema-field/error-code contract coverage reports.
- [ ] **MC-43.T11** — Run local contract tests independently of pk_core.
- [ ] **MC-43.T12** — Run separate pk_core conformance tests when available and report skips as missing evidence, never pass.

#### Component-specific acceptance gates

- [ ] **MC-43.V01** — Every public payload/error/version path has executable contract evidence.
- [ ] **MC-43.V02** — Schema/error compatibility regressions fail before integration testing.
- [ ] **MC-43.V03** — Reports clearly distinguish pass, fail, skip/missing evidence, waived, and unsupported.

#### Required deliverables / evidence

- [ ] **MC-43.E01** — Produce, version, and reference in release evidence: `contract test suite`.
- [ ] **MC-43.E02** — Produce, version, and reference in release evidence: `golden fixtures`.
- [ ] **MC-43.E03** — Produce, version, and reference in release evidence: `contract coverage report`.
- [ ] **MC-43.E04** — Produce, version, and reference in release evidence: `version compatibility fixtures`.

#### Definition of done

- [ ] **MC-43.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-43.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-43.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-43.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-43.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-43.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-43.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-44 — Adjacent-layer integration matrix

**Audit finding:** No executable tests are bundled for PLN-02, PLN-04, PLN-05, GAP-02, GAP-03, GAP-10, execution tiers, or provider variants.

**Original control coverage:** C030, C083

#### Engineering implementation checklist

- [ ] **MC-44.T01** — Create an adjacent-layer integration matrix for PLN-02, PLN-04, PLN-05, GAP-02, GAP-03, GAP-10, INV-33, runtimes, and providers.
- [ ] **MC-44.T02** — For each integration define direction, transport/API, schema version, identity, authorization, timeout, retry/idempotency, owner, and failure semantics.
- [ ] **MC-44.T03** — Provide hermetic mocks/fakes for CI plus reference/real integrations for certification.
- [ ] **MC-44.T04** — Test startup/version negotiation and incompatible-peer rejection.
- [ ] **MC-44.T05** — Test end-to-end placement from application intent through execution admission/lease acknowledgement.
- [ ] **MC-44.T06** — Test dependency unavailable, slow, stale, malformed, unauthorized, incompatible, and degraded scenarios.
- [ ] **MC-44.T07** — Test conflicting topology/residency/quota/policy constraints across boundaries.
- [ ] **MC-44.T08** — Test cancellation/retry/idempotency across multi-step handoffs.
- [ ] **MC-44.T09** — Test reconciliation after execution rejection/lost lease.
- [ ] **MC-44.T10** — Capture traces/logs/evidence and map results into RTM.
- [ ] **MC-44.T11** — Version fixtures with compatibility matrix.
- [ ] **MC-44.T12** — Periodically prove mock behavior matches real peer contracts.

#### Component-specific acceptance gates

- [ ] **MC-44.V01** — Every supported adjacent layer has positive and negative executable integration evidence.
- [ ] **MC-44.V02** — Reference end-to-end tests prove selected runtime/tier/node/resources are enforced downstream.
- [ ] **MC-44.V03** — Peer failure/incompatibility produces documented safe behavior without state leak or constraint downgrade.

#### Required deliverables / evidence

- [ ] **MC-44.E01** — Produce, version, and reference in release evidence: `integration matrix`.
- [ ] **MC-44.E02** — Produce, version, and reference in release evidence: `adjacent-plane mocks/fakes`.
- [ ] **MC-44.E03** — Produce, version, and reference in release evidence: `reference integration tests`.
- [ ] **MC-44.E04** — Produce, version, and reference in release evidence: `integration evidence reports`.

#### Definition of done

- [ ] **MC-44.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-44.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-44.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-44.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-44.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-44.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-44.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-45 — Platform/runtime compatibility matrix tests

**Audit finding:** No CI matrix spans CPU architectures, OSes, hypervisors, runtime implementations, providers, or protocol/schema versions.

**Original control coverage:** C084, C093

#### Engineering implementation checklist

- [ ] **MC-45.T01** — Define supported compatibility across CPU architectures, OSes, Python versions, hypervisors/execution tiers, runtimes, providers, state stores, and protocol/schema versions.
- [ ] **MC-45.T02** — Classify combinations as required, best-effort, experimental, or unsupported.
- [ ] **MC-45.T03** — Create CI axes covering each required combination or documented representative equivalence.
- [ ] **MC-45.T04** — Include x86_64/ARM64 where support is claimed and avoid implying unsupported architectures.
- [ ] **MC-45.T05** — Test platform-specific clock, filesystem/path, process, concurrency, locale/encoding, and networking behavior.
- [ ] **MC-45.T06** — Test hypervisor/runtime capability differences and reject invalid combinations before placement.
- [ ] **MC-45.T07** — Test mixed protocol/schema versions during rolling upgrades.
- [ ] **MC-45.T08** — Capture environment/build metadata for every result.
- [ ] **MC-45.T09** — Track flaky environment failures as defects rather than hiding them as passes.
- [ ] **MC-45.T10** — Update matrix for dependency/platform EOL under version policy.
- [ ] **MC-45.T11** — Block release on failed/missing required cells absent waiver.
- [ ] **MC-45.T12** — Publish matrix evidence in release bundle.

#### Component-specific acceptance gates

- [ ] **MC-45.V01** — Every claimed supported combination has current automated evidence or approved equivalence rationale.
- [ ] **MC-45.V02** — Unsupported combinations are detected explicitly before unpredictable runtime failure.
- [ ] **MC-45.V03** — Release gate blocks failed/missing required matrix cells.

#### Required deliverables / evidence

- [ ] **MC-45.E01** — Produce, version, and reference in release evidence: `compatibility matrix`.
- [ ] **MC-45.E02** — Produce, version, and reference in release evidence: `matrix CI workflows`.
- [ ] **MC-45.E03** — Produce, version, and reference in release evidence: `environment capture`.
- [ ] **MC-45.E04** — Produce, version, and reference in release evidence: `compatibility reports`.

#### Definition of done

- [ ] **MC-45.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-45.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-45.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-45.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-45.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-45.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-45.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-46 — Fuzz/property-based testing

**Audit finding:** No fuzz corpus/property suite targets constructors, schema boundaries, classifier inputs, candidate sets, or error serialization.

**Original control coverage:** C085

#### Engineering implementation checklist

- [ ] **MC-46.T01** — Adopt property-based/fuzz tools compatible with the implementation and pin tool versions.
- [ ] **MC-46.T02** — Fuzz workload/node/config/policy/schema constructors with arbitrary Unicode, lengths, malformed collections, numeric boundaries, NaN/Infinity, and duplicates.
- [ ] **MC-46.T03** — Fuzz serialized parsers/RPC/WIT/JSON/Protobuf boundaries with malformed, truncated, and oversized payloads.
- [ ] **MC-46.T04** — Assert invariants including classification idempotence, deterministic ordering, no tier downgrade, no over-capacity placement, safe tenant isolation, and valid error envelopes.
- [ ] **MC-46.T05** — Randomize candidate/topology/occupancy ordering to prove order independence where required.
- [ ] **MC-46.T06** — Fuzz lifecycle/state transitions and replay sequences.
- [ ] **MC-46.T07** — Apply CPU/memory/time budgets per case to detect complexity/resource-exhaustion defects.
- [ ] **MC-46.T08** — Persist minimized failing cases as regression corpus.
- [ ] **MC-46.T09** — Run fast fuzz smoke on changes and longer scheduled/release campaigns.
- [ ] **MC-46.T10** — Use native sanitizers/instrumented dependencies where applicable.
- [ ] **MC-46.T11** — Treat crash, hang, invariant failure, and resource blowup as defects.
- [ ] **MC-46.T12** — Publish corpus/run/coverage/failure metrics in release evidence.

#### Component-specific acceptance gates

- [ ] **MC-46.V01** — Fuzz/property campaigns complete with no unresolved crashes, hangs, or invariant violations.
- [ ] **MC-46.V02** — Every discovered issue becomes minimized deterministic regression coverage.
- [ ] **MC-46.V03** — Resource-exhaustion fuzz remains bounded by configured budgets.

#### Required deliverables / evidence

- [ ] **MC-46.E01** — Produce, version, and reference in release evidence: `property/fuzz harness`.
- [ ] **MC-46.E02** — Produce, version, and reference in release evidence: `seed/minimized corpus`.
- [ ] **MC-46.E03** — Produce, version, and reference in release evidence: `fuzz CI jobs`.
- [ ] **MC-46.E04** — Produce, version, and reference in release evidence: `fuzz campaign report`.

#### Definition of done

- [ ] **MC-46.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-46.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-46.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-46.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-46.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-46.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-46.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-47 — Distributed concurrency/race tests

**Audit finding:** A local two-thread oversubscription test now exists, but there is no multi-process/distributed race, stale-writer, ABA/fencing, or split-brain test.

**Original control coverage:** C086

#### Engineering implementation checklist

- [ ] **MC-47.T01** — Build a multi-process harness using production durable-state/fencing interfaces.
- [ ] **MC-47.T02** — Race schedulers for one remaining slot, one quota unit, and one accelerator partition.
- [ ] **MC-47.T03** — Test concurrent duplicate workload/request IDs across processes.
- [ ] **MC-47.T04** — Inject stale read followed by conditional write and ensure stale writer loses.
- [ ] **MC-47.T05** — Test ABA by release/reallocate then replay an old token/command.
- [ ] **MC-47.T06** — Partition scheduler instances from state/consensus/execution and simulate split brain.
- [ ] **MC-47.T07** — Test leader churn while requests are in flight.
- [ ] **MC-47.T08** — Delay/reorder/duplicate downstream acknowledgements.
- [ ] **MC-47.T09** — Crash the winning scheduler after reserve but before response and reconcile after recovery.
- [ ] **MC-47.T10** — Continuously assert at-most-one owner, capacity/quota bounds, monotonic fencing, and tenant isolation.
- [ ] **MC-47.T11** — Run high-iteration randomized schedules for rare races.
- [ ] **MC-47.T12** — Persist deterministic seeds/event timelines for failures.

#### Component-specific acceptance gates

- [ ] **MC-47.V01** — Distributed race tests show no duplicate ownership, quota/capacity breach, stale-token acceptance, or permanent orphan.
- [ ] **MC-47.V02** — Each injected race has a safe deterministic outcome or explicit retry path.
- [ ] **MC-47.V03** — Failures reproduce from saved timelines/seeds.

#### Required deliverables / evidence

- [ ] **MC-47.E01** — Produce, version, and reference in release evidence: `distributed race harness`.
- [ ] **MC-47.E02** — Produce, version, and reference in release evidence: `race scenario suite`.
- [ ] **MC-47.E03** — Produce, version, and reference in release evidence: `invariant monitor`.
- [ ] **MC-47.E04** — Produce, version, and reference in release evidence: `event timeline capture`.

#### Definition of done

- [ ] **MC-47.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-47.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-47.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-47.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-47.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-47.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-47.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-48 — Benchmark/soak/burst/fleet-scale certification

**Audit finding:** No soak, burst, overload, fleet-scale, scale-in/out, or recovery benchmark suite is committed.

**Original control coverage:** C088

#### Engineering implementation checklist

- [ ] **MC-48.T01** — Define fleet-scale certification sizes for supported edge/datacenter deployments.
- [ ] **MC-48.T02** — Run steady-state soak long enough to expose memory, file-descriptor, thread, queue, and state growth.
- [ ] **MC-48.T03** — Run burst tests with request spikes and topology/capability updates.
- [ ] **MC-48.T04** — Run controlled overload beyond capacity to validate shedding, queue bounds, and recovery.
- [ ] **MC-48.T05** — Scale out under load and ensure new capacity is used only after full health/attestation/topology registration.
- [ ] **MC-48.T06** — Scale in/drain under load and prevent new placements on draining resources.
- [ ] **MC-48.T07** — Repeat fail/recover cycles to detect state leaks/reconciliation backlog.
- [ ] **MC-48.T08** — Measure latency, throughput, errors, resource use, state conflicts, telemetry overhead, and fairness throughout.
- [ ] **MC-48.T09** — Assert deterministic/safety invariants at scale.
- [ ] **MC-48.T10** — Use mixed tenant/workload and accelerator/topology constraints where supported.
- [ ] **MC-48.T11** — Capture environment/config/policy/build digests plus raw metrics.
- [ ] **MC-48.T12** — Apply MC-36 pass/fail thresholds and archive evidence.

#### Component-specific acceptance gates

- [ ] **MC-48.V01** — Soak/burst/overload/scale tests meet resource, latency, fairness, and recovery thresholds.
- [ ] **MC-48.V02** — No leak/state divergence accumulates over certification duration.
- [ ] **MC-48.V03** — Scale/overload recovery preserves all safety invariants.

#### Required deliverables / evidence

- [ ] **MC-48.E01** — Produce, version, and reference in release evidence: `fleet-scale scenarios`.
- [ ] **MC-48.E02** — Produce, version, and reference in release evidence: `soak/burst runner`.
- [ ] **MC-48.E03** — Produce, version, and reference in release evidence: `resource/invariant monitors`.
- [ ] **MC-48.E04** — Produce, version, and reference in release evidence: `certification reports`.

#### Definition of done

- [ ] **MC-48.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-48.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-48.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-48.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-48.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-48.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-48.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-49 — Machine-readable release evidence bundle

**Audit finding:** No generated evidence ledger, signed gate result, SBOM, provenance attestation, checksum manifest, or release certificate is included.

**Original control coverage:** C090, C100

#### Engineering implementation checklist

- [ ] **MC-49.T01** — Define a machine-readable release-evidence manifest with component version, source commit, build digest, environment, timestamp, and signer.
- [ ] **MC-49.T02** — Include RTM, unit/contract/integration/security/fuzz/fault/compatibility/benchmark/soak results with immutable digests.
- [ ] **MC-49.T03** — Include SBOM, lock digest, vulnerability summary, license inventory, checksums, and build provenance.
- [ ] **MC-49.T04** — Include approved architecture/requirements/policy/schema compatibility baselines.
- [ ] **MC-49.T05** — Represent skipped/not-run separately from pass and require waiver for mandatory missing evidence.
- [ ] **MC-49.T06** — Include external prerequisite versions/evidence for pk_core/PLN/GAP/INV integrations.
- [ ] **MC-49.T07** — Sign evidence and release-artifact manifests with managed release identity.
- [ ] **MC-49.T08** — Provide offline verification of signatures, hashes, schema, references, and required evidence presence.
- [ ] **MC-49.T09** — Store evidence immutably through supported release lifetime.
- [ ] **MC-49.T10** — Generate a human-readable release certificate from the same authoritative manifest.
- [ ] **MC-49.T11** — Make production exit gate consume exactly this manifest.
- [ ] **MC-49.T12** — Block publication on incomplete, stale, unsigned, or version-inconsistent evidence.

#### Component-specific acceptance gates

- [ ] **MC-49.V01** — Offline verification proves artifacts/evidence belong to one source/build and are unmodified.
- [ ] **MC-49.V02** — Skipped/missing/waived controls cannot appear as passes.
- [ ] **MC-49.V03** — Production gate consumes the exact signed evidence shipped with release.

#### Required deliverables / evidence

- [ ] **MC-49.E01** — Produce, version, and reference in release evidence: `release evidence schema/manifest`.
- [ ] **MC-49.E02** — Produce, version, and reference in release evidence: `evidence collector`.
- [ ] **MC-49.E03** — Produce, version, and reference in release evidence: `sign/verify tooling`.
- [ ] **MC-49.E04** — Produce, version, and reference in release evidence: `signed release certificate`.

#### Definition of done

- [ ] **MC-49.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-49.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-49.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-49.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-49.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-49.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-49.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Phase 7 — Production operations, lifecycle governance, and release control

### MC-50 — Support commitment and error-budget operating policy

**Audit finding:** SLOs exist, but support hours, paging policy, escalation ownership, budget burn action, and breach procedure are absent.

**Original control coverage:** C091, C097

#### Engineering implementation checklist

- [ ] **MC-50.T01** — Define production SLOs for availability, successful placement rate, scheduler latency, recovery/reconciliation, and critical dependencies.
- [ ] **MC-50.T02** — Define error-budget windows/calculation for each SLO.
- [ ] **MC-50.T03** — Define support coverage by deployment class.
- [ ] **MC-50.T04** — Define paging thresholds based on budget burn, safety invariant violations, dependency outage, and widespread refusal/capacity issues.
- [ ] **MC-50.T05** — Map alerts to primary/backup owner and escalation authority.
- [ ] **MC-50.T06** — Define burn-trigger actions such as investigate, freeze, rollback, capacity intervention, or incident declaration.
- [ ] **MC-50.T07** — Define narrow auditable maintenance/exclusion rules.
- [ ] **MC-50.T08** — Generate periodic error-budget reports and review trends.
- [ ] **MC-50.T09** — Tie rollout/release policy to budget where required by operations governance.
- [ ] **MC-50.T10** — Define communications expectations for prolonged incidents/SLO breach.
- [ ] **MC-50.T11** — Require postmortem and follow-up for defined budget burn thresholds.
- [ ] **MC-50.T12** — Review SLOs against benchmark/capacity reality on a fixed cadence.

#### Component-specific acceptance gates

- [ ] **MC-50.V01** — SLO/error-budget calculations derive from real telemetry and pass synthetic incident tests.
- [ ] **MC-50.V02** — Paging/escalation and release-freeze actions trigger at documented burn levels.
- [ ] **MC-50.V03** — Support ownership/response commitments are current and reviewable.

#### Required deliverables / evidence

- [ ] **MC-50.E01** — Produce, version, and reference in release evidence: `SLO_ERROR_BUDGET.md`.
- [ ] **MC-50.E02** — Produce, version, and reference in release evidence: `SLO recording rules`.
- [ ] **MC-50.E03** — Produce, version, and reference in release evidence: `burn-rate alerts`.
- [ ] **MC-50.E04** — Produce, version, and reference in release evidence: `support/escalation policy`.

#### Definition of done

- [ ] **MC-50.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-50.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-50.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-50.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-50.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-50.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-50.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-51 — Canary/staged rollout automation

**Audit finding:** `OPERATIONS.md` describes manual rollback intent, but there is no canary controller, staged rollout policy, automated health gate, or rollback trigger.

**Original control coverage:** C092

#### Engineering implementation checklist

- [ ] **MC-51.T01** — Define rollout units by environment, site, scheduler shard, tenant cohort, or traffic percentage to constrain blast radius.
- [ ] **MC-51.T02** — Define ordered rollout stages and minimum observation time/traffic at each stage.
- [ ] **MC-51.T03** — Select canary gates from SLOs, errors, tail latency, refusal mix, state conflicts, auth/security signals, resource use, and reconciliation health.
- [ ] **MC-51.T04** — Automate promotion only when mandatory gates pass; require auditable override for exceptions.
- [ ] **MC-51.T05** — Automate rollback on safety/security/state invariant failure or configured health thresholds.
- [ ] **MC-51.T06** — Verify rollback compatibility with state/schema/policy revisions before rollout starts.
- [ ] **MC-51.T07** — Govern feature flags with owner, expiry, safe default, and applicability limits.
- [ ] **MC-51.T08** — Provide emergency freeze/disable independent of normal deployment tooling.
- [ ] **MC-51.T09** — Test mixed old/new scheduler and adjacent-plane versions during partial rollout.
- [ ] **MC-51.T10** — Record stage, cohort, build, policy/config, gate results, operator actions, and rollback reason.
- [ ] **MC-51.T11** — Inject regressions in staging to prove automatic rollback.
- [ ] **MC-51.T12** — Document recovery when rollback itself fails or newer state is not backward-compatible.

#### Component-specific acceptance gates

- [ ] **MC-51.V01** — A deliberately faulty canary is stopped/rolled back before wider promotion.
- [ ] **MC-51.V02** — Rollout records provide complete lineage from build/cohort to health-gate decision.
- [ ] **MC-51.V03** — Mixed-version rolling operation satisfies supported compatibility rules.

#### Required deliverables / evidence

- [ ] **MC-51.E01** — Produce, version, and reference in release evidence: `rollout/canary policy`.
- [ ] **MC-51.E02** — Produce, version, and reference in release evidence: `promotion/rollback automation`.
- [ ] **MC-51.E03** — Produce, version, and reference in release evidence: `health gate definitions`.
- [ ] **MC-51.E04** — Produce, version, and reference in release evidence: `rollout audit records`.

#### Definition of done

- [ ] **MC-51.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-51.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-51.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-51.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-51.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-51.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-51.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-52 — Vulnerability/patch/EOL policy

**Audit finding:** No patch SLA, vulnerability triage process, supported branch policy, dependency update cadence, or EOL schedule exists.

**Original control coverage:** C094

#### Engineering implementation checklist

- [ ] **MC-52.T01** — Define vulnerability severity classification and remediation SLAs.
- [ ] **MC-52.T02** — Inventory direct/transitive dependencies and subscribe to relevant advisories.
- [ ] **MC-52.T03** — Run dependency, source, secret, and artifact/container scans where applicable in CI/release.
- [ ] **MC-52.T04** — Define emergency patch workflow for actively exploited issues while preserving minimum verification/evidence gates.
- [ ] **MC-52.T05** — Maintain supported release branches and identify which versions receive security fixes.
- [ ] **MC-52.T06** — Define dependency update cadence and owners for cryptographic, identity, runtime, and other libraries.
- [ ] **MC-52.T07** — Publish EOL schedule/notice for component, schemas, runtimes, and platforms.
- [ ] **MC-52.T08** — Use the waiver process for unpatchable findings with compensating controls and finite expiry.
- [ ] **MC-52.T09** — Regenerate SBOM and rescan after dependency changes.
- [ ] **MC-52.T10** — Verify downloaded dependency/build-tool provenance/signatures/hashes where feasible.
- [ ] **MC-52.T11** — Track vulnerability age and SLA compliance metrics.
- [ ] **MC-52.T12** — Test patch/upgrade rollback and compatibility before production rollout.

#### Component-specific acceptance gates

- [ ] **MC-52.V01** — Known vulnerabilities are triaged/remediated or formally waived within policy.
- [ ] **MC-52.V02** — EOL versions are identified and blocked from new deployment after policy dates.
- [ ] **MC-52.V03** — Release evidence includes current dependency/vulnerability status.

#### Required deliverables / evidence

- [ ] **MC-52.E01** — Produce, version, and reference in release evidence: `VULNERABILITY_PATCH_EOL.md`.
- [ ] **MC-52.E02** — Produce, version, and reference in release evidence: `scanner workflows`.
- [ ] **MC-52.E03** — Produce, version, and reference in release evidence: `supported branch/EOL matrix`.
- [ ] **MC-52.E04** — Produce, version, and reference in release evidence: `vulnerability exception records`.

#### Definition of done

- [ ] **MC-52.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-52.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-52.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-52.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-52.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-52.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-52.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-53 — State backup/reconstruction procedure

**Audit finding:** No formal backup/restore/reconstruction method exists for placement state because durable state is not implemented locally.

**Original control coverage:** C095

#### Engineering implementation checklist

- [ ] **MC-53.T01** — Classify durable scheduler state by criticality and reconstructability after MC-31.
- [ ] **MC-53.T02** — Define backup scope for leases/occupancy/quotas, policy/config history, audit checkpoints, and non-reconstructable metadata.
- [ ] **MC-53.T03** — Define RPO/RTO by deployment class and align snapshot/log retention.
- [ ] **MC-53.T04** — Encrypt backups with independent access control and integrity validation.
- [ ] **MC-53.T05** — Coordinate snapshots with transactional state for internally consistent recovery points.
- [ ] **MC-53.T06** — Document restore into clean infrastructure, same-version, and supported-upgrade scenarios.
- [ ] **MC-53.T07** — Define reconstruction from authoritative external sources where backup is unavailable or state is intentionally ephemeral.
- [ ] **MC-53.T08** — Reconcile active leases with execution plane before restored scheduler admits new work.
- [ ] **MC-53.T09** — Prevent stale restored fencing epochs/tokens from regaining authority.
- [ ] **MC-53.T10** — Schedule automated restore drills rather than backup-only checks.
- [ ] **MC-53.T11** — Record recovery duration and restore evidence.
- [ ] **MC-53.T12** — Define secure retention/deletion and legal/incident hold exceptions.

#### Component-specific acceptance gates

- [ ] **MC-53.V01** — Restore drills meet RPO/RTO and preserve fencing/lease/quota invariants.
- [ ] **MC-53.V02** — Restored scheduler reconciles execution state before issuing conflicting placements.
- [ ] **MC-53.V03** — Backup corruption/missing backup follows tested reconstruction or incident procedures.

#### Required deliverables / evidence

- [ ] **MC-53.E01** — Produce, version, and reference in release evidence: `backup/reconstruction design`.
- [ ] **MC-53.E02** — Produce, version, and reference in release evidence: `backup/restore automation`.
- [ ] **MC-53.E03** — Produce, version, and reference in release evidence: `restore reconciliation`.
- [ ] **MC-53.E04** — Produce, version, and reference in release evidence: `restore drill reports`.

#### Definition of done

- [ ] **MC-53.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-53.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-53.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-53.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-53.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-53.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-53.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-54 — Production-grade runbook set

**Audit finding:** `OPERATIONS.md` adds day-0/day-1/day-2 guidance, but it does not include environment-specific commands, ownership, rollback verification, dependency recovery, or tested operational drills.

**Original control coverage:** C096

#### Engineering implementation checklist

- [ ] **MC-54.T01** — Create day-0 runbook for prerequisites, identity bootstrap, state store, schemas, policy/config, runtime registry, adjacent dependencies, and initial verification.
- [ ] **MC-54.T02** — Create day-1 deployment runbook with exact commands/automation, config locations, health checks, smoke tests, canary stages, and rollback checkpoints.
- [ ] **MC-54.T03** — Create day-2 operations runbook for monitoring, capacity, dependency health, credential rotation, config/policy updates, upgrades, and cleanup.
- [ ] **MC-54.T04** — Provide environment/platform-specific commands for all supported operating environments.
- [ ] **MC-54.T05** — Include pre-change backup/evidence checks and post-change verification.
- [ ] **MC-54.T06** — Troubleshoot no-candidate spikes, stale reports, quota/fairness, topology mismatch, attestation failure, state conflict, and execution rejection.
- [ ] **MC-54.T07** — Include rollback verification for state/schema compatibility and restored health.
- [ ] **MC-54.T08** — Include dependency recovery/reconnect and quarantine/freeze controls.
- [ ] **MC-54.T09** — Link alerts directly to relevant runbook sections.
- [ ] **MC-54.T10** — State required permissions and warnings for destructive/admin commands.
- [ ] **MC-54.T11** — Exercise runbooks in staging/tabletop drills and correct inaccurate steps.
- [ ] **MC-54.T12** — Version runbooks with supported releases and retain prior versions.

#### Component-specific acceptance gates

- [ ] **MC-54.V01** — An operator unfamiliar with internals can bootstrap, deploy, diagnose common failures, roll back, and restore service using runbooks.
- [ ] **MC-54.V02** — Staging drills validate commands/expected outputs on supported environments.
- [ ] **MC-54.V03** — Runbooks identify owners, prerequisites, rollback points, and success criteria.

#### Required deliverables / evidence

- [ ] **MC-54.E01** — Produce, version, and reference in release evidence: `runbooks/day0.md`.
- [ ] **MC-54.E02** — Produce, version, and reference in release evidence: `runbooks/day1.md`.
- [ ] **MC-54.E03** — Produce, version, and reference in release evidence: `runbooks/day2.md`.
- [ ] **MC-54.E04** — Produce, version, and reference in release evidence: `operational drill records`.

#### Definition of done

- [ ] **MC-54.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-54.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-54.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-54.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-54.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-54.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-54.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-55 — Incident response procedure

**Audit finding:** No severity model, paging tree, containment steps, communications path, evidence preservation, or recovery checklist exists.

**Original control coverage:** C097

#### Engineering implementation checklist

- [ ] **MC-55.T01** — Define objective incident severity triggers for safety violations, outage, security compromise, residency/data breach, state corruption, and performance degradation.
- [ ] **MC-55.T02** — Define paging tree and roles: incident commander, operations, security, communications, scribe, and external-plane liaison as needed.
- [ ] **MC-55.T03** — Define first response: freeze unsafe changes, capture evidence, assess blast radius, preserve logs/audit/state, and establish communications.
- [ ] **MC-55.T04** — Define containment for compromised identity/key, malicious workload, bad policy/config, faulty release, split brain, and failed dependency.
- [ ] **MC-55.T05** — Define when to invoke quarantine, emergency disable, rollback, credential revocation, or site isolation.
- [ ] **MC-55.T06** — Define communication cadence/approval without exposing tenant-sensitive information.
- [ ] **MC-55.T07** — Preserve forensic evidence with chain of custody and audit references.
- [ ] **MC-55.T08** — Define recovery verification before restoration declaration, including state/invariant reconciliation.
- [ ] **MC-55.T09** — Require post-incident review for defined severities with action owners/dates.
- [ ] **MC-55.T10** — Map incidents to SLO/error budget, vulnerability, and waiver processes.
- [ ] **MC-55.T11** — Run tabletop exercises for outage, split brain, credential compromise, and bad policy rollout.
- [ ] **MC-55.T12** — Update procedure based on drills/incidents.

#### Component-specific acceptance gates

- [ ] **MC-55.V01** — Tabletops demonstrate timely escalation, containment, evidence preservation, and recovery decision paths.
- [ ] **MC-55.V02** — High-severity incidents cannot close without reconciliation/invariant verification and follow-up ownership.
- [ ] **MC-55.V03** — Forensic/audit evidence is retained and access-controlled.

#### Required deliverables / evidence

- [ ] **MC-55.E01** — Produce, version, and reference in release evidence: `INCIDENT_RESPONSE.md`.
- [ ] **MC-55.E02** — Produce, version, and reference in release evidence: `severity/paging matrix`.
- [ ] **MC-55.E03** — Produce, version, and reference in release evidence: `forensic evidence checklist`.
- [ ] **MC-55.E04** — Produce, version, and reference in release evidence: `tabletop records`.

#### Definition of done

- [ ] **MC-55.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-55.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-55.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-55.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-55.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-55.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-55.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-56 — Recurring review program

**Audit finding:** No scheduled access, policy, dependency, configuration, threat-model, or architecture review record exists.

**Original control coverage:** C098

#### Engineering implementation checklist

- [ ] **MC-56.T01** — Establish recurring reviews for access/roles, policy, config, dependencies, vulnerabilities, architecture, threat model, telemetry privacy, SLOs, and capacity.
- [ ] **MC-56.T02** — Assign owner/approver for each review.
- [ ] **MC-56.T03** — Define required inputs, evidence, decisions, and follow-up format.
- [ ] **MC-56.T04** — Automate reminders and flag overdue reviews.
- [ ] **MC-56.T05** — Review privileged identities/service accounts, grants, use, and justification.
- [ ] **MC-56.T06** — Review active policy/config against approved baselines and remove expired overrides.
- [ ] **MC-56.T07** — Review dependency support/EOL/vulnerability/compatibility status.
- [ ] **MC-56.T08** — Reassess trust boundaries when adjacent planes, runtimes, or features change.
- [ ] **MC-56.T09** — Review capacity/performance trends against saturation models and thresholds.
- [ ] **MC-56.T10** — Record date, roles, findings, decisions, action owners, and due dates.
- [ ] **MC-56.T11** — Escalate unresolved high-risk findings into waiver/debt register with expiry.
- [ ] **MC-56.T12** — Include review compliance in production-readiness governance.

#### Component-specific acceptance gates

- [ ] **MC-56.V01** — Every required recurring review has a current record and no unowned overdue high-risk findings.
- [ ] **MC-56.V02** — Expired access/overrides/waivers are detected and acted on.
- [ ] **MC-56.V03** — Review outcomes feed backlog, ADRs, waivers, and release governance.

#### Required deliverables / evidence

- [ ] **MC-56.E01** — Produce, version, and reference in release evidence: `review calendar/policy`.
- [ ] **MC-56.E02** — Produce, version, and reference in release evidence: `review templates`.
- [ ] **MC-56.E03** — Produce, version, and reference in release evidence: `review records`.
- [ ] **MC-56.E04** — Produce, version, and reference in release evidence: `overdue/compliance report`.

#### Definition of done

- [ ] **MC-56.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-56.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-56.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-56.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-56.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-56.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-56.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-57 — Exception/waiver/technical-debt register

**Audit finding:** No owner/expiry-based waiver register or deprecated-behavior ledger exists.

**Original control coverage:** C099

#### Engineering implementation checklist

- [ ] **MC-57.T01** — Create machine-readable waiver register with ID, control/requirement, scope, environment, risk, rationale, owner, approver, dates, and compensating controls.
- [ ] **MC-57.T02** — Require finite expiry; prohibit permanent unreviewed exceptions.
- [ ] **MC-57.T03** — Define approval authority by risk/domain.
- [ ] **MC-57.T04** — Link waivers to code/config/policy/release versions and evidence gaps.
- [ ] **MC-57.T05** — Distinguish risk acceptance, temporary implementation gap, deprecated behavior, and emergency override.
- [ ] **MC-57.T06** — Alert before expiry and block release on expired waivers.
- [ ] **MC-57.T07** — Require reapproval when scope expands or material release changes affect the exception.
- [ ] **MC-57.T08** — Track remediation milestones and closure evidence.
- [ ] **MC-57.T09** — Make exit gate show waived controls distinctly from pass.
- [ ] **MC-57.T10** — Audit create/update/approve/expire/close operations.
- [ ] **MC-57.T11** — Publish a safe operator summary while protecting sensitive details.
- [ ] **MC-57.T12** — Review waivers during recurring governance and incident/postmortem processes.

#### Component-specific acceptance gates

- [ ] **MC-57.V01** — No mandatory control is silently bypassed; every accepted gap has scoped approved unexpired waiver and compensating control.
- [ ] **MC-57.V02** — Expired or scope-mismatched waivers fail release gate.
- [ ] **MC-57.V03** — Closed waivers retain historical evidence and remediation proof.

#### Required deliverables / evidence

- [ ] **MC-57.E01** — Produce, version, and reference in release evidence: `waivers.yaml/json`.
- [ ] **MC-57.E02** — Produce, version, and reference in release evidence: `waiver validator`.
- [ ] **MC-57.E03** — Produce, version, and reference in release evidence: `expiry alerts`.
- [ ] **MC-57.E04** — Produce, version, and reference in release evidence: `waiver audit trail`.

#### Definition of done

- [ ] **MC-57.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-57.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-57.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-57.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-57.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-57.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-57.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-58 — Formal production exit gate implementation

**Audit finding:** README names `pk_core gate`, but the required framework/evidence are not bundled and no local executable gate proves all architecture/security/resilience/performance/operations prerequisites.

**Original control coverage:** C100

#### Engineering implementation checklist

- [ ] **MC-58.T01** — Implement a local executable production-exit gate aggregating architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.
- [ ] **MC-58.T02** — Define mandatory gate-input schemas including the signed release-evidence bundle.
- [ ] **MC-58.T03** — Treat skip/not-run/unknown distinctly from pass and fail mandatory controls unless explicitly waived.
- [ ] **MC-58.T04** — Validate all 100 controls and SHALL requirements through RTM/evidence.
- [ ] **MC-58.T05** — Require reproducible package, SBOM/provenance, vulnerability status, compatibility, performance, security, fault, and operations evidence.
- [ ] **MC-58.T06** — Require external prerequisite evidence for pk_core and adjacent planes used by deployment profile.
- [ ] **MC-58.T07** — Validate owner/on-call, runbooks, incident process, rollout/rollback, backup/recovery, and support commitments.
- [ ] **MC-58.T08** — Reject expired waivers, unsupported dependencies, or stale security/performance evidence.
- [ ] **MC-58.T09** — Emit machine-readable GO/NO-GO with per-control reason codes and immutable evidence refs.
- [ ] **MC-58.T10** — Sign gate results with release identity and include in release certificate.
- [ ] **MC-58.T11** — Meta-test gate failure when each mandatory evidence class is removed, corrupted, stale, or failed.
- [ ] **MC-58.T12** — Make publication/deployment automation require a valid signed GO for the exact artifact digest.

#### Component-specific acceptance gates

- [ ] **MC-58.V01** — Removing/failing mandatory evidence deterministically returns NO-GO unless a valid scoped waiver applies.
- [ ] **MC-58.V02** — Gate result reproduces offline from release evidence.
- [ ] **MC-58.V03** — No production artifact can publish/deploy without signed GO for its exact digest.

#### Required deliverables / evidence

- [ ] **MC-58.E01** — Produce, version, and reference in release evidence: `production gate executable`.
- [ ] **MC-58.E02** — Produce, version, and reference in release evidence: `gate policy/schema`.
- [ ] **MC-58.E03** — Produce, version, and reference in release evidence: `gate meta-tests`.
- [ ] **MC-58.E04** — Produce, version, and reference in release evidence: `signed GO/NO-GO result`.

#### Definition of done

- [ ] **MC-58.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-58.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-58.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-58.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-58.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-58.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-58.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-59 — CI workflow

**Audit finding:** No repository CI configuration runs compile, unit, security, compatibility, benchmark, or release gates on change.

**Original control coverage:** C070, C084-C090, C100

#### Engineering implementation checklist

- [ ] **MC-59.T01** — Add CI for pull requests, protected branches, tags/releases, and scheduled deep-test jobs.
- [ ] **MC-59.T02** — Run compile/syntax and unit tests on every change while reporting optional pk_core absence separately from local success.
- [ ] **MC-59.T03** — Run pinned format/lint/type/static analysis appropriate to the codebase.
- [ ] **MC-59.T04** — Run schema/contract, property/fuzz smoke, secret, dependency/vulnerability, and license checks.
- [ ] **MC-59.T05** — Build package and clean-install smoke-test supported Python versions.
- [ ] **MC-59.T06** — Run compatibility matrix jobs on required platforms/runtimes/providers or approved equivalents.
- [ ] **MC-59.T07** — Run distributed-race, fault, and security suites on protected/scheduled/release paths.
- [ ] **MC-59.T08** — Run reproducible benchmarks/performance regression gates on controlled runners.
- [ ] **MC-59.T09** — Retain evidence artifacts with commit/environment/tool metadata.
- [ ] **MC-59.T10** — Protect release/tag jobs with least-privilege credentials and approval; never expose signing keys to untrusted PR code.
- [ ] **MC-59.T11** — Generate SBOM, checksums, provenance, signed evidence, and exit-gate output in release workflow.
- [ ] **MC-59.T12** — Use branch protection so required gates cannot be bypassed except via audited break-glass.
- [ ] **MC-59.T13** — Detect silently skipped mandatory jobs through CI policy/self-tests.

#### Component-specific acceptance gates

- [ ] **MC-59.V01** — Pull requests automatically run required fast gates and protected release jobs run full certification.
- [ ] **MC-59.V02** — Failed/skipped mandatory jobs block merge/release.
- [ ] **MC-59.V03** — Release credentials/signing authority are isolated from untrusted contribution contexts.

#### Required deliverables / evidence

- [ ] **MC-59.E01** — Produce, version, and reference in release evidence: `CI workflow definitions`.
- [ ] **MC-59.E02** — Produce, version, and reference in release evidence: `pinned CI tooling config`.
- [ ] **MC-59.E03** — Produce, version, and reference in release evidence: `branch/release protection policy`.
- [ ] **MC-59.E04** — Produce, version, and reference in release evidence: `CI evidence retention`.

#### Definition of done

- [ ] **MC-59.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-59.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-59.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-59.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-59.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-59.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-59.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### MC-60 — License/SBOM/release provenance artifacts

**Audit finding:** The archive contains no license file, SBOM, dependency inventory, build provenance statement, or release checksums. License terms cannot be inferred.

**Original control coverage:** Supply-chain support for C041, C045, C090, C094

#### Engineering implementation checklist

- [ ] **MC-60.T01** — Select/add the authoritative software license only after confirming ownership and intended distribution terms; do not infer licensing.
- [ ] **MC-60.T02** — Add required copyright, NOTICE, and third-party attribution files.
- [ ] **MC-60.T03** — Inventory direct/transitive runtime/build/test dependencies with version, source, license, and checksum.
- [ ] **MC-60.T04** — Generate per-release SPDX and/or CycloneDX SBOM.
- [ ] **MC-60.T05** — Scan dependency licenses and review unresolved/unknown/restricted terms.
- [ ] **MC-60.T06** — Generate checksum manifest for source archive, packages, schemas, SBOM, evidence, and release artifacts.
- [ ] **MC-60.T07** — Produce build provenance attestation linking source commit, builder, recipe, dependencies, environment, and outputs; align with an established framework such as SLSA where appropriate.
- [ ] **MC-60.T08** — Sign release manifests/artifacts/attestations with managed release keys and publish verification instructions.
- [ ] **MC-60.T09** — Verify downloaded build dependencies/tools against approved provenance/signatures/hashes where feasible.
- [ ] **MC-60.T10** — Retain SBOM/provenance immutably for supported release lifetime.
- [ ] **MC-60.T11** — CI-gate missing license, SBOM drift, checksum mismatch, unsigned provenance, or prohibited license.
- [ ] **MC-60.T12** — Document offline/restricted-environment release verification.

#### Component-specific acceptance gates

- [ ] **MC-60.V01** — Every distributed artifact has authoritative license status, SBOM, checksums, and provenance.
- [ ] **MC-60.V02** — Offline verification binds artifact to exact source/build and detects tampering.
- [ ] **MC-60.V03** — Release CI blocks unknown/prohibited license or provenance gaps according to policy.

#### Required deliverables / evidence

- [ ] **MC-60.E01** — Produce, version, and reference in release evidence: `LICENSE`.
- [ ] **MC-60.E02** — Produce, version, and reference in release evidence: `NOTICE/third-party notices`.
- [ ] **MC-60.E03** — Produce, version, and reference in release evidence: `SPDX/CycloneDX SBOM`.
- [ ] **MC-60.E04** — Produce, version, and reference in release evidence: `checksum manifest`.
- [ ] **MC-60.E05** — Produce, version, and reference in release evidence: `signed build provenance`.

#### Definition of done

- [ ] **MC-60.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **MC-60.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **MC-60.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **MC-60.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **MC-60.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **MC-60.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **MC-60.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## External prerequisite integration and certification checklists

These items are not automatically defects in SCH-01 because primary implementation belongs to adjacent elements. They remain certification dependencies whenever the production deployment profile relies on them.

### EXT-01 — pk_core assessment/evidence/gate framework

**Required architectural role:** 100-check assessment, evidence ledger, gate and verification framework.

#### Integration checklist

- [ ] **EXT-01.T01** — Pin an approved pk_core version/commit and record its compatibility range with SCH-01.
- [ ] **EXT-01.T02** — Provide reproducible online/offline installation and import paths.
- [ ] **EXT-01.T03** — Document exact pk_core APIs/classes used by the SCH-01 conformance adapter while keeping core scheduling independently testable.
- [ ] **EXT-01.T04** — Run previously skipped pk_core integration tests in certification CI and fail clearly when required dependency is unavailable.
- [ ] **EXT-01.T05** — Map SCH-01 C001-C100 to pk_core evidence/gate semantics and reconcile ID/schema differences.
- [ ] **EXT-01.T06** — Record pk_core version/digest in release evidence.
- [ ] **EXT-01.T07** — Test incompatible, missing, and partial pk_core installations with stable dependency errors.
- [ ] **EXT-01.T08** — Validate evidence-ledger integrity, immutability, and retention expectations.
- [ ] **EXT-01.T09** — Run pk_core gate against the exact release artifact and preserve raw machine-readable output.
- [ ] **EXT-01.T10** — Verify pk_core does not convert local failures/skips into passes and that waivers remain explicit.
- [ ] **EXT-01.T11** — Compatibility-test future pk_core upgrades before changing the pin.
- [ ] **EXT-01.T12** — Define separate owner/escalation for pk_core defects.

#### Integration acceptance gates

- [ ] **EXT-01.V01** — Full pk_core integration/conformance suite runs without skips in production certification.
- [ ] **EXT-01.V02** — Exact pk_core version/digest and gate result are present in signed release evidence.
- [ ] **EXT-01.V03** — Unavailable/incompatible pk_core cannot be mistaken for certification success.

#### Integration definition of done

- [ ] **EXT-01.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-01.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-01.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-01.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-01.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-01.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-01.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-02 — PLN-02 Application plane integration

**Required architectural role:** Resolved application revision/components.

#### Integration checklist

- [ ] **EXT-02.T01** — Define a versioned application-resolution contract with application ID, immutable release/revision digest, components, workload identities, tenant, provenance, resource/security/latency requirements, and data references.
- [ ] **EXT-02.T02** — Authenticate/authorize PLN-02 producer and bind tenant/application identity to payload.
- [ ] **EXT-02.T03** — Reject mutable or ambiguous application revision references.
- [ ] **EXT-02.T04** — Define one-to-many component/workload expansion plus dependency/affinity semantics.
- [ ] **EXT-02.T05** — Use stable idempotency/correlation IDs across application resolution and placement.
- [ ] **EXT-02.T06** — Define behavior for incomplete, stale, withdrawn, or superseded revisions.
- [ ] **EXT-02.T07** — Create positive/negative fixtures across supported versions.
- [ ] **EXT-02.T08** — Test rolling-version compatibility between PLN-02 and SCH-01.
- [ ] **EXT-02.T09** — Trace placement to exact application release lineage.
- [ ] **EXT-02.T10** — Propagate cancellation/rollback when a release is withdrawn during placement.
- [ ] **EXT-02.T11** — Include peer version and integration evidence in SCH-01 release bundle.

#### Integration acceptance gates

- [ ] **EXT-02.V01** — Every placement traces to an immutable authenticated application revision.
- [ ] **EXT-02.V02** — Stale/incompatible/withdrawn input cannot create untracked placement.
- [ ] **EXT-02.V03** — End-to-end tests cover multi-component resolution and cancellation.

#### Integration definition of done

- [ ] **EXT-02.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-02.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-02.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-02.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-02.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-02.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-02.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-03 — PLN-05 Elasticity plane integration

**Required architectural role:** Desired instance count.

#### Integration checklist

- [ ] **EXT-03.T01** — Define versioned scale intent with application/workload identity, desired/min/max count, priority, reason, generation, and timestamp.
- [ ] **EXT-03.T02** — Authenticate/authorize scale-intent producers and bind intents to tenant/application.
- [ ] **EXT-03.T03** — Use monotonic generation/CAS so stale intents cannot override newer desired state.
- [ ] **EXT-03.T04** — Define scale-up/down semantics and which existing leases can be terminated.
- [ ] **EXT-03.T05** — Integrate desired count with quotas/fair-share and site/runtime/accelerator capacity.
- [ ] **EXT-03.T06** — Make placement creation idempotent under duplicate scale messages.
- [ ] **EXT-03.T07** — Define partial/degraded behavior when desired count exceeds quota/capacity.
- [ ] **EXT-03.T08** — Test concurrent scale changes while placements are in flight.
- [ ] **EXT-03.T09** — Test reconnect/replay after either plane restarts.
- [ ] **EXT-03.T10** — Correlate scale generations with created/released lease IDs.
- [ ] **EXT-03.T11** — Emit scale backlog/refusal/success metrics and certification evidence.

#### Integration acceptance gates

- [ ] **EXT-03.V01** — Stale/duplicate scale intents cannot over-place or cause unintended scale-down.
- [ ] **EXT-03.V02** — Desired state converges after restart/reconnect within documented bounds.
- [ ] **EXT-03.V03** — Quota/fair-share limits hold during burst scale-up.

#### Integration definition of done

- [ ] **EXT-03.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-03.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-03.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-03.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-03.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-03.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-03.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-04 — GAP-02 Hardware capability discovery integration

**Required architectural role:** Authoritative node capability/attestation reports.

#### Integration checklist

- [ ] **EXT-04.T01** — Define authoritative versioned node/accelerator capability report schema.
- [ ] **EXT-04.T02** — Authenticate reporter/provider and attest report integrity/node identity.
- [ ] **EXT-04.T03** — Include monotonic sequence, issue/freshness time, site, tiers/runtimes, resources, capabilities, devices/partitions, health, firmware/driver, and topology references.
- [ ] **EXT-04.T04** — Canonicalize capability names/versions and reject ungoverned self-asserted feature strings.
- [ ] **EXT-04.T05** — Define atomic full/incremental report update semantics.
- [ ] **EXT-04.T06** — Reject replayed, future, stale, revoked, mismatched, or partially signed reports.
- [ ] **EXT-04.T07** — Define node disappearance/retirement and capability withdrawal.
- [ ] **EXT-04.T08** — Reference thermal/power/attestation data without conflating source ownership.
- [ ] **EXT-04.T09** — Run large-fleet update and stale-report tests.
- [ ] **EXT-04.T10** — Test compromised reporter and revoked node scenarios.
- [ ] **EXT-04.T11** — Record report revision/attestation references in placement evidence.

#### Integration acceptance gates

- [ ] **EXT-04.V01** — SCH-01 consumes only authenticated, fresh, schema-valid reports tied to correct node identity.
- [ ] **EXT-04.V02** — Replay/forgery/staleness tests fail closed.
- [ ] **EXT-04.V03** — Capability withdrawal blocks new placement within documented propagation bound.

#### Integration definition of done

- [ ] **EXT-04.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-04.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-04.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-04.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-04.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-04.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-04.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-05 — PLN-04 Execution plane integration

**Required architectural role:** Enforce selected isolation tier and admit workload.

#### Integration checklist

- [ ] **EXT-05.T01** — Define versioned placement-admission request with workload/tenant, node, runtime ID/version/digest, isolation tier, resources/devices, data path, fencing token, policy/config revisions, and attestation prerequisites.
- [ ] **EXT-05.T02** — Mutually authenticate/authorize SCH-01 and PLN-04 roles.
- [ ] **EXT-05.T03** — Require PLN-04 to validate fencing, runtime compatibility, capacity/device assignment, isolation tier, and attestation before admission.
- [ ] **EXT-05.T04** — Return schema-valid admit/reject/timeout with stable error code and actual sandbox/runtime identity.
- [ ] **EXT-05.T05** — Make admission idempotent on lease/request ID and reject stale tokens.
- [ ] **EXT-05.T06** — Persist acknowledgement for timeout/crash reconciliation.
- [ ] **EXT-05.T07** — Define cancellation, release, drain, and cleanup confirmation.
- [ ] **EXT-05.T08** — Test downstream rejection after scheduler reservation and reconcile quota/state/device reservations.
- [ ] **EXT-05.T09** — Test real isolation enforcement for every supported execution tier.
- [ ] **EXT-05.T10** — Test mixed-version rolling upgrade and emergency runtime disable.
- [ ] **EXT-05.T11** — Trace placement through actual launched runtime/node/device and release lifecycle.

#### Integration acceptance gates

- [ ] **EXT-05.V01** — End-to-end tests prove PLN-04 enforces exactly the runtime/tier/resources selected by SCH-01.
- [ ] **EXT-05.V02** — Stale/duplicate admission cannot launch duplicate execution.
- [ ] **EXT-05.V03** — Rejected/timed-out admission safely reconciles all reservations.

#### Integration definition of done

- [ ] **EXT-05.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-05.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-05.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-05.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-05.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-05.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-05.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-06 — GAP-03 Topology-aware scheduler/fair-share integration

**Required architectural role:** Topology/locality and fair-share guard.

#### Integration checklist

- [ ] **EXT-06.T01** — Define ownership split between GAP-03 inputs/decisions and SCH-01 placement authority.
- [ ] **EXT-06.T02** — Version topology/fair-share contract with graph/policy revision, timestamp/freshness, and deterministic cost/constraints.
- [ ] **EXT-06.T03** — Authenticate provider and validate graph integrity, stable IDs, and fairness policy scope.
- [ ] **EXT-06.T04** — Provide atomic snapshot semantics so a decision cannot mix graph revisions.
- [ ] **EXT-06.T05** — Define hard/soft topology constraints and precedence with residency/security.
- [ ] **EXT-06.T06** — Define fair-share reservation/commit semantics that prevent duplicate entitlement consumption.
- [ ] **EXT-06.T07** — Handle unavailable/stale/degraded provider explicitly.
- [ ] **EXT-06.T08** — Test explain consistency against GAP-03 cost/fairness inputs.
- [ ] **EXT-06.T09** — Run multi-site/failure-domain/NUMA and skewed-tenant scenarios.
- [ ] **EXT-06.T10** — Test graph update/partition and fairness-state restart/reconciliation.
- [ ] **EXT-06.T11** — Include peer revision/integration evidence in certification.

#### Integration acceptance gates

- [ ] **EXT-06.V01** — Topology/fair-share constraints are enforced consistently and atomically.
- [ ] **EXT-06.V02** — Stale/conflicting provider state cannot silently violate hard constraints or fairness.
- [ ] **EXT-06.V03** — Explanations identify the exact GAP-03 revision used.

#### Integration definition of done

- [ ] **EXT-06.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-06.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-06.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-06.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-06.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-06.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-06.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-07 — GAP-10 Power/thermal-aware scheduling integration

**Required architectural role:** Optional thermal exclusion input.

#### Integration checklist

- [ ] **EXT-07.T01** — Define power/thermal signal schema with node/device identity, sensor source, values/state, timestamp, quality, threshold policy revision, and exclusion recommendation.
- [ ] **EXT-07.T02** — Authenticate/attest signal producer and bind readings to node/device.
- [ ] **EXT-07.T03** — Define freshness/quality requirements and reject invalid/out-of-range/stale telemetry.
- [ ] **EXT-07.T04** — Use hysteresis/minimum hold time to prevent oscillation near thresholds.
- [ ] **EXT-07.T05** — Distinguish hard thermal exclusion from soft energy-efficiency scoring.
- [ ] **EXT-07.T06** — Define safe behavior when GAP-10/sensors are unavailable.
- [ ] **EXT-07.T07** — Propagate exclusion atomically with node snapshot where possible.
- [ ] **EXT-07.T08** — Test overheating, cooling, sensor failure, contradictory sensors, and stale telemetry.
- [ ] **EXT-07.T09** — Ensure thermal scoring cannot override security/residency/isolation.
- [ ] **EXT-07.T10** — Expose aggregate thermal exclusion telemetry/reason codes.
- [ ] **EXT-07.T11** — Record GAP-10 revision in evidence when it affects eligibility.

#### Integration acceptance gates

- [ ] **EXT-07.V01** — Hard exclusions prevent new placement within propagation bound.
- [ ] **EXT-07.V02** — Hysteresis avoids oscillation while recovering capacity after sustained safe state.
- [ ] **EXT-07.V03** — Unavailable/stale sensor behavior follows documented safety policy.

#### Integration definition of done

- [ ] **EXT-07.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-07.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-07.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-07.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-07.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-07.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-07.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

### EXT-08 — INV-33 Virtualization controller integration

**Required architectural role:** Execution-side lease lifecycle and reclamation.

#### Integration checklist

- [ ] **EXT-08.T01** — Define versioned lease operations for reserve, admit, renew, drain, release, revoke, expire, and reclaim.
- [ ] **EXT-08.T02** — Bind leases to workload, tenant, node, runtime/sandbox, resources/devices, fencing epoch/token, times, and controller identity.
- [ ] **EXT-08.T03** — Authenticate/authorize both sides and require stale-token rejection.
- [ ] **EXT-08.T04** — Make reserve/release/renew idempotent with durable acknowledgements.
- [ ] **EXT-08.T05** — Define renewal interval, grace, expiry, and temporary disconnection behavior.
- [ ] **EXT-08.T06** — Define orphan detection/reclamation after scheduler/controller restart or node loss.
- [ ] **EXT-08.T07** — Reconcile controller-observed sandboxes with SCH-01 durable occupancy.
- [ ] **EXT-08.T08** — Do not reissue reclaimed resources until stale execution is fenced/terminated.
- [ ] **EXT-08.T09** — Test delayed/duplicate renewal, lost release, controller/scheduler failover, partition, and ABA.
- [ ] **EXT-08.T10** — Emit lease lifecycle metrics/audit and link to placement IDs.
- [ ] **EXT-08.T11** — Include INV-33 version/compatibility evidence in certification.

#### Integration acceptance gates

- [ ] **EXT-08.V01** — Lease tests prove at-most-one valid owner and safe reclamation across crash/partition/restart.
- [ ] **EXT-08.V02** — Expired/revoked resources cannot be reused while stale execution remains authoritative.
- [ ] **EXT-08.V03** — SCH-01 and INV-33 converge to the same lease state after recovery.

#### Integration definition of done

- [ ] **EXT-08.D01** — Assign accountable implementation owner and approver before marking complete.
- [ ] **EXT-08.D02** — Version all code/schema/config artifacts and preserve deterministic behavior for an immutable input snapshot.
- [ ] **EXT-08.D03** — Commit positive, negative, boundary, failure, and concurrency tests appropriate to the component.
- [ ] **EXT-08.D04** — Fail security-critical paths closed and emit stable machine-readable errors plus safe diagnostics/audit evidence.
- [ ] **EXT-08.D05** — Document operational telemetry, runbook, upgrade, rollback, and compatibility impact where production behavior changes.
- [ ] **EXT-08.D06** — Update the RTM with immutable evidence references for implementation, tests, and acceptance results.
- [ ] **EXT-08.D07** — Do not count skipped/not-run/unknown verification as pass; represent exceptions only through approved unexpired waivers.

## Final production-closure checklist

- [ ] **FINAL-01** — All MC-01 through MC-60 acceptance gates are complete or explicitly covered by scoped, approved, unexpired waivers.
- [ ] **FINAL-02** — Every external prerequisite used by the deployment profile has a versioned contract and end-to-end integration evidence.
- [ ] **FINAL-03** — The RTM has no orphan requirements/controls, missing owners, stale evidence, broken references, or expired waivers.
- [ ] **FINAL-04** — All mandatory CI, contract, integration, compatibility, security, fuzz, race, fault, benchmark, soak, and disaster tests are executed; skipped mandatory tests produce NO-GO.
- [ ] **FINAL-05** — The signed release-evidence bundle contains source/build digests, SBOM, provenance, checksums, test results, benchmark results, vulnerability state, compatibility matrix, waivers, and external evidence.
- [ ] **FINAL-06** — The production exit gate returns signed GO for the exact artifact digest to be deployed.
- [ ] **FINAL-07** — Canary/staged rollout and rollback have been exercised against supported state/schema/runtime combinations.
- [ ] **FINAL-08** — Day-0/day-1/day-2 runbooks, incident procedures, owner/on-call records, recovery drills, and support commitments are current.
- [ ] **FINAL-09** — Identity, authorization, attestation, policy, keys, audit, and distributed fencing/state have tested fail-closed behavior.
- [ ] **FINAL-10** — Production observability distinguishes normal load, policy rejection, capacity exhaustion, dependency degradation, security attack indicators, state/fencing anomalies, and software defects.

## Appendix A — Original SCH-01 100-control reference

This appendix preserves the control text used by the hardened repository so the remediation backlog can be cross-referenced without opening `CHECKLIST.json`.

- **SCH-01-C001 — Architecture & Scope:** Define the exact production responsibility of Workload Classification and Runtime Placement Engine.
- **SCH-01-C002 — Architecture & Scope:** Document what Workload Classification and Runtime Placement Engine owns and explicitly does not own.
- **SCH-01-C003 — Architecture & Scope:** Identify upstream, downstream, and peer dependencies of Workload Classification and Runtime Placement Engine.
- **SCH-01-C004 — Architecture & Scope:** Define the authoritative source of truth used by Workload Classification and Runtime Placement Engine.
- **SCH-01-C005 — Architecture & Scope:** Document assumptions Workload Classification and Runtime Placement Engine makes about nodes, runtimes, networks, storage, and control planes.
- **SCH-01-C006 — Architecture & Scope:** Define tenant, environment, site, and workload boundaries relevant to Workload Classification and Runtime Placement Engine.
- **SCH-01-C007 — Architecture & Scope:** Separate mandatory Workload Classification and Runtime Placement Engine capabilities from optional optimizations.
- **SCH-01-C008 — Architecture & Scope:** Document unsupported deployment patterns and non-goals for Workload Classification and Runtime Placement Engine.
- **SCH-01-C009 — Architecture & Scope:** Assign an accountable owner and escalation path for Workload Classification and Runtime Placement Engine.
- **SCH-01-C010 — Architecture & Scope:** Approve an architecture decision record for Workload Classification and Runtime Placement Engine, its technologies (Workload classifier, runtime selector, placement engine, policy inputs, topology/data/accelerator awareness), and its function (Classify each workload and select execution target, node, isolation tier, accelerator, data path, and placement based on workload characteristics and policy.).
- **SCH-01-C011 — Requirements & Semantics:** Translate the source function of Workload Classification and Runtime Placement Engine — Classify each workload and select execution target, node, isolation tier, accelerator, data path, and placement based on workload characteristics and policy. — into testable SHALL-level requirements.
- **SCH-01-C012 — Requirements & Semantics:** Define functional requirements for Workload Classification and Runtime Placement Engine across cloud, datacenter, near-edge, and far-edge contexts where applicable.
- **SCH-01-C013 — Requirements & Semantics:** Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.
- **SCH-01-C014 — Requirements & Semantics:** Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Workload Classification and Runtime Placement Engine.
- **SCH-01-C015 — Requirements & Semantics:** Define lifecycle states and legal state transitions managed or exposed by Workload Classification and Runtime Placement Engine.
- **SCH-01-C016 — Requirements & Semantics:** Define versioning and backward-compatibility requirements for Workload Classification and Runtime Placement Engine.
- **SCH-01-C017 — Requirements & Semantics:** Define capacity ceilings, quotas, and fairness semantics relevant to Workload Classification and Runtime Placement Engine.
- **SCH-01-C018 — Requirements & Semantics:** Define behavior when network connectivity is intermittent or absent.
- **SCH-01-C019 — Requirements & Semantics:** Define precedence rules when Workload Classification and Runtime Placement Engine requirements conflict with security, residency, SLO, or cost constraints.
- **SCH-01-C020 — Requirements & Semantics:** Maintain a requirements traceability matrix from each Workload Classification and Runtime Placement Engine requirement to implementation and verification evidence.
- **SCH-01-C021 — Interfaces & Integration:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Workload Classification and Runtime Placement Engine.
- **SCH-01-C022 — Interfaces & Integration:** Use versioned typed schemas for all externally visible Workload Classification and Runtime Placement Engine contracts.
- **SCH-01-C023 — Interfaces & Integration:** Define authentication requirements at each Workload Classification and Runtime Placement Engine boundary.
- **SCH-01-C024 — Interfaces & Integration:** Define authorization and explicit capability requirements at each Workload Classification and Runtime Placement Engine boundary.
- **SCH-01-C025 — Interfaces & Integration:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Workload Classification and Runtime Placement Engine.
- **SCH-01-C026 — Interfaces & Integration:** Define structured failure codes and machine-readable error details for Workload Classification and Runtime Placement Engine.
- **SCH-01-C027 — Interfaces & Integration:** Define compatibility behavior when peers use different supported versions.
- **SCH-01-C028 — Interfaces & Integration:** Document payload, concurrency, queue, connection, or resource limits at Workload Classification and Runtime Placement Engine interfaces.
- **SCH-01-C029 — Interfaces & Integration:** Provide reference examples and conformance fixtures for Workload Classification and Runtime Placement Engine.
- **SCH-01-C030 — Interfaces & Integration:** Create automated integration tests proving Workload Classification and Runtime Placement Engine interoperates with adjacent architectural layers.
- **SCH-01-C031 — Implementation & Configuration:** Select and pin approved implementations, versions, or specifications for Workload Classification and Runtime Placement Engine: Workload classifier, runtime selector, placement engine, policy inputs, topology/data/accelerator awareness.
- **SCH-01-C032 — Implementation & Configuration:** Separate immutable artifacts from mutable configuration and state for Workload Classification and Runtime Placement Engine.
- **SCH-01-C033 — Implementation & Configuration:** Define declarative configuration and secure defaults for Workload Classification and Runtime Placement Engine.
- **SCH-01-C034 — Implementation & Configuration:** Validate configuration before activation and fail closed on security-critical errors.
- **SCH-01-C035 — Implementation & Configuration:** Support site- and environment-specific configuration without rebuilding immutable artifacts.
- **SCH-01-C036 — Implementation & Configuration:** Record configuration provenance, version, author, and activation time.
- **SCH-01-C037 — Implementation & Configuration:** Apply atomic or transactional configuration updates where partial application is unsafe.
- **SCH-01-C038 — Implementation & Configuration:** Define automatic and operator-driven rollback for failed Workload Classification and Runtime Placement Engine changes.
- **SCH-01-C039 — Implementation & Configuration:** Keep credentials and secret material out of ordinary Workload Classification and Runtime Placement Engine configuration and diagnostics.
- **SCH-01-C040 — Implementation & Configuration:** Provide a deterministic bootstrap path from an empty node/environment to healthy Workload Classification and Runtime Placement Engine operation.
- **SCH-01-C041 — Security, Trust & Isolation:** Threat-model Workload Classification and Runtime Placement Engine against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.
- **SCH-01-C042 — Security, Trust & Isolation:** Apply least privilege to every identity and capability used by Workload Classification and Runtime Placement Engine.
- **SCH-01-C043 — Security, Trust & Isolation:** Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Workload Classification and Runtime Placement Engine permits.
- **SCH-01-C044 — Security, Trust & Isolation:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.
- **SCH-01-C045 — Security, Trust & Isolation:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Workload Classification and Runtime Placement Engine.
- **SCH-01-C046 — Security, Trust & Isolation:** Enforce tenant/workload isolation across Workload Classification and Runtime Placement Engine execution, memory, state, network, and device boundaries as applicable.
- **SCH-01-C047 — Security, Trust & Isolation:** Encrypt sensitive Workload Classification and Runtime Placement Engine data in transit and at rest with managed key rotation.
- **SCH-01-C048 — Security, Trust & Isolation:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.
- **SCH-01-C049 — Security, Trust & Isolation:** Emit tamper-evident audit events for security-sensitive Workload Classification and Runtime Placement Engine operations.
- **SCH-01-C050 — Security, Trust & Isolation:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.
- **SCH-01-C051 — Resilience & Failure Handling:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Workload Classification and Runtime Placement Engine.
- **SCH-01-C052 — Resilience & Failure Handling:** Define automated health and stall detection thresholds for Workload Classification and Runtime Placement Engine.
- **SCH-01-C053 — Resilience & Failure Handling:** Implement bounded retry with backoff and jitter only where operations are safe to retry.
- **SCH-01-C054 — Resilience & Failure Handling:** Implement admission control, load shedding, or circuit breaking to prevent Workload Classification and Runtime Placement Engine failure cascades.
- **SCH-01-C055 — Resilience & Failure Handling:** Define failover behavior without violating isolation, residency, or consistency requirements.
- **SCH-01-C056 — Resilience & Failure Handling:** Provide degraded operation when noncritical dependencies are unavailable.
- **SCH-01-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Workload Classification and Runtime Placement Engine state.
- **SCH-01-C058 — Resilience & Failure Handling:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.
- **SCH-01-C059 — Resilience & Failure Handling:** Provide quarantine, freeze, disable, or isolation controls for unsafe Workload Classification and Runtime Placement Engine behavior.
- **SCH-01-C060 — Resilience & Failure Handling:** Run fault-injection tests proving Workload Classification and Runtime Placement Engine recovery against documented objectives.
- **SCH-01-C061 — Performance & Resource Efficiency:** Establish reproducible baselines for Workload Classification and Runtime Placement Engine latency, throughput, startup, CPU, memory, storage, network, and power overhead.
- **SCH-01-C062 — Performance & Resource Efficiency:** Define p50, p95, p99, and worst-case performance thresholds for Workload Classification and Runtime Placement Engine.
- **SCH-01-C063 — Performance & Resource Efficiency:** Measure Workload Classification and Runtime Placement Engine under steady load, burst load, overload, scale-out, scale-in, and recovery.
- **SCH-01-C064 — Performance & Resource Efficiency:** Measure per-workload and per-tenant overhead introduced by Workload Classification and Runtime Placement Engine.
- **SCH-01-C065 — Performance & Resource Efficiency:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Workload Classification and Runtime Placement Engine.
- **SCH-01-C066 — Performance & Resource Efficiency:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.
- **SCH-01-C067 — Performance & Resource Efficiency:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.
- **SCH-01-C068 — Performance & Resource Efficiency:** Measure power and thermal impact on constrained edge nodes where relevant.
- **SCH-01-C069 — Performance & Resource Efficiency:** Define capacity models and saturation signals that predict when Workload Classification and Runtime Placement Engine needs more resources.
- **SCH-01-C070 — Performance & Resource Efficiency:** Block releases that regress approved Workload Classification and Runtime Placement Engine startup, density, throughput, or tail-latency thresholds.
- **SCH-01-C071 — Observability & Explainability:** Expose Workload Classification and Runtime Placement Engine health, readiness, version, configuration, dependency status, and active capability set.
- **SCH-01-C072 — Observability & Explainability:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.
- **SCH-01-C073 — Observability & Explainability:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.
- **SCH-01-C074 — Observability & Explainability:** Propagate trace context across all relevant Workload Classification and Runtime Placement Engine boundaries.
- **SCH-01-C075 — Observability & Explainability:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.
- **SCH-01-C076 — Observability & Explainability:** Record the reason for every automated decision made by Workload Classification and Runtime Placement Engine.
- **SCH-01-C077 — Observability & Explainability:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.
- **SCH-01-C078 — Observability & Explainability:** Correlate Workload Classification and Runtime Placement Engine events with application release lineage and the live infrastructure graph.
- **SCH-01-C079 — Observability & Explainability:** Define telemetry retention, sampling, privacy, and export policy.
- **SCH-01-C080 — Observability & Explainability:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.
- **SCH-01-C081 — Testing & Certification:** Create unit tests for deterministic Workload Classification and Runtime Placement Engine logic and state transitions.
- **SCH-01-C082 — Testing & Certification:** Create contract tests for every public Workload Classification and Runtime Placement Engine interface.
- **SCH-01-C083 — Testing & Certification:** Create integration tests with every supported adjacent layer and execution tier.
- **SCH-01-C084 — Testing & Certification:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Workload Classification and Runtime Placement Engine.
- **SCH-01-C085 — Testing & Certification:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Workload Classification and Runtime Placement Engine.
- **SCH-01-C086 — Testing & Certification:** Create concurrency and race-condition tests for shared/distributed Workload Classification and Runtime Placement Engine state.
- **SCH-01-C087 — Testing & Certification:** Create security tests derived directly from the Workload Classification and Runtime Placement Engine threat model.
- **SCH-01-C088 — Testing & Certification:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Workload Classification and Runtime Placement Engine.
- **SCH-01-C089 — Testing & Certification:** Create disaster, partition, reconnect, and degraded-control-plane tests.
- **SCH-01-C090 — Testing & Certification:** Require machine-readable acceptance evidence before certifying a Workload Classification and Runtime Placement Engine release for production.
- **SCH-01-C091 — Operations, Release & Governance:** Define production SLOs, error budgets, and support commitments for Workload Classification and Runtime Placement Engine.
- **SCH-01-C092 — Operations, Release & Governance:** Define canary, staged rollout, rollback, and emergency-disable procedures for Workload Classification and Runtime Placement Engine.
- **SCH-01-C093 — Operations, Release & Governance:** Maintain a supported-version compatibility matrix for Workload Classification and Runtime Placement Engine and adjacent dependencies.
- **SCH-01-C094 — Operations, Release & Governance:** Define patching, vulnerability response, and end-of-life SLAs for Workload Classification and Runtime Placement Engine.
- **SCH-01-C095 — Operations, Release & Governance:** Provide backup, restore, migration, or reconstruction procedures for Workload Classification and Runtime Placement Engine state where applicable.
- **SCH-01-C096 — Operations, Release & Governance:** Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.
- **SCH-01-C097 — Operations, Release & Governance:** Define incident severity, paging, escalation, containment, and recovery procedures.
- **SCH-01-C098 — Operations, Release & Governance:** Perform recurring access, policy, dependency, configuration, and architecture reviews.
- **SCH-01-C099 — Operations, Release & Governance:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.
- **SCH-01-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

---

**Source basis:** SCH-01 v4.2.0 `MISSING_COMPONENTS.md`, `AUDIT_REPORT.md`, and the 100-control `CHECKLIST.json`. This document defines work required to close gaps; it does not claim any currently missing component has been implemented.
