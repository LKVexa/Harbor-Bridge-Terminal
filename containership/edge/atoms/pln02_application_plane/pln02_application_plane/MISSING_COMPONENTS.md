> **v4.3.0 disposition (2026-09-23).** Every item below was worked under the implementation checklist.
> Current status per item (authoritative source: `TRACEABILITY.json`, verified by `tools/gate.py`):
>
> | MC | Title | v4.3 status | Open acceptance |
> |---|---|---|---|
> | MC-01 | Original master source archive | **BLOCKED_OWNER** | MASTER.md not supplied; recovery unresolved (recorded, nothing reconstructed). |
> | MC-02 | ADR and accountable ownership | **BLOCKED_OWNER** | ADR state is Proposed: approval by quorum not recorded.; Named owners are UNASSIGNED. |
> | MC-03 | Normative requirements specification | **PARTIAL** | Spec awaits approval under ADR-PLN02-001. |
> | MC-04 | Version policy, negotiation, compatibility | **IMPLEMENTED** | — |
> | MC-05 | Capacity, quota, fairness, admission | **PARTIAL** | Quotas are per replica; estate-wide quota coordination needs a shared store. |
> | MC-06 | Disconnected catalogue cache / GAP-04 | **PARTIAL** | GAP-04 exercised through a lease mock only. |
> | MC-07 | Constraint precedence and conflicts | **IMPLEMENTED** | — |
> | MC-08 | Traceability and acceptance record | **IMPLEMENTED** | — |
> | MC-09 | OAM adapter | **IMPLEMENTED** | — |
> | MC-10 | WIT parser and type checker | **PARTIAL** | WIT subset only; no differential conformance against the reference wasm-tools parser (TD-003). |
> | MC-11 | Boundary authentication and trust bootstrap | **PARTIAL** | Caller tokens implemented; node/peer mTLS and attestation belong to the hosting transport (external). |
> | MC-12 | Capability entitlement / authorization | **IMPLEMENTED** | — |
> | MC-13 | Timeout, cancellation, retry, idempotency | **IMPLEMENTED** | — |
> | MC-14 | Wire-level error schema | **IMPLEMENTED** | — |
> | MC-15 | Adjacent-layer integration harness | **PARTIAL** | All six peers are contract-faithful mocks; no live PLN-01/INV-65/PLN-03/SCH-01/INV-11/GAP-04. |
> | MC-16 | Reproducible build and dependency lock | **IMPLEMENTED** | — |
> | MC-17 | Configuration, provenance, activation, rollback | **IMPLEMENTED** | — |
> | MC-18 | Secrets, encryption, key lifecycle | **PARTIAL** | KMS binding and encryption in transit/at rest are deployment-provided (external). |
> | MC-19 | Threat model and adversarial plan | **PARTIAL** | Security review sign-off not recorded. |
> | MC-20 | Ambient authority reduction / isolation | **BLOCKED_EXTERNAL** | Profile written; no deployment attestation that it is applied. |
> | MC-21 | Artifact signature, provenance, supply chain | **PARTIAL** | Default HMAC is symmetric (TD-002); SBOM/attestation generation runs only in unexecuted CI. |
> | MC-22 | Tamper-evident audit ledger | **IMPLEMENTED** | — |
> | MC-23 | Failure catalogue, health, stall detection | **IMPLEMENTED** | — |
> | MC-24 | Failover, split-brain, quarantine/freeze/disable | **PARTIAL** | Fencing is single-process per store root (TD-001); multi-process HA needs an external lease. |
> | MC-25 | Revision store and durable lifecycle | **IMPLEMENTED** | — |
> | MC-26 | Tenant/environment/site context | **IMPLEMENTED** | — |
> | MC-27 | Provider catalogue client | **IMPLEMENTED** | — |
> | MC-28 | Provider selection and explain | **IMPLEMENTED** | — |
> | MC-29 | Performance baseline and regression suite | **PARTIAL** | Single reference host only; constrained-edge power/thermal (C068) not measured. |
> | MC-30 | Runtime observability | **IMPLEMENTED** | — |
> | MC-31 | Telemetry governance, dashboards, alerts | **PARTIAL** | Definitions only; not deployed to a monitoring backend. |
> | MC-32 | Fuzz, property, concurrency, security tests | **IMPLEMENTED** | — |
> | MC-33 | Fault injection, partition, reconnect | **PARTIAL** | In-process fault injection only; no real network/site partition campaign. |
> | MC-34 | Cross-platform / protocol CI matrix | **BLOCKED_EXTERNAL** | Matrix defined (3 OS x 5 Python); only Linux/3.11 executed here. |
> | MC-35 | Benchmark, soak, fleet-scale environment | **BLOCKED_EXTERNAL** | Short single-host soak only; fleet-scale environment not available. |
> | MC-36 | CI/CD production gate and release evidence | **PARTIAL** | Gate is fail-closed and runs locally; pk_core full-estate run and signed attestation are external. |
> | MC-37 | Canary, rollout, rollback, emergency disable | **PARTIAL** | Controls exist and are tested; no production drill executed. |
> | MC-38 | Support, vulnerability, incident, review governance | **BLOCKED_OWNER** | Policy written; no on-call owner, review or exercise evidence. |
> | MC-39 | License, NOTICE, distribution policy | **BLOCKED_OWNER** | Owner chose to leave the licence unresolved; LICENSE records 'owner decision pending'. |

# PLN-02 Application Plane — Post-v4.2.0 Missing Components

This inventory is based on the contents of the **updated** repository, not on
what the contract/checklist merely declares. “Missing” means the supplied
archive contains no complete implementation and/or no executable evidence for
the component. “Partial” means v4.2.0 contains a local primitive but the
production mechanism is still incomplete.

## MC-01 — Original master prompt/workflow source archive

**Status:** Missing.  
**Evidence:** v4.1 README referenced `MASTER.md`; the file was absent from the
source archive.  
**Needed:** the authoritative original master prompt/workflow material, source
revision metadata, and provenance. It should not be reconstructed and labelled
“verbatim” without the source.

## MC-02 — Approved architecture decision record and accountable ownership

**Status:** Missing.  
**Checklist:** C009, C010.  
**Needed:** approved ADR, named accountable owner role, escalation path,
decision rationale, alternatives, consequences, review date, and approval
evidence.

## MC-03 — Normative application-plane requirements specification

**Status:** Missing.  
**Checklist:** C011-C015.  
**Needed:** SHALL-level functional/NFR requirements by deployment context;
explicit success/partial/degraded/retryable/terminal semantics; lifecycle states
and legal transitions. `CHECKLIST.json` asks for these but is not itself the
resulting requirements specification.

## MC-04 — Version policy, negotiation, migration, and compatibility matrix

**Status:** Partial.  
**Checklist:** C016, C027, C093.  
**Present:** exact schema/version rejection and exact interface-version equality.
**Missing:** supported-version windows, downgrade/upgrade rules, negotiation,
migration policy, deprecation timelines, and adjacent dependency compatibility
matrix.

## MC-05 — Capacity, quota, fairness, and dynamic admission policy

**Status:** Partial.  
**Checklist:** C017, C028, C054, C067, C069.  
**Present:** static safety limits for component/edge/interface/capability counts.
**Missing:** per-tenant quotas, fairness, payload byte limits, concurrency/queue
limits, load shedding, circuit breaking, saturation models, and live admission
signals.

## MC-06 — Disconnected-operation catalogue cache and GAP-04 integration

**Status:** Missing from this archive / external dependency.  
**Checklist:** C018, C048, C056, C089.  
**Present:** conformance adapter can use `GAP-04` if installed.  
**Missing:** shipped autonomy controller, signed/cached catalogue snapshots,
lease persistence, reconnect reconciliation, stale-data policy, and partition
tests.

## MC-07 — Constraint precedence and policy-conflict engine

**Status:** Missing.  
**Checklist:** C019, C055.  
**Needed:** deterministic precedence among security, residency, consistency,
SLO, locality, and cost constraints; conflict diagnostics; failover rules that
cannot violate higher-priority constraints.

## MC-08 — Requirement-to-evidence traceability and production acceptance record

**Status:** Missing.  
**Checklist:** C020, C090, C100.  
**Needed:** machine-readable traceability matrix connecting all 100 requirements
to design, code, tests, runtime evidence, owner, status, waiver, and release-gate
result. The external `pk_core` mechanism is referenced but its evidence is not
included here.

## MC-09 — OAM application model parser/adapter

**Status:** Missing.  
**Source function:** “OAM/WIT-based application definitions and portable
components.”  
**Needed:** OAM schema/model support, parsing, validation, translation into the
internal component graph, trait/policy semantics, version handling, and
conformance fixtures. v4.2 accepts its own compact JSON model, not OAM.

## MC-10 — WIT parser and semantic interface type checker

**Status:** Missing.  
**Checklist:** C021, C022, C027, C084, C085.  
**Present:** interface names and opaque version strings are compared exactly.
**Missing:** WIT parsing, world/interface/function/resource type comparison,
subtyping/compatibility rules, package/version resolution, WIT fixtures, and
fuzzing of WIT inputs.

## MC-11 — Boundary authentication and trust bootstrap

**Status:** Missing.  
**Checklist:** C023, C044, C048.  
**Needed:** caller/node/peer/provider/control-plane identity model,
authentication protocols, trust roots, certificate/key lifecycle, failure
behavior when identity/time/attestation systems are unavailable, and tests.

## MC-12 — Capability entitlement and authorization policy enforcement

**Status:** Missing.  
**Checklist:** C024, C042, C046.  
**Present:** resolver checks whether a capability has a provider.  
**Missing:** whether the tenant/component is entitled to request/use that
capability, least-privilege policy evaluation, policy provenance, deny reasons,
and tenant/workload isolation enforcement.

## MC-13 — Timeout, cancellation, retry, idempotency, and backpressure contract

**Status:** Missing.  
**Checklist:** C025, C053.  
**Needed:** boundary-level operation semantics and implementation once resolution
is exposed over RPC/API/event transport, including bounded retry only for safe
operations.

## MC-14 — Wire-level structured error schema

**Status:** Partial.  
**Checklist:** C026.  
**Present:** Python exceptions expose stable codes and detail dictionaries.
**Missing:** a versioned public error document schema, stable error registry,
transport/status mappings, retryability field, correlation identifiers, and
compatibility tests.

## MC-15 — Adjacent-layer integration harness and tests

**Status:** Missing.  
**Checklist:** C030, C083.  
**Dependencies named by the contract:** PLN-01, INV-65, PLN-03, SCH-01, INV-11;
GAP-04 is additionally referenced by resilience logic.  
**Needed:** executable fixtures/mocks or real integration environments and tests
for each supported adjacent layer.

## MC-16 — Reproducible package/build metadata and dependency lock

**Status:** Missing.  
**Checklist:** C031, C032, C040, C093.  
**Needed:** `pyproject.toml` or equivalent build manifest, exact supported Python
range, pinned/locked `pk_core` dependency identity, reproducible build process,
artifact checksums, installation validation, and bootstrap from an empty
environment.

## MC-17 — Declarative configuration, provenance, atomic activation, and rollback

**Status:** Missing.  
**Checklist:** C033-C038.  
**Needed:** configuration schema, secure defaults, environment/site overlays,
pre-activation validation, author/source/version/timestamp provenance,
transactional activation, last-known-good state, and operator/automatic rollback.

## MC-18 — Secret management, encryption, and key lifecycle integration

**Status:** Missing.  
**Checklist:** C039, C047, C048.  
**Needed:** explicit secret references rather than inline values, KMS/secret-store
integration, encryption in transit/at rest for sensitive state, key rotation,
and safe failure behavior when key services are unavailable.

## MC-19 — Complete threat model and adversarial validation plan

**Status:** Partial.  
**Checklist:** C041, C050.  
**Present:** five threat bullets in `contract.py`.  
**Missing:** assets, trust boundaries, attacker models, abuse cases, mitigations,
residual risk, ownership, and executable tests for privilege escalation,
injection, replay, spoofing, escape, side channels, and exhaustion.

## MC-20 — Ambient-authority reduction and runtime isolation controls

**Status:** Missing / deployment-layer dependent.  
**Checklist:** C043, C046.  
**Needed:** explicit filesystem/network/device/kernel/secret capability model,
sandbox profile, tenant isolation controls, and verification that the deployed
resolver/service receives no ambient authority beyond its requirements.

## MC-21 — Artifact/provider signature, provenance, and supply-chain verification

**Status:** Missing.  
**Checklist:** C045.  
**Present:** application revision and binding hashes provide content integrity,
not authenticity.  
**Needed:** signed component/provider artifacts, trust policy, provenance/SBOM,
approved-version policy, signature verification, revocation, and negative tests.

## MC-22 — Tamper-evident security audit event ledger

**Status:** Missing.  
**Checklist:** C049.  
**Needed:** security-event schema, append-only/tamper-evident storage, chain or
signature verification, actor/tenant/correlation fields, retention, export, and
access control.

## MC-23 — Complete failure catalogue, health, and stall detection

**Status:** Partial.  
**Checklist:** C051, C052.  
**Present:** three contract failure modes and typed local refusals.  
**Missing:** process/node/site/network/provider/control-plane failure catalogue,
health/readiness model, stall thresholds, dependency health, watchdog behavior,
and objective-driven detection tests.

## MC-24 — Failover, split-brain protection, quarantine, freeze, and disable controls

**Status:** Missing.  
**Checklist:** C055, C058, C059.  
**Needed:** ownership/lease fencing, stale-controller rejection, duplicate
publication prevention, quarantine/freeze/disable APIs, failover constraints,
and recovery procedures.

## MC-25 — Revision publication store and durable lifecycle

**Status:** Missing.  
**Checklist:** C004, C032, C057, C095.  
**Present:** an in-memory dictionary with a content address.  
**Missing:** authoritative immutable revision store, atomic publish, lookup,
history/supersession links, sealing, retention, crash consistency, restart/replay,
backup/restore, and migration/reconstruction procedures.

## MC-26 — Tenant/environment/site context propagation and enforcement

**Status:** Partial.  
**Checklist:** C006, C046, C064, C073.  
**Present:** contract documentation of boundaries.  
**Missing:** tenant/environment/site fields in the resolved document, scoped
catalogue lookup, isolation checks, per-tenant accounting, and stable telemetry
identifiers.

## MC-27 — Provider catalogue client/service with freshness and provenance

**Status:** Missing.  
**Checklist:** C004, C021, C036, C044, C045, C051.  
**Present:** resolver receives an already-selected in-memory capability→provider
map.  
**Missing:** catalogue acquisition, revision/freshness, signed provenance,
provider health, atomic snapshot semantics, cache policy, and stale-catalogue
handling.

## MC-28 — Provider selection and explainable binding policy

**Status:** Missing.  
**Checklist:** C019, C076, C077.  
**Present:** one provider ID per capability is supplied directly.  
**Missing:** candidate sets, selection constraints, cost/locality/residency/SLO
policy, deterministic tie-breaking, rejection rationale, and an explain view.

## MC-29 — Performance baseline and regression certification suite

**Status:** Missing.  
**Checklist:** C061-C070.  
**Needed:** reproducible p50/p95/p99/worst-case latency, throughput, startup, CPU,
memory, storage/network overhead, steady/burst/overload/scale/recovery profiles,
per-tenant overhead, allocation/copy analysis, constrained-edge power/thermal
measurement, capacity model, and release-blocking regression thresholds.

## MC-30 — Runtime observability implementation

**Status:** Missing.  
**Checklist:** C071-C078.  
**Present:** contract lists four desired signal names.  
**Missing:** actual health/readiness/version/config/dependency endpoint, metrics,
structured logs, trace-context propagation, safe high-cardinality diagnostics,
decision-reason records, explain API, and release/infrastructure graph
correlation.

## MC-31 — Telemetry governance, dashboards, and alerts

**Status:** Missing.  
**Checklist:** C079, C080.  
**Needed:** retention/sampling/privacy/export policy, redaction, dashboards, and
alerts that distinguish load, degradation, policy rejection, dependency failure,
attack, and software defect.

## MC-32 — Full fuzz, property, concurrency, and security test suites

**Status:** Partial.  
**Checklist:** C081, C082, C085-C087.  
**Present:** deterministic unit/contract tests and an audit-time randomized
exercise.  
**Missing:** committed property-based/fuzz corpus, parser/schema fuzzing,
concurrency/race tests for future shared state, and complete tests derived from
the threat model.

## MC-33 — Fault-injection, disaster, partition, reconnect, and degraded-control-plane tests

**Status:** Missing.  
**Checklist:** C060, C089.  
**Needed:** controlled dependency/provider/network/site failures, recovery
objectives, stale-catalogue behavior, reconnect reconciliation, and evidence of
bounded recovery.

## MC-34 — Cross-platform and protocol compatibility CI matrix

**Status:** Missing.  
**Checklist:** C084, C093.  
**Needed:** supported CPU/OS/Python/runtime/provider/protocol combinations,
automated matrix tests, compatibility evidence, and explicit unsupported
combinations.

## MC-35 — Benchmark, soak, burst, and fleet-scale certification environment

**Status:** Missing.  
**Checklist:** C088.  
**Needed:** repeatable large-scale workloads, long-duration soak, burst and
fleet simulations, leak/stability thresholds, result retention, and release
comparison baselines.

## MC-36 — CI/CD production gate and machine-readable release evidence

**Status:** Missing from this archive.  
**Checklist:** C070, C090, C100.  
**Present:** commands referencing external `pk_core`.  
**Missing:** CI configuration, required checks, generated gate artifact, evidence
ledger artifact, signature/attestation, fail-closed release policy, and a proven
full-estate gate run.

## MC-37 — Canary, staged rollout, rollback, and emergency-disable automation

**Status:** Partial documentation only.  
**Checklist:** C092, C096.  
**Present:** brief README day-0/day-1/day-2 notes.  
**Missing:** executable rollout stages, health criteria, rollback triggers,
emergency disable/freeze mechanism, operator commands, drills, and recovery
verification.

## MC-38 — Support, vulnerability, incident, review, and technical-debt governance

**Status:** Missing.  
**Checklist:** C091, C094, C097-C099.  
**Needed:** support commitments; patch/vulnerability/EOL SLAs; incident severity,
paging, escalation, containment and recovery; recurring access/policy/dependency/
configuration/architecture reviews; and owned exception/waiver/deprecation/debt
registers with expiry dates.

## MC-39 — License, NOTICE, and distribution policy for this standalone archive

**Status:** Missing from the supplied package.  
**Needed:** explicit repository/package license, NOTICE/attribution where
required, third-party dependency licensing process, and release-distribution
policy. A parent repository may provide these, but none is present in this
archive and none was assumed.

---

## Summary

**Post-hardening missing-component groups: 39.**

The highest-risk remaining gaps for production use are MC-08 (traceable release
evidence), MC-11/12 (authentication and authorization), MC-21/22 (supply-chain
and audit integrity), MC-25/27 (authoritative revision/catalogue services),
MC-29/30 (performance/observability evidence), and MC-36 (actual production
gate). The OAM/WIT promises in the source description also remain materially
unimplemented (MC-09/10).
