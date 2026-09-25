# GAP-04 Disconnected Operation Controller
## Missing Components — Professional Engineering Checklist
**Checklist version:** 1.0.0  
**Baseline audited implementation:** GAP-04 v4.2.0  
**Source register:** `GAP04_v4.2.0_MISSING_COMPONENTS.md`  
**Scope:** 56 remaining production-readiness components identified after the v4.2.0 audit.

> **Status run:** GAP-04 4.3.0 against checklist 1.0.0 · generated 2026-09-22 from `tools/build_status.py` · test run `local-4beee8cb841d`
> **Totals:** 666 verified [x] · 606 partial [~] · 118 blocked [!] · 60 not started [ ] · 6 N/A pending approval [-] — of 1456 controls.
> **Production gate:** NO_GO (see `evidence/gate_decision.json`). A checkbox is [x] only where code/tests/artifacts exist and were run; nothing is marked complete on narrative alone.

### Purpose

This document converts the 56-item missing-component register into an implementation-grade engineering checklist. It is intended for architecture review, sprint planning, implementation, security review, verification, operations readiness, and Production-GO evidence.

### Status convention

Use one status per checkbox in the project tracker:

- `[ ]` Not started
- `[~]` In progress / partially satisfied
- `[x]` Implemented **and** evidence attached
- `[!]` Blocked
- `[-]` Not applicable — requires written rationale and approval

A checkbox is not considered complete solely because code exists. Completion requires objective evidence appropriate to the control: source reference, test ID/result, schema/contract, configuration or policy artifact, operational dashboard/runbook, security review, release artifact digest, or approved exception.

### Required evidence fields for every component

For each component, record:

- **Owner**
- **Reviewer / approver**
- **Target release**
- **Implementation references**
- **Schema / contract references**
- **Test IDs and latest passing evidence**
- **Operational evidence**
- **Security evidence**
- **Known exceptions / waiver IDs**
- **Last review date**
- **Final status**
- **Production-GO impact**

### Global completion rules

1. P0 controls are blocking for production autonomy unless an explicitly authorized governance process states otherwise.
2. P1 controls are required for production operations, reliability, release qualification, or verification as designated by the formal GO policy.
3. P2 controls establish governance and lifecycle completeness and must not be represented as satisfied without retained evidence.
4. Security-critical inputs fail closed on ambiguity, invalid signatures, stale authority, unsupported versions, integrity failure, or uncertain durable state.
5. Safety-critical decisions must be traceable to the exact lease, policy, authority epoch, partition epoch, controller generation, configuration, code version, and durable journal/audit evidence used.
6. Every external contract and durable format must be versioned and included in compatibility testing.
7. Every accepted offline decision must be recoverable, attributable, reconcilable, and idempotent after process/host failure.
8. No requirement may be marked complete using narrative assertion alone.

---

## 01. Cryptographically signed autonomy lease envelope

**Priority:** P0  
**Control family:** Crypto  

### Checklist

- [x] **GAP04-C01-001** — Document the threat model, trust anchors, cryptographic assumptions, protected assets, attacker capabilities, and explicit non-goals.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-002** — Define a versioned schema/interface with strict parsing, size limits, canonical encoding requirements, and backward/forward compatibility behavior.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-003** — Add secure defaults and fail-closed behavior for unknown versions, invalid cryptographic material, unavailable trust state, and ambiguous inputs.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-004** — Instrument stable reason codes, security audit events, health state, and bounded-cardinality metrics for verification failures.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-005** — Create positive, negative, boundary, corruption, downgrade, replay, and version-skew test vectors and retain them as release evidence.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-006** — Define a canonical, versioned lease envelope containing issuer identity, subject/site/node binding, lease ID, issuance time, not-before time, expiry time, policy version/hash, capability set, authority generation/epoch, nonce, key ID, signature algorithm, and signature bytes.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-007** — Define a deterministic canonical serialization for signing and verification; prohibit ambiguous field ordering, duplicate keys, non-canonical numeric encodings, and alternate Unicode representations.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-008** — Bind every lease to a specific trust domain and deployment scope so a lease issued for one site, tenant, cluster, node class, or environment cannot be replayed in another.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-009** — Implement signature verification against an explicit trust store; reject unknown issuers, unknown key IDs, revoked keys, unsupported algorithms, malformed signatures, and unverifiable certificate chains.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-010** — Pin an allow-list of cryptographic algorithms and key sizes; explicitly reject algorithm substitution, `none`, downgrade, legacy, and weak-curve/key configurations.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-011** — Validate issuance/not-before/expiry ordering, maximum lease lifetime, permitted clock skew, policy digest format, capability syntax, generation monotonicity, and nonce length before accepting a lease.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-012** — Make lease verification fail closed before any offline action authorization; no local decision may use a lease whose authenticity, freshness, scope, policy binding, or authority epoch is uncertain.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-013** — Add deterministic negative tests for forged signatures, wrong-site bindings, wrong policy hashes, expired leases, future-issued leases, stale epochs, modified capabilities, truncated payloads, and unknown issuers.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-014** — Add key-rotation tests covering overlapping signer validity, new-key rollout, old-key revocation, forced rollover, and recovery from stale verifier trust bundles.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [x] **GAP04-C01-015** — Record the verified lease fingerprint, signer/key ID, authority generation, policy hash, and verification result in the audit record without logging private key material or sensitive capability payloads.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [~] **GAP04-C01-016** — Expose machine-readable lease verification status and reason codes to health/readiness and reconciliation interfaces.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease` · Note: health exposes lease id/watermark and verification-failure metrics by code; no explicit per-lease verification-status field

- [x] **GAP04-C01-017** — Define a signed-envelope schema fixture and compatibility suite for every supported lease-envelope version.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [~] **GAP04-C01-018** — Document issuer responsibilities, key custody, signing service SLOs, revocation path, emergency key compromise procedure, and maximum tolerated verification outage.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease` · Note: issuer duties documented in THREAT_MODEL §7; key custody and signing-service SLOs belong to the control-plane owner (W-001/W-005)

- [~] **GAP04-C01-019** — Produce release evidence showing the exact crypto library/version, FIPS or equivalent mode where required, verifier configuration, trust roots, and test vectors.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease` · Note: library/version pinned and recorded; FIPS mode not validated (W-005) · Waiver(s): W-005

- [x] **GAP04-C01-020** — Production gate: demonstrate that no unsigned, unverifiable, stale, cross-site, downgraded, or policy-mismatched lease can authorize an offline action.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`


### Component acceptance evidence

- [~] **GAP04-C01-021** — An approved design/ADR exists for **Cryptographically signed autonomy lease envelope** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C01-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [~] **GAP04-C01-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C01-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C01-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`

- [~] **GAP04-C01-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-005, W-007, W-009
- **Status:** In progress (19 verified / 6 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/trust.py`, `runtime/canonical.py`, `runtime/crypto.py`, `runtime/node.py:install_lease`
- **Remaining gap:** Issuer-side custody/SLOs and FIPS evidence depend on the control-plane org.


---


## 02. Trusted time source and reboot-safe anti-rollback clock

**Priority:** P0  
**Control family:** Time  

### Checklist

- [x] **GAP04-C02-001** — Document clock trust assumptions, threat model, supported hardware/virtualization environments, and fail-safe behavior when trust degrades.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C02-002** — Define explicit API contracts for trusted monotonic time, wall time, uncertainty/quality, checkpoint persistence, and rollback detection.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C02-003** — Ensure all safety timers use one reviewed time abstraction rather than direct calls to wall-clock APIs.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-004** — Expose machine-readable degradation reasons and audit transitions in clock trust state.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Software HWM only; whole-disk rollback while partitioned is a documented residual risk (W-012).

- [!] **GAP04-C02-005** — Retain platform-specific qualification evidence for every supported OS/hardware class.
  - Note: blocked; Software HWM only; whole-disk rollback while partitioned is a documented residual risk (W-012). · Waiver(s): W-008

- [x] **GAP04-C02-006** — Define a trusted-time abstraction that separates wall-clock presentation from monotonic safety time used for lease expiry, policy freshness, and timeout decisions.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-007** — Persist anti-rollback state across reboot using TPM NV counters, secure monotonic storage, signed checkpoints, or an equivalently tamper-resistant mechanism appropriate to the platform.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: HWM persisted in MAC'd journal frames; no TPM NV counter (W-012) · Waiver(s): W-012

- [x] **GAP04-C02-008** — Detect wall-clock rollback beyond an explicitly configured tolerance and enter a fail-safe state that forbids extension of any lease or policy freshness window.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-009** — Detect VM snapshot restore or disk-image rollback through persisted generation/checkpoint mismatches, monotonic counters, or attested boot state.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: detected when a trusted anchor is below HWM; a full-disk restore is undetectable offline (R1) · Waiver(s): W-012

- [x] **GAP04-C02-010** — Ensure reboot cannot reset elapsed-disconnect duration, lease age, policy age, revocation age, or reconciliation deadlines.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-011** — Model NTP/PTP/GPS/manual clock corrections explicitly; large forward or backward jumps must be classified and audited rather than silently accepted.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: jumps beyond max_drift fail closed and are counted; small slews accepted without classification

- [~] **GAP04-C02-012** — Specify trusted-time source priority, quorum/consensus rules if multiple sources exist, holdover behavior, accuracy bounds, and maximum disconnected holdover.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: priority signed token > authenticated adapter > optional RTC; no multi-source quorum

- [~] **GAP04-C02-013** — Bind stored trusted-time checkpoints to device identity and integrity-protected state so they cannot be transplanted to another node.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: HWM frames are MAC'd with the node audit key; transplant together with keys.json is possible

- [~] **GAP04-C02-014** — Add tests for RTC reset, daylight-saving changes, leap seconds, timezone changes, NTP step/slew, suspend/resume, hibernation, reboot, snapshot restore, and battery-backed-clock failure.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: RTC reset, reboot, snapshot restore, rollback, jump tested; suspend/hibernate not; DST/timezone/leap irrelevant (integer UTC)

- [x] **GAP04-C02-015** — Define behavior when trusted time is unavailable: deny new autonomy grants, preserve conservative expiry, surface degraded health, and prevent manual override from silently extending authority.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-016** — Audit every time-source transition, rollback detection, holdover entry/exit, and administrator time override with old/new values and source identity.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: rollback/jump rejections counted and logged; anchor transitions not individually audited

- [x] **GAP04-C02-017** — Expose monotonic-age and trusted-time-quality indicators through telemetry without leaking security-sensitive platform data.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C02-018** — Verify integer widths and overflow behavior for long uptimes, far-future timestamps, epoch conversions, and serialization across supported runtimes.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-019** — Document platform-specific trusted-time dependencies and minimum hardware/firmware requirements.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in THREAT_MODEL §6; hardware requirements depend on W-012

- [~] **GAP04-C02-020** — Production gate: prove with reboot/snapshot/clock-manipulation tests that elapsed authority can never be extended by moving time backward.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: reboot/rollback tests pass; whole-disk rollback residual (R1) · Waiver(s): W-012


### Component acceptance evidence

- [~] **GAP04-C02-021** — An approved design/ADR exists for **Trusted time source and reboot-safe anti-rollback clock** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C02-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C02-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C02-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C02-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/clock.py`, `runtime/node.py:_now`, `tests/test_p0_durability.py::TrustedTime`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-008, W-009, W-012
- **Status:** In progress (11 verified / 13 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/clock.py`, `runtime/node.py:_now`
- **Remaining gap:** Software HWM only; whole-disk rollback while partitioned is a documented residual risk (W-012).


---


## 03. Durable crash-consistent offline decision journal

**Priority:** P0  
**Control family:** Persistence  

### Checklist

- [x] **GAP04-C03-001** — Document durability guarantees, crash model, filesystem/database assumptions, integrity model, retention, and recovery invariants.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C03-002** — Version all on-disk formats and define forward migration, backward-read, and unsupported-version behavior.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: partially implemented; Qualified on one filesystem only; ENOSPC/fsync-error injection not real.

- [x] **GAP04-C03-003** — Make writes bounded, checksummed/integrity-protected as appropriate, and safe under abrupt termination.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C03-004** — Expose durable sequence/checkpoint state and persistence failures through health, logs, metrics, and machine-readable errors.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: partially implemented; Qualified on one filesystem only; ENOSPC/fsync-error injection not real.

- [!] **GAP04-C03-005** — Qualify on every supported storage/filesystem profile with deterministic fault injection.
  - Note: blocked; Qualified on one filesystem only; ENOSPC/fsync-error injection not real. · Waiver(s): W-008

- [x] **GAP04-C03-006** — Replace the in-memory journal with a durable write-ahead or append-only log whose commit point is defined in terms of actual persistence semantics.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C03-007** — Specify record framing, schema version, length, checksum/MAC, decision ID, partition epoch, policy version/hash, lease ID, operation, result, timestamp, and reconciliation state.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: frames carry seq/gen/kind/prev/h/mac + decision bindings; no explicit per-frame schema version (file format PK_JOURNAL/1)

- [~] **GAP04-C03-008** — Use atomic append/rename/fsync semantics appropriate to each supported filesystem; explicitly document directory fsync requirements and Windows equivalents.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: tmp+fsync+rename+dir-fsync on POSIX; Windows equivalent present but unqualified (W-008)

- [~] **GAP04-C03-009** — Implement startup recovery that scans to the last valid committed record, detects torn writes, isolates corrupt segments, and never fabricates or silently drops committed decisions.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: torn tail truncated, mid-file corruption fails closed; corrupt segments are not isolated/quarantined automatically

- [x] **GAP04-C03-010** — Separate `accepted locally`, `persisted`, `applied to supervisor`, `queued for reconciliation`, and `reconciled` states so crash recovery can determine exactly what must be replayed.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C03-011** — Guarantee stable ordering using a monotonic per-controller sequence and partition epoch; define behavior for sequence gaps and duplicates.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C03-012** — Implement bounded retention with segment rotation, compaction, archival, and watermarks that never delete unreconciled or legally required audit evidence.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C03-013** — Reserve emergency journal capacity so storage pressure cannot prevent recording the decision that autonomy is being frozen.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C03-014** — Add configurable durability modes only if safety policy permits; the production profile must not acknowledge a decision before required persistence is achieved.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C03-015** — Protect journal contents with integrity checks and, where sensitive, encryption; manage keys independently from data files.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C03-016** — Add power-cut/fault-injection tests at every byte/record/segment transition, including allocation failure, partial sector write, ENOSPC, fsync failure, and directory metadata failure.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: 10 named crash points + random SIGKILL; no real ENOSPC/fsync-failure/partial-sector injection

- [~] **GAP04-C03-017** — Add recovery tests for repeated crash loops, corrupted tail records, corrupted middle segments, missing segments, duplicated segments, and rollback to an older disk snapshot.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: torn tail, mid corruption, crash loops tested; missing/duplicated segments and old-snapshot rollback not

- [~] **GAP04-C03-018** — Expose journal utilization, oldest unreconciled decision, segment count, corruption state, last durable sequence, and compaction status as metrics.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: utilization/bytes/seq exposed; oldest unreconciled age, segment count, corruption state not

- [~] **GAP04-C03-019** — Document data-retention, export, privacy, and forensic requirements for journal records.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: classification/retention in THREAT_MODEL §5; legal/forensic policy needs owner approval

- [x] **GAP04-C03-020** — Production gate: demonstrate lossless recovery of every acknowledged offline decision after abrupt power loss with deterministic handling of corruption.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`


### Component acceptance evidence

- [~] **GAP04-C03-021** — An approved design/ADR exists for **Durable crash-consistent offline decision journal** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C03-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C03-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C03-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C03-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C03-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`, `tests/test_p0_durability.py::JournalWAL` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-008, W-009
- **Status:** In progress (12 verified / 12 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/journal.py`, `runtime/storage.py:atomic_write`, `runtime/node.py:_recover`
- **Remaining gap:** Qualified on one filesystem only; ENOSPC/fsync-error injection not real.


---


## 04. Tamper-evident audit chain

**Priority:** P0  
**Control family:** Audit  

### Checklist

- [x] **GAP04-C04-001** — Define audit threat model, evidence retention period, authority/ownership, privacy classification, and verifier trust model.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C04-002** — Version the event/export format and provide independent verification tooling.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C04-003** — Make audit persistence non-optional for actions that require accountability and fail safely if required audit evidence cannot be recorded.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-004** — Expose backlog/integrity/export state via health and metrics with high-severity alerts on verification failure.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Hash chain + HMAC; no signed checkpoints, audit-key rotation, or site binding.

- [x] **GAP04-C04-005** — Retain verification reports and representative tamper tests in release evidence.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-006** — Define an append-only audit event schema with event ID, sequence, previous-event digest, event digest, actor/issuer identity, controller generation, partition epoch, policy/lease fingerprints, action, result, reason code, and trusted timestamp evidence.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: frame schema has seq/prev/h/gen/kind; actor/policy bindings live in decision bodies rather than a separate audit schema

- [x] **GAP04-C04-007** — Choose and document the integrity construction: hash chain, Merkle accumulator, signed checkpoints, or an equivalent design with explicit threat assumptions.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-008** — Protect audit signing/MAC keys in TPM/HSM/secure element or OS-protected key storage; prohibit storage beside unprotected audit data.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: audit key in keys.json (0600), separate file, no TPM/HSM (W-005) · Waiver(s): W-005

- [~] **GAP04-C04-009** — Create periodic signed checkpoints so long chains can be verified incrementally and exported without trusting local mutable metadata.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: MAC'd anchor header on compaction; no periodic signed checkpoints

- [~] **GAP04-C04-010** — Detect sequence deletion, insertion, reordering, truncation, forked histories, altered fields, and replayed prior audit segments.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: deletion/insertion/modification/reorder detected; whole-frame tail truncation indistinguishable from crash (R3)

- [~] **GAP04-C04-011** — Bind audit chains to controller generation and device/site identity so copied chains cannot be presented as evidence from another controller.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: generation bound per frame; site/device identity not bound into chain

- [x] **GAP04-C04-012** — Define crash-consistent ordering between business decisions and their audit events so an accepted decision cannot exist without durable accountability evidence.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C04-013** — Implement verifier tooling that can validate an exported chain offline and produce machine-readable success/failure plus first-corrupt-event information.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-014** — Define reconnect upload protocol with resumable transfer, acknowledgement watermarks, duplicate suppression, and server-side verification.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: export attached to reconciliation; resumable audit upload protocol not implemented

- [~] **GAP04-C04-015** — Add tests that mutate every event field, break links, remove events, reorder ranges, truncate files, alter checkpoints, substitute keys, and replay an older chain.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: delete/forge/MAC tests; not every field, key substitution or old-chain replay

- [x] **GAP04-C04-016** — Ensure logs redact secrets and sensitive payloads while retaining enough normalized identifiers to support forensic reconstruction.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-017** — Expose chain head digest, verified sequence, upload watermark, backlog, key ID, and verification failures through telemetry.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: audit head in reconciliation record; no chain-head metric

- [~] **GAP04-C04-018** — Define retention, legal hold, privacy deletion exceptions, and forensic export procedures without undermining chain verifiability.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: retention documented; legal-hold process needs owner

- [ ] **GAP04-C04-019** — Document key rotation while preserving verifiable continuity across signer changes.
  - Note: not started: audit MAC key rotation with continuity

- [~] **GAP04-C04-020** — Production gate: an independent verifier must detect any unauthorized modification, deletion, insertion, reordering, truncation, or cross-device substitution of audit history.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: independent verifier exists; tail truncation and cross-device substitution gaps


### Component acceptance evidence

- [~] **GAP04-C04-021** — An approved design/ADR exists for **Tamper-evident audit chain** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C04-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C04-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C04-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C04-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`, `tests/test_p0_durability.py::JournalWAL`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-005, W-007, W-009
- **Status:** In progress (10 verified / 14 partial / 1 blocked / 1 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/journal.py:verify_export`, `runtime/node.py:reconnect`
- **Remaining gap:** Hash chain + HMAC; no signed checkpoints, audit-key rotation, or site binding.


---


## 05. Policy artifact integrity and provenance

**Priority:** P0  
**Control family:** Crypto  

### Checklist

- [x] **GAP04-C05-001** — Document the threat model, trust anchors, cryptographic assumptions, protected assets, attacker capabilities, and explicit non-goals.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C05-002** — Define a versioned schema/interface with strict parsing, size limits, canonical encoding requirements, and backward/forward compatibility behavior.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C05-003** — Add secure defaults and fail-closed behavior for unknown versions, invalid cryptographic material, unavailable trust state, and ambiguous inputs.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C05-004** — Instrument stable reason codes, security audit events, health state, and bounded-cardinality metrics for verification failures.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-005** — Create positive, negative, boundary, corruption, downgrade, replay, and version-skew test vectors and retain them as release evidence.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Bundle format lacks activation window/dependencies; policy build pipeline belongs to GAP-13.

- [~] **GAP04-C05-006** — Define a signed policy bundle format containing policy ID, semantic version, content digest, issuer, trust domain, creation time, activation window, rollback floor, dependencies, schema version, and signature metadata.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: bundle has version, issuer, trust domain, activated_at, author/approver; no activation window, dependencies, explicit floor field

- [x] **GAP04-C05-007** — Canonicalize policy bytes before hashing/signing and define exactly which metadata is covered by the signature.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-008** — Validate signer trust, certificate/key status, algorithm allow-list, digest, schema compatibility, activation conditions, and dependency versions before staging.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: signer/alg/digest/schema validated; activation conditions/dependency versions not

- [x] **GAP04-C05-009** — Pin the lease to the exact policy digest or immutable policy identifier used for every offline decision.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C05-010** — Maintain a monotonic policy rollback floor so an attacker cannot reactivate an older but correctly signed vulnerable policy.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C05-011** — Persist activation metadata and the last-known-good policy transactionally with controller generation and lease state.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-012** — Provide staged validation before activation: schema validation, semantic validation, dependency resolution, test evaluation, and dry-run compatibility checks.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: structural validation only; no semantic dry-run

- [x] **GAP04-C05-013** — Fail closed if the active policy bundle becomes unreadable, unverifiable, internally inconsistent, or newer than the local evaluator supports.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-014** — Record provenance: build source, author/approver, CI attestation, policy compiler version, policy-engine version, and release artifact digest.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: author/approver recorded; CI attestation/compiler/engine versions not

- [~] **GAP04-C05-015** — Add tests for signature alteration, stale signer, expired signer, wrong trust domain, digest mismatch, rollback attempts, malformed dependencies, unsupported schema, and partial writes.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: alteration, rollback, same-version reuse, digest mismatch tested; expired signer partially

- [~] **GAP04-C05-016** — Expose active policy ID/version/digest, verification status, age, activation time, rollback floor, and last refresh result via health/metrics.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: version and age in health; digest/activation time not

- [x] **GAP04-C05-017** — Define secure cache eviction so the last-known-good policy is retained until an explicitly safer fallback is available.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-018** — Document emergency revocation of a policy bundle and how disconnected nodes learn the revocation when connectivity returns.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in RUNBOOK RB-04; emergency revocation of a bundle needs GAP-13 contract

- [!] **GAP04-C05-019** — Provide a reproducible policy-build pipeline with deterministic output and signed provenance.
  - Note: blocked: reproducible policy build pipeline is GAP-13's (W-002)

- [x] **GAP04-C05-020** — Production gate: only an authenticated, integrity-verified, non-rolled-back, lease-matched policy artifact may authorize offline behavior.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`


### Component acceptance evidence

- [~] **GAP04-C05-021** — An approved design/ADR exists for **Policy artifact integrity and provenance** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C05-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C05-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C05-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C05-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`, `tests/test_p0_lease_policy.py::PolicyProvenance`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (13 verified / 11 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/trust.py:verify_policy`, `runtime/node.py:install_policy`
- **Remaining gap:** Bundle format lacks activation window/dependencies; policy build pipeline belongs to GAP-13.


---


## 06. Revocation epoch/watermark mechanism

**Priority:** P0  
**Control family:** Auth State  

### Checklist

- [x] **GAP04-C06-001** — Document authority topology, trust roots, propagation assumptions, offline risk window, and disaster-recovery constraints.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-002** — Version authority-state messages and authenticate every update.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: partially implemented; Single global epoch; epoch update API is authorized but the epoch value itself is not a signed message.

- [~] **GAP04-C06-003** — Persist monotonic security state using rollback-resistant techniques appropriate to the platform.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: partially implemented; Single global epoch; epoch update API is authorized but the epoch value itself is not a signed message.

- [~] **GAP04-C06-004** — Expose freshness/generation state and stale/replay denials through health, audit, metrics, and stable error codes.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: partially implemented; Single global epoch; epoch update API is authorized but the epoch value itself is not a signed message.

- [~] **GAP04-C06-005** — Test issuer failover, reconnect ordering, stale replay, and restored-backup scenarios.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: partially implemented; Single global epoch; epoch update API is authorized but the epoch value itself is not a signed message.

- [x] **GAP04-C06-006** — Define a monotonically increasing authority epoch or revocation watermark scoped to the trust domain and bound into every lease/cached grant.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-007** — Persist the highest accepted epoch in rollback-resistant storage and reject any authority object carrying a lower epoch after restart or reconnect.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: persisted in journal (software rollback resistance, W-012)

- [~] **GAP04-C06-008** — Specify issuance semantics for global, site, node, workload, policy, and capability-specific revocation domains if different scopes are required.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: single authority epoch + lease-id + grant revocations; no per-scope domains

- [x] **GAP04-C06-009** — Ensure reconnect processing applies newer revocation state before renewing or issuing replacement offline authority.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-010** — Define behavior for epoch gaps, concurrent issuer replicas, issuer failover, and recovery from a lost or rebuilt authority service.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: documented only (issuer failover out of scope)

- [~] **GAP04-C06-011** — Protect epoch updates cryptographically so unauthenticated peers cannot force denial-of-service by advertising artificially high generations.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: apply_revocations is authz-gated but the epoch value is not signed (DoS by authorized caller possible)

- [x] **GAP04-C06-012** — Include revocation epoch in journal and audit records for every decision so later reconciliation can prove which authority state was used.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C06-013** — Invalidate cached grants deterministically when their epoch falls below the accepted watermark.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-014** — Add tests for stale lease replay, stale cached grant replay, reboot with older persisted state, snapshot rollback, concurrent epoch updates, and forged high epochs.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: stale lease replay + restart tested; snapshot rollback, concurrent updates, forged high epochs not

- [x] **GAP04-C06-015** — Define how offline nodes bound risk when revocation information may have advanced while disconnected.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-016** — Expose current accepted epoch, lease epoch, policy epoch if separate, and last authenticated refresh time through health and metrics.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: watermark in health; lease epoch not separately

- [~] **GAP04-C06-017** — Provide operational tooling to inspect and advance epochs with authenticated, auditable controls and two-person approval where appropriate.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: authorized API; no two-person control

- [x] **GAP04-C06-018** — Document epoch exhaustion/width, serialization, wraparound prohibition, and migration strategy.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-019** — Define disaster-recovery rules so restoring the authority service cannot move the generation backward.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: documented in THREAT_MODEL; authority-service DR is upstream

- [x] **GAP04-C06-020** — Production gate: a previously revoked or superseded grant must remain invalid after reconnect, restart, failover, and snapshot restoration.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`


### Component acceptance evidence

- [~] **GAP04-C06-021** — An approved design/ADR exists for **Revocation epoch/watermark mechanism** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C06-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C06-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C06-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C06-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`, `tests/test_p0_lease_policy.py::RevocationEpoch`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (10 verified / 15 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/node.py:apply_revocations`, `runtime/trust.py:verify_lease`
- **Remaining gap:** Single global epoch; epoch update API is authorized but the epoch value itself is not a signed message.


---


## 07. Durable replay/idempotency identifiers

**Priority:** P0  
**Control family:** Persistence  

### Checklist

- [x] **GAP04-C07-001** — Document durability guarantees, crash model, filesystem/database assumptions, integrity model, retention, and recovery invariants.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-002** — Version all on-disk formats and define forward migration, backward-read, and unsupported-version behavior.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: partially implemented; Dedupe window is per partition; retention semantics across partitions documented but not formally bounded.

- [x] **GAP04-C07-003** — Make writes bounded, checksummed/integrity-protected as appropriate, and safe under abrupt termination.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-004** — Expose durable sequence/checkpoint state and persistence failures through health, logs, metrics, and machine-readable errors.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: partially implemented; Dedupe window is per partition; retention semantics across partitions documented but not formally bounded.

- [!] **GAP04-C07-005** — Qualify on every supported storage/filesystem profile with deterministic fault injection.
  - Note: blocked; Dedupe window is per partition; retention semantics across partitions documented but not formally bounded.

- [x] **GAP04-C07-006** — Assign every locally accepted decision a globally unique, durable decision ID generated before side effects occur.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-007** — Assign every reconciliation batch/transaction a stable idempotency key that survives retry, process crash, timeout, and network reconnect.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-008** — Define identifier entropy, format, namespace, collision assumptions, and whether IDs encode site/controller generation or remain opaque.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-009** — Persist IDs transactionally with decision payload, journal sequence, effect status, and reconciliation acknowledgement.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-010** — Implement server-side and local duplicate-detection windows sized to the maximum retry/recovery horizon.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: local dedupe per open partition; server side only in reference GAP-05

- [~] **GAP04-C07-011** — Define exact semantics for duplicate `pending`, `applied`, `rejected`, `rolled back`, `quarantined`, and `already reconciled` requests.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: replayed flag + E0601 for content mismatch; full duplicate-state semantics not enumerated

- [x] **GAP04-C07-012** — Never generate a new idempotency key merely because a request timed out; retries must reuse the original key.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-013** — Bind IDs to canonical request hashes so an attacker or bug cannot reuse an old key with different content.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-014** — Add tests for retry storms, lost acknowledgements, crash after remote commit/before local commit, crash before remote commit, duplicate journal replay, and concurrent retry from duplicate controllers.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-015** — Define retention/garbage-collection policy for idempotency records so expired dedupe state cannot re-enable an old destructive request.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: dedupe index cleared after reconciliation; a reused request id in a later partition yields a new decision (different epoch)

- [x] **GAP04-C07-016** — Expose duplicate/replay counters and dedupe-cache pressure metrics.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-017** — Audit detected replays with source peer, original decision ID, canonical request hash, and disposition.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-018** — Document cross-version idempotency semantics so rolling upgrades do not change the meaning of existing keys.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: cross-version semantics stated in ADR-005 only

- [x] **GAP04-C07-019** — Ensure identifiers contain no sensitive information if exposed across trust boundaries.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [x] **GAP04-C07-020** — Production gate: repeated delivery of any previously committed reconciliation or supervisor command must not create a second side effect.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`


### Component acceptance evidence

- [~] **GAP04-C07-021** — An approved design/ADR exists for **Durable replay/idempotency identifiers** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C07-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C07-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C07-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py`

- [~] **GAP04-C07-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:_decide`, `runtime/node.py:reconnect`, `tests/test_p0_reconcile_adapters.py::Idempotency`, `tests/test_crash_recovery.py` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 9 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/node.py:_decide`, `runtime/node.py:reconnect`
- **Remaining gap:** Dedupe window is per partition; retention semantics across partitions documented but not formally bounded.


---


## 08. Real reconciliation engine

**Priority:** P0  
**Control family:** Reconciliation  

### Checklist

- [x] **GAP04-C08-001** — Document convergence model, authoritative source, conflict taxonomy, reversible/irreversible operations, and operator escalation rules.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [x] **GAP04-C08-002** — Version reconciliation request/result schemas and bind them to stable decision/idempotency identifiers.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [x] **GAP04-C08-003** — Persist progress so retries and crashes are safe and deterministic.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [~] **GAP04-C08-004** — Expose conflict/backlog/retry/quarantine state through health, metrics, logs, and traces.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: partially implemented; Authoritative-wins with compensate/quarantine; no merge functions, operator replay tool or vector clocks.

- [~] **GAP04-C08-005** — Use property/fault-injection testing to prove idempotency and convergence for supported operation classes.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: partially implemented; Authoritative-wins with compensate/quarantine; no merge functions, operator replay tool or vector clocks.

- [~] **GAP04-C08-006** — Define reconciliation states and transitions for pending, matched, conflicting, superseded, accepted, rolled back, quarantined, retriable failure, permanent failure, and acknowledged.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: accepted/compensated/quarantined/in-progress/partial; superseded/rolled-back states not modeled

- [~] **GAP04-C08-007** — Classify conflicts by object/resource type, operation semantics, policy version, authority epoch, causal order, and whether side effects are reversible.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: conflict = authoritative write on same subject after partition start; no per-type classes

- [~] **GAP04-C08-008** — Specify authoritative resolution rules for every conflict class; prohibit ad-hoc last-write-wins where safety or integrity constraints require stronger semantics.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: one rule for all classes (authoritative wins) documented in ADR-005

- [-] **GAP04-C08-009** — Support deterministic merge functions only where operations are mathematically/semantically mergeable; version and test every merge rule.
  - Note: N/A proposed: no merge functions are offered; approval pending

- [~] **GAP04-C08-010** — Define rollback/compensation operations with explicit preconditions, idempotency keys, audit records, and failure escalation.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: idempotent compensation via GAP-01; no preconditions

- [~] **GAP04-C08-011** — Define quarantine for conflicts that cannot be safely auto-resolved; quarantined objects must not silently re-enter normal operation.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: quarantined outcome recorded; later re-entry of the subject is not blocked

- [x] **GAP04-C08-012** — Reconcile authenticated revocation and policy updates before granting any new lease after reconnect.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [x] **GAP04-C08-013** — Batch decisions with bounded size, stable ordering, checkpoints, resumable progress, and partial-failure isolation.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [~] **GAP04-C08-014** — Implement acknowledgement protocol carrying decision IDs, remote result, authoritative version/vector/epoch, and durable high-watermark.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: per-batch ack digest; no authoritative version/vector/epoch in ack

- [x] **GAP04-C08-015** — Persist reconciliation progress transactionally so a crash cannot forget a remote commit or double-apply a compensation.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [~] **GAP04-C08-016** — Add tests for divergent concurrent edits, stale policy decisions, stale authority generations, partial batches, lost ACKs, reorder, duplicate delivery, remote timeout, and permanent remote rejection.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: partial batches, duplicates, conflicts, peer failure tested; lost-ACK partially

- [~] **GAP04-C08-017** — Add invariant/property tests showing reconciliation converges to a valid authoritative state under repeated retries.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: flapping fault test exercises repeated reconnects; no formal convergence property

- [~] **GAP04-C08-018** — Expose backlog, oldest pending age, conflict counts by class, retry counts, quarantine count, throughput, and last successful watermark.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: outcome/conflict metrics; backlog/oldest age not

- [ ] **GAP04-C08-019** — Provide operator inspection/replay tools that cannot bypass authorization or erase forensic history.
  - Note: not started: operator inspection/replay tool

- [~] **GAP04-C08-020** — Production gate: demonstrate deterministic, idempotent recovery from a multi-hour partition with conflicts, lost acknowledgements, process crashes, and repeated reconnects.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: multi-day logical soak + crash suite; not a real multi-hour partition


### Component acceptance evidence

- [~] **GAP04-C08-021** — An approved design/ADR exists for **Real reconciliation engine** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C08-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [~] **GAP04-C08-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C08-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C08-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation`

- [~] **GAP04-C08-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`, `tests/test_p0_reconcile_adapters.py::Reconciliation` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (8 verified / 15 partial / 1 blocked / 1 not started / 1 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/node.py:reconnect`, `runtime/node.py:_resolve_conflict`, `runtime/adapters.py:ReferenceReplication`
- **Remaining gap:** Authoritative-wins with compensate/quarantine; no merge functions, operator replay tool or vector clocks.


---


## 09. State-replication adapter (GAP-05)

**Priority:** P0  
**Control family:** Integration  

### Checklist

- [~] **GAP04-C09-001** — Publish a versioned adapter contract with explicit timeouts, retries, cancellation, error mapping, authentication, and compatibility rules.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Real GAP-05 not available (W-002); interface is submit-only. · Waiver(s): W-002

- [x] **GAP04-C09-002** — Validate peer identity, trust domain, schema/protocol version, and message scope before consuming data or issuing commands.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C09-003** — Bound adapter queues/concurrency and isolate dependency failure with circuit breaking/backpressure.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C09-004** — Propagate correlation/trace context and expose dependency health/latency/error metrics.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Real GAP-05 not available (W-002); interface is submit-only. · Waiver(s): W-002

- [!] **GAP04-C09-005** — Qualify against real adjacent-component versions represented in the approved compatibility matrix.
  - Note: blocked; Real GAP-05 not available (W-002); interface is submit-only. · Waiver(s): W-002

- [~] **GAP04-C09-006** — Define a versioned adapter interface to GAP-05 for reading authoritative state, publishing local deltas, receiving remote versions, and acquiring reconciliation metadata.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: submit/ack only; no authoritative read API · Waiver(s): W-002

- [x] **GAP04-C09-007** — Map GAP-04 decision IDs, partition epochs, controller generations, policy hashes, and authority epochs into the replication protocol.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C09-008** — Define consistency guarantees required by each operation: strong, causal, monotonic-read, read-your-writes, eventual, or explicitly offline-local.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented as eventual + authoritative-wins only · Waiver(s): W-002

- [~] **GAP04-C09-009** — Reject replicated state whose schema/protocol version, trust domain, tenant/site identity, or integrity metadata is incompatible.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: contract version negotiated; trust domain/tenant integrity metadata not checked · Waiver(s): W-002

- [ ] **GAP04-C09-010** — Handle replication lag and stale reads explicitly; expose staleness bounds to the policy decision path.
  - Note: not started · Waiver(s): W-002

- [ ] **GAP04-C09-011** — Define causal/version-vector or sequence semantics used to detect concurrent updates and feed the reconciliation classifier.
  - Note: not started: version vectors · Waiver(s): W-002

- [x] **GAP04-C09-012** — Ensure replication callbacks cannot mutate GAP-04 state without passing validation, authentication, and transactional persistence boundaries.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C09-013** — Implement bounded retry, backoff, circuit breaking, queue limits, and cancellation behavior for the adapter.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [!] **GAP04-C09-014** — Add integration tests using real GAP-05 fixtures for normal replication, stale state, divergent versions, duplicate deltas, reordering, corruption, and failover.
  - Note: blocked: no real GAP-05 fixtures (W-002) · Waiver(s): W-002

- [!] **GAP04-C09-015** — Add mixed-version tests covering supported GAP-04/GAP-05 combinations and explicit rejection outside the matrix.
  - Note: blocked: no GAP-05 versions (W-002) · Waiver(s): W-002

- [x] **GAP04-C09-016** — Propagate trace context and stable correlation IDs across the adapter.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C09-017** — Expose replication availability, remote watermark, local lag, last error, protocol version, and queue depth through health/metrics.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: breaker state in health; watermark/lag not · Waiver(s): W-002

- [ ] **GAP04-C09-018** — Document bootstrap/resync semantics for a node with empty or corrupt replicated state.
  - Note: not started · Waiver(s): W-002

- [~] **GAP04-C09-019** — Define security requirements for transport authentication, message integrity, authorization, and tenant/site isolation.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in MASTER §7; transport is external · Waiver(s): W-002

- [x] **GAP04-C09-020** — Production gate: GAP-04 must make no claim of authoritative convergence without verified GAP-05 state and explicit compatibility evidence.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002


### Component acceptance evidence

- [~] **GAP04-C09-021** — An approved design/ADR exists for **State-replication adapter (GAP-05)** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001, W-002

- [x] **GAP04-C09-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C09-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-002, W-007

- [!] **GAP04-C09-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-002, W-009

- [x] **GAP04-C09-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C09-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`, `tests/test_p0_reconcile_adapters.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001, W-002


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-007, W-009
- **Status:** Blocked (9 verified / 10 partial / 4 blocked / 3 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/adapters.py:ReferenceReplication`, `runtime/node.py:_submit_with_retry`
- **Remaining gap:** Real GAP-05 not available (W-002); interface is submit-only.


---


## 10. WAN/reachability adapter (GAP-12)

**Priority:** P0  
**Control family:** Integration  

### Checklist

- [~] **GAP04-C10-001** — Publish a versioned adapter contract with explicit timeouts, retries, cancellation, error mapping, authentication, and compatibility rules.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Single authenticated signal; network-layer sources belong to GAP-12. · Waiver(s): W-002

- [x] **GAP04-C10-002** — Validate peer identity, trust domain, schema/protocol version, and message scope before consuming data or issuing commands.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C10-003** — Bound adapter queues/concurrency and isolate dependency failure with circuit breaking/backpressure.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C10-004** — Propagate correlation/trace context and expose dependency health/latency/error metrics.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Single authenticated signal; network-layer sources belong to GAP-12. · Waiver(s): W-002

- [!] **GAP04-C10-005** — Qualify against real adjacent-component versions represented in the approved compatibility matrix.
  - Note: blocked; Single authenticated signal; network-layer sources belong to GAP-12. · Waiver(s): W-002

- [~] **GAP04-C10-006** — Define authenticated reachability states beyond boolean connected/disconnected: healthy, degraded, asymmetric, captive/filtered, flapping, unknown, and partitioned.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: unknown/up/degraded/down/flapping; asymmetric/captive not distinct · Waiver(s): W-002

- [ ] **GAP04-C10-007** — Use multiple independent signals where appropriate (control-plane heartbeat, authenticated application probe, route/interface state, DNS/service resolution) rather than unauthenticated ICMP alone.
  - Note: not started: single signal · Waiver(s): W-002

- [x] **GAP04-C10-008** — Require authenticated challenge/response or equivalent for authority/service reachability so spoofed packets cannot falsely exit partition mode.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C10-009** — Implement hysteresis, debounce, minimum dwell times, and transition thresholds to prevent rapid mode oscillation under link flapping.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C10-010** — Distinguish network reachability from successful authority synchronization; connected mode is not safe until required revocation/policy/reconciliation steps complete.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C10-011** — Model asymmetric reachability and half-open sessions; inability to receive acknowledgements must not be treated as healthy connectivity.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: asymmetric case surfaces as reconciliation failure (tested) · Waiver(s): W-002

- [~] **GAP04-C10-012** — Bound probe rate and retry budgets to avoid self-induced WAN congestion during large-site reconnect storms.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: probe rate is caller-driven · Waiver(s): W-002

- [!] **GAP04-C10-013** — Handle stale DNS, resolver poisoning indicators, IP changes, proxy transitions, VPN changes, and multi-homing deterministically.
  - Note: blocked: DNS/IP/VPN handling is GAP-12's · Waiver(s): W-002

- [~] **GAP04-C10-014** — Add fault-injection tests for packet loss, latency, jitter, reordering, NAT rebinding, DNS failure, TLS failure, asymmetric path, captive portal, and intermittent success.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: loss/latency/flap/spoof tested; DNS/TLS/NAT not · Waiver(s): W-002

- [~] **GAP04-C10-015** — Expose raw signals and derived connectivity state separately for debugging while policy consumes only the authenticated derived state.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: only derived state exposed · Waiver(s): W-002

- [~] **GAP04-C10-016** — Audit connectivity state transitions with cause, previous/new state, confidence/source, and partition epoch.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: partition entry logged; not every transition · Waiver(s): W-002

- [~] **GAP04-C10-017** — Propagate trace/correlation identifiers for connectivity diagnostics without logging credentials.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: no probe tracing · Waiver(s): W-002

- [x] **GAP04-C10-018** — Define adapter version negotiation and explicit unsupported-state behavior.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C10-019** — Document platform-specific network event sources and privilege requirements.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in MASTER · Waiver(s): W-002

- [x] **GAP04-C10-020** — Production gate: an attacker or flaky network must not be able to cause premature reconnect/renewal or conceal a true partition.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002


### Component acceptance evidence

- [~] **GAP04-C10-021** — An approved design/ADR exists for **WAN/reachability adapter (GAP-12)** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001, W-002

- [x] **GAP04-C10-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C10-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-002, W-007

- [!] **GAP04-C10-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-002, W-009

- [x] **GAP04-C10-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C10-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/adapters.py:ReachabilityMonitor`, `tests/test_p0_reconcile_adapters.py::Reachability`, `tests/test_p1_resilience_suites.py::FaultInjection`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001, W-002


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-007, W-009
- **Status:** Blocked (9 verified / 13 partial / 3 blocked / 1 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/adapters.py:ReachabilityMonitor`
- **Remaining gap:** Single authenticated signal; network-layer sources belong to GAP-12.


---


## 11. Policy-engine adapter (GAP-13)

**Priority:** P0  
**Control family:** Integration  

### Checklist

- [~] **GAP04-C11-001** — Publish a versioned adapter contract with explicit timeouts, retries, cancellation, error mapping, authentication, and compatibility rules.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Reference evaluator only; no decision cache. · Waiver(s): W-002

- [x] **GAP04-C11-002** — Validate peer identity, trust domain, schema/protocol version, and message scope before consuming data or issuing commands.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C11-003** — Bound adapter queues/concurrency and isolate dependency failure with circuit breaking/backpressure.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C11-004** — Propagate correlation/trace context and expose dependency health/latency/error metrics.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Reference evaluator only; no decision cache. · Waiver(s): W-002

- [!] **GAP04-C11-005** — Qualify against real adjacent-component versions represented in the approved compatibility matrix.
  - Note: blocked; Reference evaluator only; no decision cache. · Waiver(s): W-002

- [~] **GAP04-C11-006** — Define a versioned request/response contract carrying subject, resource, operation, environment, lease fingerprint, authority epoch, partition epoch, policy digest, and relevant replicated-state version.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: evaluate(policy, kind, subject, tier); lease fingerprint/epochs not passed · Waiver(s): W-002

- [~] **GAP04-C11-007** — Validate and normalize all policy inputs before evaluation; reject unknown fields, malformed identifiers, unsupported actions, and missing mandatory context.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: kind/subject bounded; no full normalization · Waiver(s): W-002

- [x] **GAP04-C11-008** — Ensure policy evaluation is deterministic for the same canonical input and policy version where the policy language promises determinism.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [-] **GAP04-C11-009** — Cache only decisions explicitly marked cacheable and bind cache entries to policy digest, authority epoch, subject/resource scope, and expiry.
  - Note: N/A proposed: no decision caching · Waiver(s): W-002

- [-] **GAP04-C11-010** — Invalidate cached decisions on policy change, revocation generation change, identity change, privilege change, or clock-trust degradation.
  - Note: N/A proposed: no decision caching · Waiver(s): W-002

- [~] **GAP04-C11-011** — Expose policy engine unavailability distinctly from explicit deny; production behavior must fail closed for operations requiring authoritative evaluation.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: engine exceptions surface as coded errors; unavailability not a distinct code · Waiver(s): W-002

- [x] **GAP04-C11-012** — Define policy staleness bounds and prevent stale policy from being refreshed merely by process restart.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C11-013** — Protect adapter transport and policy context with mutual authentication and least-privilege authorization.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: in-process; mTLS helpers provided · Waiver(s): W-002

- [~] **GAP04-C11-014** — Add integration tests for allow, deny, error, timeout, stale cache, policy upgrade, revocation, malformed result, version skew, and engine failover.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: allow/deny/stale/upgrade tested; timeout/malformed/failover not · Waiver(s): W-002

- [!] **GAP04-C11-015** — Add differential tests against authoritative policy fixtures to detect semantic drift between offline/local evaluator and central engine.
  - Note: blocked: needs authoritative GAP-13 fixtures (W-002) · Waiver(s): W-002

- [x] **GAP04-C11-016** — Record policy decision reason codes and matched rule identifiers in audit records without leaking policy secrets.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C11-017** — Expose evaluator version, active policy digest, cache hit/miss, evaluation latency, error rate, and staleness via telemetry.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: version/age in health; latency/cache metrics not · Waiver(s): W-002

- [~] **GAP04-C11-018** — Define bounded concurrency, timeout, cancellation, and circuit-breaker behavior.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: breaker only; no timeouts/cancellation · Waiver(s): W-002

- [~] **GAP04-C11-019** — Document supported policy-language/compiler/runtime versions.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented as reference only · Waiver(s): W-002

- [x] **GAP04-C11-020** — Production gate: every offline authorization must be reproducibly attributable to a verified policy version and validated decision context.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002


### Component acceptance evidence

- [~] **GAP04-C11-021** — An approved design/ADR exists for **Policy-engine adapter (GAP-13)** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001, W-002

- [x] **GAP04-C11-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C11-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-002, W-007

- [!] **GAP04-C11-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-002, W-009

- [x] **GAP04-C11-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C11-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`, `tests/test_p0_reconcile_adapters.py::Policy`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001, W-002


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-007, W-009
- **Status:** Blocked (8 verified / 13 partial / 3 blocked / 0 not started / 2 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/adapters.py:ReferencePolicyEngine`, `runtime/node.py:_decide`
- **Remaining gap:** Reference evaluator only; no decision cache.


---


## 12. Security-plane/capability adapter (PLN-07)

**Priority:** P0  
**Control family:** Integration  

### Checklist

- [~] **GAP04-C12-001** — Publish a versioned adapter contract with explicit timeouts, retries, cancellation, error mapping, authentication, and compatibility rules.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Signed grants with epoch revocation; no resource scope/delegation. · Waiver(s): W-002

- [x] **GAP04-C12-002** — Validate peer identity, trust domain, schema/protocol version, and message scope before consuming data or issuing commands.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C12-003** — Bound adapter queues/concurrency and isolate dependency failure with circuit breaking/backpressure.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C12-004** — Propagate correlation/trace context and expose dependency health/latency/error metrics.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Signed grants with epoch revocation; no resource scope/delegation. · Waiver(s): W-002

- [!] **GAP04-C12-005** — Qualify against real adjacent-component versions represented in the approved compatibility matrix.
  - Note: blocked; Signed grants with epoch revocation; no resource scope/delegation. · Waiver(s): W-002

- [~] **GAP04-C12-006** — Define an authenticated adapter contract for identity assertions, capability grants, revocation status, issuer trust, and delegation constraints.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: grant/revocation contract; delegation constraints absent · Waiver(s): W-002

- [~] **GAP04-C12-007** — Represent capabilities with explicit subject, resource scope, operations, constraints, expiry, issuer, authority epoch, delegation depth, and proof/signature reference.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: subject/caps/epoch/expiry/issuer; no resource scope or delegation depth · Waiver(s): W-002

- [x] **GAP04-C12-008** — Enforce least privilege and deny unknown/ambiguous capabilities; wildcard privileges must be explicitly bounded and reviewed.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [x] **GAP04-C12-009** — Verify issuer trust and revocation before accepting or caching a capability grant.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C12-010** — Bind cached capability state to device/site identity, policy digest, and authority generation.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: bound to site + epoch; not policy digest · Waiver(s): W-002

- [x] **GAP04-C12-011** — Define behavior when security-plane state is unavailable, stale, partially synchronized, or internally inconsistent.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C12-012** — Prevent confused-deputy behavior by preserving original caller identity and authorization context across supervisor/replication calls.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: grant id recorded on decision; caller identity not forwarded to supervisor · Waiver(s): W-002

- [~] **GAP04-C12-013** — Add tests for forged grants, stale grants, revoked issuers, wrong tenant/site, scope escalation, delegation loops, malformed constraints, and replay.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: forged, wrong-site, stale-epoch tested; delegation N/A · Waiver(s): W-002

- [!] **GAP04-C12-014** — Add mixed-version compatibility tests with PLN-07 schemas and signer/key formats.
  - Note: blocked: no PLN-07 versions (W-002) · Waiver(s): W-002

- [x] **GAP04-C12-015** — Propagate stable security decision reason codes into GAP-04 machine-readable errors and audit events.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [ ] **GAP04-C12-016** — Expose grant freshness, revocation freshness, signer/trust status, and adapter health without disclosing secrets.
  - Note: not started · Waiver(s): W-002

- [~] **GAP04-C12-017** — Protect transport using mTLS/workload identity or equivalent and pin expected peer identity/trust domain.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: mTLS helpers; adapter in-process · Waiver(s): W-002

- [x] **GAP04-C12-018** — Define secure cache persistence and rollback protection if capability state survives restart.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: grants are not persisted across restart by design (re-fetched) · Waiver(s): W-002

- [~] **GAP04-C12-019** — Document emergency revocation semantics and expected propagation SLO.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in RUNBOOK RB-07 · Waiver(s): W-002

- [x] **GAP04-C12-020** — Production gate: no local action can exceed the authenticated capability envelope in force for that subject at the accepted authority epoch.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002


### Component acceptance evidence

- [~] **GAP04-C12-021** — An approved design/ADR exists for **Security-plane/capability adapter (PLN-07)** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001, W-002

- [x] **GAP04-C12-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C12-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-002, W-007

- [!] **GAP04-C12-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-002, W-009

- [x] **GAP04-C12-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002

- [~] **GAP04-C12-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/adapters.py:CapabilityPlane`, `tests/test_p0_reconcile_adapters.py::Capabilities`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001, W-002


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-007, W-009
- **Status:** Blocked (10 verified / 12 partial / 3 blocked / 1 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/adapters.py:CapabilityPlane`
- **Remaining gap:** Signed grants with epoch revocation; no resource scope/delegation.


---


## 13. Edge-supervisor adapter (GAP-01)

**Priority:** P0  
**Control family:** Integration  

### Checklist

- [~] **GAP04-C13-001** — Publish a versioned adapter contract with explicit timeouts, retries, cancellation, error mapping, authentication, and compatibility rules.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: partially implemented; Synchronous reference supervisor; no async operations or response integrity. · Waiver(s): W-002

- [x] **GAP04-C13-002** — Validate peer identity, trust domain, schema/protocol version, and message scope before consuming data or issuing commands.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [x] **GAP04-C13-003** — Bound adapter queues/concurrency and isolate dependency failure with circuit breaking/backpressure.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [~] **GAP04-C13-004** — Propagate correlation/trace context and expose dependency health/latency/error metrics.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: partially implemented; Synchronous reference supervisor; no async operations or response integrity. · Waiver(s): W-002

- [!] **GAP04-C13-005** — Qualify against real adjacent-component versions represented in the approved compatibility matrix.
  - Note: blocked; Synchronous reference supervisor; no async operations or response integrity. · Waiver(s): W-002

- [~] **GAP04-C13-006** — Define a versioned command contract for start/stop/restart/admit/evict/freeze/quarantine/resource-change operations with idempotency key and decision ID.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: 5 action kinds; freeze/quarantine operations not in contract · Waiver(s): W-002

- [x] **GAP04-C13-007** — Map every GAP-04 policy action to an explicit supervisor operation or explicit unsupported result; no implicit fall-through.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [~] **GAP04-C13-008** — Require supervisor authentication and authorization; verify the peer identity before issuing lifecycle commands.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: in-process; mTLS helpers · Waiver(s): W-002

- [x] **GAP04-C13-009** — Persist the intended supervisor side effect before issuing it and persist the returned result/operation handle after completion.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [ ] **GAP04-C13-010** — Handle asynchronous supervisor operations with stable operation IDs, polling/subscription, timeout, cancellation, and crash recovery.
  - Note: not started: async operations · Waiver(s): W-002

- [~] **GAP04-C13-011** — Never assume timeout means failure; query operation status using the original idempotency key before retrying.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: failures recorded durably; status query by key not implemented · Waiver(s): W-002

- [~] **GAP04-C13-012** — Define precondition checks using workload generation/version to prevent stale commands from changing a newer workload incarnation.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: fencing generation only; no workload generation precondition · Waiver(s): W-002

- [~] **GAP04-C13-013** — Add integration tests for duplicate commands, delayed completion, process restart, supervisor failover, partial failure, stale generation, permission denial, and unsupported action.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: duplicates, stale generation, failure tested; failover/delay not · Waiver(s): W-002

- [x] **GAP04-C13-014** — Map supervisor failures to machine-readable GAP-04 error codes and reconciliation states.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [x] **GAP04-C13-015** — Propagate trace context and audit correlation IDs across the boundary.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [~] **GAP04-C13-016** — Expose supervisor reachability, queue depth, command latency, failure rate, and last successful interaction.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: breaker state only · Waiver(s): W-002

- [~] **GAP04-C13-017** — Bound concurrency and implement backpressure so reconnect storms cannot overload the supervisor.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: admission bounds decide(); compensation not bounded · Waiver(s): W-002

- [x] **GAP04-C13-018** — Document exactly which local actions are reversible and define compensation for each reversible operation.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [ ] **GAP04-C13-019** — Verify supervisor responses are integrity-protected and belong to the expected request/operation ID.
  - Note: not started: response integrity · Waiver(s): W-002

- [x] **GAP04-C13-020** — Production gate: each accepted GAP-04 decision must have a durable, idempotent, attributable supervisor effect or a durable, explicit failure state.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002


### Component acceptance evidence

- [~] **GAP04-C13-021** — An approved design/ADR exists for **Edge-supervisor adapter (GAP-01)** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001, W-002

- [x] **GAP04-C13-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [~] **GAP04-C13-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-002, W-007

- [!] **GAP04-C13-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-002, W-009

- [x] **GAP04-C13-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Waiver(s): W-002

- [~] **GAP04-C13-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`, `tests/test_p0_reconcile_adapters.py::Supervisor` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001, W-002


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-007, W-009
- **Status:** In progress (10 verified / 12 partial / 2 blocked / 2 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/adapters.py:ReferenceSupervisor`, `runtime/node.py:_execute`, `runtime/node.py:resume_effects`
- **Remaining gap:** Synchronous reference supervisor; no async operations or response integrity.


---


## 14. Authentication and authorization for every external boundary

**Priority:** P0  
**Control family:** Security  

### Checklist

- [x] **GAP04-C14-001** — Maintain a boundary/identity/data-flow threat model and explicit trust-domain map.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [x] **GAP04-C14-002** — Use deny-by-default authorization and least-privilege service/operator identities.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [x] **GAP04-C14-003** — Version security-sensitive protocols and reject downgrade/unknown modes.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [~] **GAP04-C14-004** — Audit all security decisions with stable reason codes while redacting credentials/secrets.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: partially implemented; Deny-by-default SPIFFE authz; PKI lifecycle and IPC hardening external.

- [~] **GAP04-C14-005** — Run recurring adversarial tests and dependency/credential lifecycle review.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: partially implemented; Deny-by-default SPIFFE authz; PKI lifecycle and IPC hardening external.

- [x] **GAP04-C14-006** — Inventory every inbound/outbound boundary: policy engine, security plane, supervisor, replication, WAN probes, reconciliation service, telemetry sink, operator API, storage/key services, and local IPC.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [x] **GAP04-C14-007** — Assign an identity mechanism to each boundary (mTLS SPIFFE/SVID, device certificate, workload token, OS peer credentials, TPM attestation, or documented equivalent).
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [~] **GAP04-C14-008** — Define trust domains, accepted issuers/CAs, certificate/key lifetimes, rotation process, and revocation checking.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: trust domain enforced; certificate lifetimes/rotation are PKI's

- [x] **GAP04-C14-009** — Authorize every operation using explicit least-privilege roles/capabilities; authenticated identity alone must never imply permission.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [~] **GAP04-C14-010** — Enforce tenant/site/node scoping on every request and response to prevent confused-deputy and cross-tenant access.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: site scoping in envelopes; per-request tenant scoping not

- [~] **GAP04-C14-011** — Reject anonymous, expired, not-yet-valid, revoked, wrong-audience, wrong-issuer, and wrong-trust-domain credentials.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: TLS stack enforces validity; only identity parsing tested

- [~] **GAP04-C14-012** — Protect local IPC against untrusted same-host processes using OS ACLs, namespaces, service SIDs, peer credential checks, or equivalent.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: files 0600; no IPC surface

- [x] **GAP04-C14-013** — Pin protocol versions/cipher suites and disable insecure renegotiation/downgrade paths.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [x] **GAP04-C14-014** — Define credential bootstrap/rotation with no long-lived secret embedded in source, image, configuration, or logs.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [~] **GAP04-C14-015** — Add authorization tests for every endpoint/action, including negative tests for privilege escalation and scope crossover.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: several boundaries tested, not all 14

- [ ] **GAP04-C14-016** — Add mTLS/token replay, certificate substitution, stale credential, revoked credential, and trust-store rollback tests.
  - Note: not started: needs PKI fixtures

- [~] **GAP04-C14-017** — Audit authentication failures and authorization denials using redacted stable identities and reason codes.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: decide denials logged with code; not every boundary

- [ ] **GAP04-C14-018** — Rate-limit and back off repeated authentication failures to mitigate resource exhaustion without hiding attacks.
  - Note: not started

- [~] **GAP04-C14-019** — Document break-glass access with time bounds, approval, explicit scope, and mandatory post-event review.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: break-glass = overrides (RUNBOOK RB-08)

- [~] **GAP04-C14-020** — Production gate: every external request is mutually attributable, integrity protected where required, and denied unless explicitly authorized.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: partial until every boundary is covered


### Component acceptance evidence

- [~] **GAP04-C14-021** — An approved design/ADR exists for **Authentication and authorization for every external boundary** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C14-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [~] **GAP04-C14-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C14-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C14-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs`

- [~] **GAP04-C14-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/authz.py`, `runtime/opsapi.py`, `tests/test_p0_reconcile_adapters.py::Authz`, `tests/test_p1_operations.py::HealthMetricsLogs` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (10 verified / 13 partial / 1 blocked / 2 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/authz.py`, `runtime/opsapi.py`
- **Remaining gap:** Deny-by-default SPIFFE authz; PKI lifecycle and IPC hardening external.


---


## 15. Encrypted persistent state and managed keys

**Priority:** P0  
**Control family:** Crypto Storage  

### Checklist

- [x] **GAP04-C15-001** — Document protected data classes, key hierarchy, hardware trust assumptions, and recovery/compromise model.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [x] **GAP04-C15-002** — Version encrypted record formats including algorithm and key identifiers without permitting unsafe algorithm agility.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [x] **GAP04-C15-003** — Fail closed on integrity/authentication failure and avoid automatic destructive recovery.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [ ] **GAP04-C15-004** — Instrument key-store/encryption health without exposing key material.
  - Note: not started in 4.3.0; Keys beside data in the reference provider (W-005).

- [~] **GAP04-C15-005** — Include key rotation, backup/restore, device replacement, and compromise tests in release qualification.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: partially implemented; Keys beside data in the reference provider (W-005).

- [x] **GAP04-C15-006** — Inventory all persistent sensitive data: leases, policies, journal, audit chain, identity material, cached grants, configuration, reconciliation state, backups, and temporary files.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [x] **GAP04-C15-007** — Classify each data set and define encryption-at-rest requirements, key scope, retention, and permitted plaintext exposure.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [x] **GAP04-C15-008** — Use authenticated encryption with approved algorithms/modes; reject unauthenticated encryption and home-grown cryptography.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [~] **GAP04-C15-009** — Generate data-encryption keys from a managed KMS/HSM/TPM/secure-element or OS-protected key hierarchy with explicit trust assumptions.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: os.urandom keys in 0600 file; TPM/KMS seam only · Waiver(s): W-005

- [ ] **GAP04-C15-010** — Separate key-encryption keys from data-encryption keys and rotate without rewriting unrelated security domains where possible.
  - Note: not started: KEK/DEK separation · Waiver(s): W-005

- [~] **GAP04-C15-011** — Bind encrypted state to device/site/context metadata as associated data to detect ciphertext transplantation.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: AAD binds seq + key id; site not bound

- [~] **GAP04-C15-012** — Define secure bootstrap and recovery when hardware-bound keys are unavailable, replaced, or intentionally re-provisioned.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: documented

- [~] **GAP04-C15-013** — Zeroize plaintext key material and sensitive buffers where the runtime/platform permits; prevent keys from appearing in logs, crash dumps, telemetry, or command lines.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: best-effort zeroization (CPython limits)

- [~] **GAP04-C15-014** — Protect temporary files, swap/pagefile exposure, core dumps, and backup copies according to the same data classification.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: backups encrypted; swap/core-dump controls not

- [~] **GAP04-C15-015** — Add tests for wrong key, revoked key, rotated key, corrupted ciphertext/tag, truncated file, key-store outage, restored backup, and device replacement.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: wrong key, rotation, corrupted tag, backup tested

- [x] **GAP04-C15-016** — Define key-version metadata and migration so older encrypted records remain decryptable only for the approved retention window.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [ ] **GAP04-C15-017** — Expose encryption/key-health status without exposing key material.
  - Note: not started

- [~] **GAP04-C15-018** — Document key compromise response, forced rotation, re-encryption, certificate replacement, and forensic preservation.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: documented in RUNBOOK RB-07/09

- [x] **GAP04-C15-019** — Verify backup/restore tooling preserves encryption guarantees and does not export plaintext by default.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [~] **GAP04-C15-020** — Production gate: loss or theft of persistent storage alone must not reveal protected controller state or permit undetected modification.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: fails while keys sit beside data (W-005) · Waiver(s): W-005


### Component acceptance evidence

- [~] **GAP04-C15-021** — An approved design/ADR exists for **Encrypted persistent state and managed keys** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C15-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [~] **GAP04-C15-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C15-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C15-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys`

- [~] **GAP04-C15-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`, `tests/test_p0_durability.py::EncryptionKeys` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-005, W-007, W-009
- **Status:** In progress (10 verified / 12 partial / 1 blocked / 3 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/storage.py:Keyring`, `runtime/crypto.py`, `runtime/backup.py`
- **Remaining gap:** Keys beside data in the reference provider (W-005).


---


## 16. Split-brain fencing / single-authority ownership

**Priority:** P0  
**Control family:** Distributed  

### Checklist

- [x] **GAP04-C16-001** — Define distributed-system safety invariants, authority source, network partition assumptions, and recovery semantics.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-002** — Version fencing/ownership messages and bind them to authenticated identity and persistent generations.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: partially implemented; Single-host fencing only (W-011).

- [x] **GAP04-C16-003** — Make stale-owner rejection enforceable at every side-effect boundary that can honor fencing.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-004** — Expose ownership/generation/lock state with critical alerts on ambiguity.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: partially implemented; Single-host fencing only (W-011).

- [~] **GAP04-C16-005** — Test split-brain, delayed messages, failover, duplicated images, and partial network partitions.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: partially implemented; Single-host fencing only (W-011).

- [~] **GAP04-C16-006** — Define the ownership model: exactly one active controller per site/node/shard or an explicitly coordinated multi-active protocol with proven safety.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: one active per state directory; documented

- [~] **GAP04-C16-007** — Assign a monotonic controller generation/fencing token issued by an authority that cannot move backward.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: local persisted generation, not authority-issued · Waiver(s): W-011

- [~] **GAP04-C16-008** — Require every supervisor, replication, reconciliation, and durable-state mutation to carry the current fencing token where the adjacent subsystem supports fencing.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: journal + supervisor carry generation; reference GAP-05 does not check it

- [x] **GAP04-C16-009** — Reject commands and writes from a controller generation older than the highest accepted generation.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-010** — Detect duplicate active instances through lease/lock/consensus membership or an equivalent mechanism; local PID files alone are insufficient for distributed ownership.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: OS lock only · Waiver(s): W-011

- [~] **GAP04-C16-011** — Define takeover protocol: acquire new generation, quiesce old authority, validate durable state, reconcile outstanding work, then enable actions.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: acquire → recover → resume effects; no quiesce of old authority

- [ ] **GAP04-C16-012** — Ensure network partition between two controller instances cannot allow both to perform unrestricted conflicting actions.
  - Note: not started: two hosts · Waiver(s): W-011

- [x] **GAP04-C16-013** — Persist ownership/generation state crash-consistently and bind it to site/node identity.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-014** — Add tests for simultaneous startup, stale process resume, VM clone, network split, authority-service failover, lock loss, delayed packets from old owner, and duplicate disk image.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: simultaneous start (subprocess) + stale gen; VM clone not

- [~] **GAP04-C16-015** — Audit ownership acquisition/loss with prior/new generation, actor, reason, and peer observations.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: open logs generation

- [~] **GAP04-C16-016** — Expose active generation, ownership state, lease/lock expiry, and duplicate-owner detection as health/metrics.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: generation in health

- [ ] **GAP04-C16-017** — Define emergency recovery from a permanently lost owner without re-enabling stale generations.
  - Note: not started

- [~] **GAP04-C16-018** — Document dependencies on consensus/lock service availability and fail-safe behavior when fencing cannot be verified.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: documented

- [x] **GAP04-C16-019** — Ensure operator override cannot bypass fencing silently.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-020** — Production gate: an old or duplicated controller instance must be unable to mutate authoritative state after a newer generation has taken ownership.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: single host only (W-011) · Waiver(s): W-011


### Component acceptance evidence

- [~] **GAP04-C16-021** — An approved design/ADR exists for **Split-brain fencing / single-authority ownership** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C16-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C16-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C16-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency`

- [~] **GAP04-C16-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/fencing.py`, `runtime/node.py:__init__`, `tests/test_p0_durability.py::Fencing`, `tests/test_p1_resilience_suites.py::Concurrency` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009, W-011
- **Status:** In progress (7 verified / 16 partial / 1 blocked / 2 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/fencing.py`, `runtime/node.py:__init__`
- **Remaining gap:** Single-host fencing only (W-011).


---


## 17. Persisted partition epoch and controller generation

**Priority:** P0  
**Control family:** Persistence  

### Checklist

- [x] **GAP04-C17-001** — Document durability guarantees, crash model, filesystem/database assumptions, integrity model, retention, and recovery invariants.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-002** — Version all on-disk formats and define forward migration, backward-read, and unsupported-version behavior.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: partially implemented; Software rollback resistance only.

- [x] **GAP04-C17-003** — Make writes bounded, checksummed/integrity-protected as appropriate, and safe under abrupt termination.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-004** — Expose durable sequence/checkpoint state and persistence failures through health, logs, metrics, and machine-readable errors.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: partially implemented; Software rollback resistance only.

- [!] **GAP04-C17-005** — Qualify on every supported storage/filesystem profile with deterministic fault injection.
  - Note: blocked; Software rollback resistance only.

- [x] **GAP04-C17-006** — Persist partition epoch and controller generation in durable integrity-protected state rather than initializing them solely in memory.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [x] **GAP04-C17-007** — Increment partition epoch atomically at the defined transition into a new disconnected episode and never reuse an earlier epoch for the same controller identity.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [x] **GAP04-C17-008** — Bind every offline decision, journal segment, audit event, reconciliation record, and lease evaluation to partition epoch and controller generation.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [x] **GAP04-C17-009** — Persist generation changes before enabling any side effects under the new controller instance.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-010** — Protect persisted epoch/generation from rollback using fencing authority, trusted monotonic storage, signed checkpoints, or a documented equivalent.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: journal MAC; no hardware monotonic storage (W-012) · Waiver(s): W-012

- [x] **GAP04-C17-011** — Define integer width, monotonicity, wraparound prohibition, serialization, and migration semantics.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [x] **GAP04-C17-012** — Detect missing/corrupt epoch state at startup and enter recovery/quarantine rather than silently resetting to zero.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-013** — Define behavior when durable state is restored from backup older than authority service state.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: restore bumps generation; older authority watermark relies on control plane

- [x] **GAP04-C17-014** — Add tests for crash between epoch increment and journal append, reboot during partition, snapshot rollback, duplicated storage, generation change, and migration from pre-persistence releases.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-015** — Include epoch/generation in all machine-readable errors related to stale/replayed requests.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: stale-generation errors carry both values; not every error

- [~] **GAP04-C17-016** — Expose persisted vs active values and last transition timestamp in diagnostics.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: values in health; last transition time not

- [x] **GAP04-C17-017** — Audit every increment and generation change with cause.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-018** — Define reconciliation rules for records created by an older controller generation but not yet acknowledged.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: older-generation records reconcile normally; documented

- [~] **GAP04-C17-019** — Document ownership of epoch allocation relative to GAP-12 connectivity events.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: documented in MASTER §5

- [~] **GAP04-C17-020** — Production gate: restarts and image rollback cannot cause an old partition or controller generation to be mistaken for a new trustworthy authority context.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: image rollback residual (R1)


### Component acceptance evidence

- [~] **GAP04-C17-021** — An approved design/ADR exists for **Persisted partition epoch and controller generation** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C17-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C17-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C17-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing`

- [~] **GAP04-C17-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`, `tests/test_p0_durability.py::Fencing` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009, W-012
- **Status:** In progress (12 verified / 12 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/node.py:_recover`, `controller.py:to_snapshot`, `runtime/fencing.py`
- **Remaining gap:** Software rollback resistance only.


---


## 18. Atomic lease/policy/journal state transaction model

**Priority:** P0  
**Control family:** Transactional  

### Checklist

- [x] **GAP04-C18-001** — Document the atomicity/isolation/durability invariants and the exact external side effects covered by each transaction.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-002** — Version durable records and ensure recovery code is compatible with all supported formats.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-003** — Instrument commit/recovery failures with stable error codes and safety readiness impact.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: partially implemented; Crash points cover every write type but not every byte offset; real I/O faults not injected.

- [x] **GAP04-C18-004** — Prohibit best-effort continuation after an uncertain commit for safety-critical state.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-005** — Qualify using exhaustive crash-point and I/O-fault injection around transaction boundaries.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: partially implemented; Crash points cover every write type but not every byte offset; real I/O faults not injected.

- [x] **GAP04-C18-006** — Define the exact safety transaction boundary spanning lease state, active policy digest/version, authority epoch, partition epoch, controller generation, journal append, and side-effect intent.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-007** — Choose a transaction mechanism appropriate to the persistence substrate: embedded transactional database, WAL with commit record, copy-on-write manifest, or equivalent.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-008** — Ensure no externally visible side effect occurs from a state combination that was never durably committed.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-009** — Use explicit transaction IDs and commit sequence numbers to correlate journal/audit/reconciliation state.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-010** — On startup, recover to the last complete committed transaction and deterministically roll forward or roll back incomplete work.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-011** — Prevent torn activation where a new policy is marked active but the corresponding lease/policy binding or rollback floor is not persisted.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-012** — Prevent decision acknowledgement before both authorization context and decision intent meet required durability.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-013** — Ensure compaction/checkpoint operations are themselves atomic and recoverable.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [x] **GAP04-C18-014** — Add injected-crash tests before/after every persistence write, fsync, rename, commit record, and side-effect dispatch.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-015** — Add ENOSPC, permission-loss, filesystem-read-only, corruption, I/O timeout, and key-unavailable tests.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: capacity exhaustion simulated; real ENOSPC/read-only fs/permission loss not

- [x] **GAP04-C18-016** — Define transaction isolation/concurrency semantics for simultaneous renewal, policy refresh, reconciliation, and operator override.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-017** — Expose current durable transaction sequence, recovery-required flag, and last commit failure.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: journal seq in health; recovery flag not

- [x] **GAP04-C18-018** — Audit recovery decisions without double-recording business actions.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-019** — Document filesystem/database durability assumptions per supported OS.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: POSIX assumptions documented; other OSes unqualified (W-008)

- [~] **GAP04-C18-020** — Production gate: exhaustive fault injection must not produce a state where lease, policy, epoch, journal, and performed side effect disagree about what was authorized.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: not exhaustive


### Component acceptance evidence

- [~] **GAP04-C18-021** — An approved design/ADR exists for **Atomic lease/policy/journal state transaction model** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C18-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C18-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C18-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py`

- [~] **GAP04-C18-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`, `tests/test_crash_recovery.py` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (16 verified / 9 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/node.py:_commit`, `runtime/journal.py`, `runtime/storage.py:atomic_write`
- **Remaining gap:** Crash points cover every write type but not every byte offset; real I/O faults not injected.


---


## 19. Machine-readable error model

**Priority:** P0  
**Control family:** Api  

### Checklist

- [x] **GAP04-C19-001** — Publish the contract as a versioned schema/specification and treat it as a compatibility surface.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-002** — Validate every boundary input and bound message size, nesting, string length, and collection count.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-003** — Use stable identifiers/correlation IDs and deterministic retry/idempotency semantics.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-004** — Instrument error frequency/latency without leaking sensitive details.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-005** — Maintain golden contract fixtures and client/server compatibility tests.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [~] **GAP04-C19-006** — Define a stable error envelope with error code, category, retryability, severity, operation, correlation ID, component, protocol/schema version, safe detail fields, and optional causal chain.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: code/category/retryable/http_status/details; no correlation id or severity

- [x] **GAP04-C19-007** — Allocate documented error namespaces for authorization, lease, policy, time, connectivity, storage, reconciliation, dependency, configuration, schema, overload, and internal faults.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-008** — Keep error codes stable across patch releases; changes to semantic meaning require versioning.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-009** — Separate safe machine-readable details from operator diagnostics so secrets, keys, tokens, policy contents, and tenant data do not leak.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [~] **GAP04-C19-010** — Map internal exceptions into stable boundary errors; never expose language/runtime exception class names as the API contract.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: decide() wraps all; some lifecycle paths can still raise reference-controller exceptions

- [x] **GAP04-C19-011** — Define HTTP/gRPC/IPC status mappings if those transports are used, including idempotent retry guidance.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [~] **GAP04-C19-012** — Distinguish transient/retriable from permanent failures and include safe retry-after/backoff metadata when appropriate.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: retryable flag; no retry-after

- [~] **GAP04-C19-013** — Include partition epoch/controller generation/decision ID in relevant errors so callers can detect stale responses.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: epoch/generation in selected details only

- [x] **GAP04-C19-014** — Add schema tests for every error variant and golden fixtures across supported versions.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-015** — Add negative tests for malformed requests, unsupported versions, dependency timeouts, auth failures, ENOSPC, stale epochs, and reconciliation conflicts.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-016** — Document operator-facing remediation for each production error code.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-017** — Emit metrics by stable error code, not raw exception text.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-018** — Ensure logs preserve internal diagnostic detail behind access controls while external responses remain sanitized.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [x] **GAP04-C19-019** — Define localization policy for human messages without changing machine codes.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [~] **GAP04-C19-020** — Production gate: every documented failure mode crossing a component boundary has a stable, test-covered, non-secret-bearing machine-readable representation.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: not every path wrapped


### Component acceptance evidence

- [~] **GAP04-C19-021** — An approved design/ADR exists for **Machine-readable error model** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C19-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [~] **GAP04-C19-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C19-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C19-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts`

- [~] **GAP04-C19-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/errors.py`, `docs/ERROR_CODES.md`, `tests/test_p0_lease_policy.py::ErrorModel`, `tests/test_p1_contracts_integration.py::Contracts` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (17 verified / 8 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/errors.py`, `docs/ERROR_CODES.md`
- **Remaining gap:** No correlation id/severity/retry-after fields.


---


## 20. Fail-safe storage exhaustion strategy

**Priority:** P0  
**Control family:** Resilience  

### Checklist

- [x] **GAP04-C20-001** — Define safety state transitions, resource budgets, overload/failure thresholds, and recovery prerequisites.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C20-002** — Make overload and resource-failure handling deterministic and bounded.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C20-003** — Prioritize safety-critical state/audit work over optional work.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C20-004** — Expose saturation/freeze state through health, metrics, alerts, and machine-readable errors.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-005** — Test resource exhaustion and dependency degradation at every relevant lifecycle state.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: partially implemented; Journal budget + reserve; other budgets (logs/tmp) external.

- [~] **GAP04-C20-006** — Define separate storage budgets for journal, audit, policy/cache state, reconciliation metadata, logs, temporary files, and diagnostic dumps.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: journal + reserve budgets; logs/tmp budgets external

- [x] **GAP04-C20-007** — Reserve protected emergency capacity that ordinary logs/cache/compaction cannot consume.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-008** — Set deterministic warning, critical, freeze, and recovery thresholds based on bytes and percentage with hysteresis.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: 80% warning + freeze; no hysteresis

- [x] **GAP04-C20-009** — Before accepting any offline action, verify that required durable journal and audit writes can complete; fail closed if safety evidence cannot be persisted.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C20-010** — Define eviction priority: discard reconstructible caches/logs before authoritative journal/audit records; never evict unreconciled decisions silently.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C20-011** — Implement bounded segment rotation and backpressure so producers cannot grow storage without limit.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [x] **GAP04-C20-012** — On critical exhaustion, freeze unsafe mutations, emit an auditable state transition, preserve enough capacity for recovery evidence, and surface operator alerts.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-013** — Handle filesystem read-only transitions, quota exhaustion, inode exhaustion, write latency spikes, and partial allocation failures.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: not qualified on quota/inode/RO fs

- [~] **GAP04-C20-014** — Add tests that fill disk at every persistence transition and verify no acknowledged decision lacks its required durable records.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: fill-to-exhaustion test; not at every transition

- [x] **GAP04-C20-015** — Verify recovery after space is freed: integrity scan, compaction/checkpoint, reconcile backlog, then explicitly exit freeze only when health criteria pass.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-016** — Expose free bytes, reserved bytes, journal utilization, audit utilization, write latency, compaction debt, and freeze threshold metrics.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: utilization/bytes; write latency/compaction debt not

- [ ] **GAP04-C20-017** — Protect reserved capacity permissions so other local processes cannot consume it trivially.
  - Note: not started

- [x] **GAP04-C20-018** — Document capacity planning formula based on maximum decision rate and maximum disconnected duration.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-019** — Define operator tooling for safe export/prune of eligible data with authentication and audit.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: archive on compaction; no prune tool

- [x] **GAP04-C20-020** — Production gate: complete storage exhaustion must degrade into a deterministic safe freeze rather than silent data loss, corrupt state, or unaudited action.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`


### Component acceptance evidence

- [~] **GAP04-C20-021** — An approved design/ADR exists for **Fail-safe storage exhaustion strategy** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C20-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C20-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C20-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL`

- [~] **GAP04-C20-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`, `tests/test_p0_durability.py::JournalWAL` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (14 verified / 10 partial / 1 blocked / 1 not started / 0 N/A)
- **GO impact:** Blocking
- **Implementation:** `runtime/journal.py:_admit`, `runtime/node.py:_on_pressure`, `runtime/node.py:clear_storage_freeze`
- **Remaining gap:** Journal budget + reserve; other budgets (logs/tmp) external.


---


## 21. Declarative configuration model

**Priority:** P1  
**Control family:** Config  

### Checklist

- [x] **GAP04-C21-001** — Version the configuration schema and track provenance/digest for the effective configuration.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-002** — Validate types, ranges, units, cross-field constraints, and security-sensitive combinations before activation.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-003** — Separate secrets from non-secret configuration and apply least-privilege access to config stores.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-004** — Expose active version/digest and validation/activation state in health/audit records.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [~] **GAP04-C21-005** — Maintain golden valid/invalid fixtures and migration tests.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Note: partially implemented; No layered precedence.

- [x] **GAP04-C21-006** — Define a versioned schema for site/environment configuration covering lease duration, tier thresholds, allowed actions, policy staleness, quotas, storage limits, retry budgets, timeouts, endpoints, and feature gates.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Waiver(s): W-013

- [x] **GAP04-C21-007** — Separate immutable build-time defaults from environment/site overrides and operator emergency overrides.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-008** — Define type, range, enum, unit, cross-field, and semantic validation for every configuration value.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-009** — Prohibit unknown keys in production unless an explicit forward-compatibility extension mechanism is defined.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [~] **GAP04-C21-010** — Support deterministic layered precedence and expose the fully resolved effective configuration.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Note: single document; no layering

- [x] **GAP04-C21-011** — Bind configuration to site/tenant/trust-domain identity to prevent accidental cross-environment reuse.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [-] **GAP04-C21-012** — Support secrets by reference to secret stores rather than inline plaintext values.
  - Note: N/A proposed: configuration contains no secrets

- [x] **GAP04-C21-013** — Attach config ID/version/digest, author/source, creation time, and provenance to every effective configuration.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [~] **GAP04-C21-014** — Add configuration schema migration and compatibility tests across supported releases.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Note: one config version exists

- [x] **GAP04-C21-015** — Add negative tests for missing required values, out-of-range thresholds, invalid units, contradictory settings, and unsafe combinations.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-016** — Expose effective config digest/version in health and audit records without leaking secrets.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-017** — Provide a config linter/dry-run command usable in CI and before activation.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-018** — Document defaults, rationale, safe ranges, and whether each setting is dynamic or restart-required.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-019** — Pin production configuration examples as test fixtures.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [x] **GAP04-C21-020** — Production gate: no unvalidated or ambiguous configuration may influence autonomy decisions.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`


### Component acceptance evidence

- [~] **GAP04-C21-021** — An approved design/ADR exists for **Declarative configuration model** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C21-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [~] **GAP04-C21-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C21-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C21-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json`

- [~] **GAP04-C21-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/config.py`, `docs/CONFIGURATION.md`, `tests/test_p1_operations.py::Config`, `tests/fixtures/config_prod_example.json` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009, W-013
- **Status:** In progress (18 verified / 6 partial / 1 blocked / 0 not started / 1 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/config.py`, `docs/CONFIGURATION.md`
- **Remaining gap:** No layered precedence.


---


## 22. Atomic configuration activation and rollback

**Priority:** P1  
**Control family:** Config  

### Checklist

- [x] **GAP04-C22-001** — Version the configuration schema and track provenance/digest for the effective configuration.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C22-002** — Validate types, ranges, units, cross-field constraints, and security-sensitive combinations before activation.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C22-003** — Separate secrets from non-secret configuration and apply least-privilege access to config stores.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C22-004** — Expose active version/digest and validation/activation state in health/audit records.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C22-005** — Maintain golden valid/invalid fixtures and migration tests.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; ConfigManager is not yet wired to hot-apply into a running node (restart-required).

- [~] **GAP04-C22-006** — Stage configuration separately from active configuration and validate schema, semantics, dependencies, signatures/provenance, and compatibility before activation.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: validation before activation; no separate staging area

- [x] **GAP04-C22-007** — Use an atomic pointer/transaction to switch from old to new configuration; never partially apply fields.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C22-008** — Persist previous known-good configuration and its digest for deterministic rollback.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C22-009** — Record author, approver, reason, ticket/change ID, staged time, activation time, and affected scope.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: no ticket/change id field

- [ ] **GAP04-C22-010** — Support scheduled activation with trusted-time validation and explicit cancellation.
  - Note: not started

- [x] **GAP04-C22-011** — Require two-person approval for high-risk autonomy/security/storage thresholds where governance requires it.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C22-012** — Define rollback eligibility when a newer config has already produced incompatible durable state.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented

- [~] **GAP04-C22-013** — Add startup recovery for crash during stage, validation, activation, or rollback.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: atomic writes; crash-during-activation not tested

- [~] **GAP04-C22-014** — Add tests for invalid config, dependency mismatch, crash during activation, repeated activation, rollback, stale activation request, and concurrent operators.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: invalid/repeat/rollback tested; concurrency not

- [~] **GAP04-C22-015** — Audit every stage/activate/reject/rollback with old/new digest and reason.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: history files; not journaled

- [~] **GAP04-C22-016** — Expose active/staged version, validation state, activation timestamp, and rollback availability.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: not exposed in health

- [~] **GAP04-C22-017** — Prevent unauthorized local filesystem edits from becoming active configuration.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: optional signed config

- [~] **GAP04-C22-018** — Define distributed rollout semantics for multiple controllers/sites and version skew.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: rollout.py covers versions, not config

- [ ] **GAP04-C22-019** — Provide pre-activation impact/diff output for operators.
  - Note: not started

- [~] **GAP04-C22-020** — Production gate: config changes are all-or-nothing, attributable, reversible where supported, and impossible without validation.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: restart-required activation


### Component acceptance evidence

- [~] **GAP04-C22-021** — An approved design/ADR exists for **Atomic configuration activation and rollback** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C22-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C22-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C22-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C22-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C22-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/config.py:ConfigManager`, `tests/test_p1_operations.py::Config`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (9 verified / 14 partial / 1 blocked / 2 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/config.py:ConfigManager`
- **Remaining gap:** ConfigManager is not yet wired to hot-apply into a running node (restart-required).


---


## 23. Tier schedule configuration

**Priority:** P1  
**Control family:** Config  

### Checklist

- [x] **GAP04-C23-001** — Version the configuration schema and track provenance/digest for the effective configuration.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-002** — Validate types, ranges, units, cross-field constraints, and security-sensitive combinations before activation.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-003** — Separate secrets from non-secret configuration and apply least-privilege access to config stores.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-004** — Expose active version/digest and validation/activation state in health/audit records.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-005** — Maintain golden valid/invalid fixtures and migration tests.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: partially implemented; Schedule digest not bound to decisions.

- [x] **GAP04-C23-006** — Replace static `0/30/120` thresholds with a validated versioned tier policy.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-007** — Define units explicitly and reject implicit seconds/minutes conversions.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-008** — Support per-site/per-workload-class overrides only within centrally approved safety bounds.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: per-site config within validation bounds; no central approval of bounds

- [x] **GAP04-C23-009** — Require thresholds to be strictly ordered and non-negative with an explicit maximum disconnected horizon.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-010** — Define transition hysteresis and whether tier changes are based on trusted elapsed disconnect time, lease remaining, policy age, or a composed rule.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-011** — Bind the tier schedule digest/version to decisions and audit records.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: config_version bound; schedule digest not

- [x] **GAP04-C23-012** — Define action allow/deny matrix for every tier and verify no undefined action inherits permissive behavior.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-013** — Add boundary tests at threshold−ε, threshold, threshold+ε, clock jump, reboot, and policy refresh.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [x] **GAP04-C23-014** — Add configuration tests for equal/reversed thresholds, extreme values, integer overflow, and unsupported tier names.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-015** — Expose current tier, next threshold, time to transition, schedule version, and reason through health/metrics.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: tier in health; next threshold not

- [~] **GAP04-C23-016** — Audit every tier transition and operator-forced tier.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: tier-transition metric; per-transition audit not

- [~] **GAP04-C23-017** — Document safe defaults and approved ranges by deployment class.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: CONFIGURATION.md

- [ ] **GAP04-C23-018** — Define rollback behavior if a prior tier schedule is reactivated during an existing partition.
  - Note: not started

- [x] **GAP04-C23-019** — Ensure tier policy changes cannot extend an already-expired authority period.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-020** — Production gate: tier transitions are deterministic, time-safe, fully policy-bound, and test-covered at every boundary.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: digest binding missing


### Component acceptance evidence

- [~] **GAP04-C23-021** — An approved design/ADR exists for **Tier schedule configuration** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C23-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C23-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C23-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection`

- [~] **GAP04-C23-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `controller.py:validate_tier_schedule`, `runtime/config.py`, `tests/test_p1_operations.py::Config`, `tests/test_p1_resilience_suites.py::FaultInjection` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (14 verified / 10 partial / 1 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `controller.py:validate_tier_schedule`, `runtime/config.py`
- **Remaining gap:** Schedule digest not bound to decisions.


---


## 24. Operator override workflow

**Priority:** P1  
**Control family:** Security Ops  

### Checklist

- [~] **GAP04-C24-001** — Define operator roles, authentication strength, authorization scope, approval rules, and emergency-access policy.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: partially implemented; No ticket reference or signed override records.

- [x] **GAP04-C24-002** — Make operator actions durable, time-bounded where appropriate, and fully auditable.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-003** — Protect management interfaces against replay, stale commands, cross-site scope errors, and unauthorized local access.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-004** — Expose active emergency/override state prominently in health and dashboards.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-005** — Exercise operator workflows through tabletop/game-day and negative authorization testing.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: partially implemented; No ticket reference or signed override records.

- [x] **GAP04-C24-006** — Define explicit override types: freeze, disable, tier restriction, emergency deny, limited temporary allow, and diagnostic mode; default to deny-only overrides where possible.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-007** — Require strong operator authentication, authorization, and scoped roles separate from ordinary application identities.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-008** — Require reason, ticket/incident reference, target scope, start time, hard expiry, and requested action for every override.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: reason/ttl/scope; no ticket reference

- [x] **GAP04-C24-009** — Use two-person approval for overrides that expand authority or bypass a normal safety control where policy requires it.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-010** — Cryptographically sign or otherwise integrity-protect override records and bind them to controller/site identity.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: journal MAC protects records; not individually signed

- [x] **GAP04-C24-011** — Apply overrides through the same atomic durable state machinery as policy/config transitions.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-012** — Ensure override expiry is evaluated using trusted time and cannot be extended by reboot or clock rollback.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-013** — Make conflicting overrides deterministic with documented precedence; fail closed on ambiguity.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-014** — Provide explicit revoke/cancel with confirmation of resulting effective policy.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-015** — Audit request, approval, activation, use, expiration, cancellation, and failure with operator identities.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: journaled; 'use' events not

- [~] **GAP04-C24-016** — Add tests for expired override, stale approval, wrong scope, duplicate activation, concurrent operators, reboot, connectivity loss, and revocation.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: expiry/two-person/role tested; reboot/connectivity loss not

- [x] **GAP04-C24-017** — Expose active override state prominently in health and dashboards.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [x] **GAP04-C24-018** — Prevent override secrets/tokens from appearing in logs or command history.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-019** — Require post-incident review and evidence retention for production overrides.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: process in INCIDENT_SEVERITY; not enforced

- [x] **GAP04-C24-020** — Production gate: no override can silently persist, exceed its scope/time, or erase the evidence that it existed.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`


### Component acceptance evidence

- [~] **GAP04-C24-021** — An approved design/ADR exists for **Operator override workflow** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C24-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C24-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C24-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides`

- [~] **GAP04-C24-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`, `tests/test_p1_operations.py::Overrides` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 10 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/node.py:request_override`, `runtime/node.py:approve_override`, `runtime/node.py:cancel_override`
- **Remaining gap:** No ticket reference or signed override records.


---


## 25. Health/readiness API

**Priority:** P1  
**Control family:** Observability  

### Checklist

- [x] **GAP04-C25-001** — Define a versioned telemetry schema/taxonomy and map signals to SLOs and failure modes.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-002** — Control cardinality, privacy, redaction, retention, and access.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-003** — Ensure telemetry pipelines are bounded and cannot block safety-critical control flow.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-004** — Correlate metrics/logs/traces/audit using stable identifiers without conflating diagnostic telemetry with authoritative audit.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C25-005** — Test telemetry correctness, missing-data behavior, and alertability under fault injection.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Health shares the node lock.

- [x] **GAP04-C25-006** — Define separate liveness, readiness, and safety-readiness semantics; a process can be alive while not safe to authorize offline actions.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C25-007** — Include dependency state for policy engine, security plane, supervisor, replication, reachability source, key store, trusted time, and persistence.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: reachability + breakers; key store/persistence partial

- [x] **GAP04-C25-008** — Report lease validity/remaining time, policy freshness, authority epoch, partition epoch, controller generation, current tier, journal pressure, reconciliation backlog, and active override/freeze state.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C25-009** — Expose application version, protocol/schema versions, build digest, active config digest, and active policy digest.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: no build digest

- [x] **GAP04-C25-010** — Return stable machine-readable health codes and component states rather than free-form text only.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-011** — Protect detailed health endpoints with authentication/authorization if they reveal topology or security posture.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-012** — Provide a minimal local liveness endpoint that does not depend on external services to avoid restart loops.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-013** — Define readiness thresholds and reason precedence deterministically.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C25-014** — Add tests for every degraded/failed dependency and combination of simultaneous faults.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: several faults, not all combinations

- [~] **GAP04-C25-015** — Ensure health evaluation is bounded-time and cannot deadlock behind the component it is diagnosing.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: health takes the node lock (can wait behind reconnect)

- [x] **GAP04-C25-016** — Expose age of health data and avoid reporting stale cached success as current.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-017** — Integrate health state with orchestration without causing destructive restart loops during expected partitions.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C25-018** — Audit transitions into/out of safety-not-ready states where operationally significant.
  - Note: not started

- [x] **GAP04-C25-019** — Document which health states should page, freeze autonomy, or merely warn.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C25-020** — Production gate: an external operator/orchestrator can determine whether GAP-04 is safe to serve, not merely whether its process is running.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`


### Component acceptance evidence

- [~] **GAP04-C25-021** — An approved design/ADR exists for **Health/readiness API** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C25-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C25-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C25-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C25-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C25-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:health`, `runtime/opsapi.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (16 verified / 8 partial / 1 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/node.py:health`, `runtime/opsapi.py`
- **Remaining gap:** Health shares the node lock.


---


## 26. Metrics exporter

**Priority:** P1  
**Control family:** Observability  

### Checklist

- [x] **GAP04-C26-001** — Define a versioned telemetry schema/taxonomy and map signals to SLOs and failure modes.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C26-002** — Control cardinality, privacy, redaction, retention, and access.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C26-003** — Ensure telemetry pipelines are bounded and cannot block safety-critical control flow.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C26-004** — Correlate metrics/logs/traces/audit using stable identifiers without conflating diagnostic telemetry with authoritative audit.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C26-005** — Test telemetry correctness, missing-data behavior, and alertability under fault injection.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Default histogram buckets; limited histograms.

- [~] **GAP04-C26-006** — Define counters for decisions attempted/allowed/denied/failed, reconnects, reconciliations, conflicts, retries, revocations, journal writes, audit writes, and dependency failures.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: core counters; revocation/journal-write counters not

- [~] **GAP04-C26-007** — Define histograms for decision latency, persistence latency, policy evaluation, supervisor action, reconciliation batch, and reconnect convergence.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: decision latency only

- [x] **GAP04-C26-008** — Define gauges for lease remaining, policy age, journal bytes/utilization, reconciliation backlog, current tier, authority epoch, active partition duration, queue depth, and storage free space.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C26-009** — Use bounded label cardinality; never label metrics with raw decision IDs, workload IDs at fleet scale, user input, secrets, or unbounded error strings.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C26-010** — Standardize units and histogram buckets based on measured SLOs rather than arbitrary defaults.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: generic buckets, not SLO-derived

- [x] **GAP04-C26-011** — Expose component/version/build/config metadata via dedicated info metrics.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C26-012** — Protect metrics endpoints or transport according to deployment sensitivity.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C26-013** — Implement scrape/export failure isolation so telemetry outage cannot block control decisions.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C26-014** — Add tests verifying metric monotonicity, reset behavior, label sets, units, and no-secret leakage.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: cardinality/format tested; monotonicity/reset not

- [~] **GAP04-C26-015** — Define aggregation rules and recording metrics for fleet/site dashboards.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: dashboard queries only

- [x] **GAP04-C26-016** — Instrument rejected/failed operations with stable reason-code labels.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C26-017** — Track internal queue saturation and dropped telemetry separately from dropped business work.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: not tracked

- [~] **GAP04-C26-018** — Document retention and sampling at telemetry backend.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: backend policy

- [~] **GAP04-C26-019** — Provide golden metric examples for operators and integration tests.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: no golden examples

- [~] **GAP04-C26-020** — Production gate: every production SLO and primary failure mode has a measurable, bounded-cardinality signal.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C26-021** — An approved design/ADR exists for **Metrics exporter** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C26-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C26-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C26-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C26-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C26-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/observability.py`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (12 verified / 13 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/observability.py`
- **Remaining gap:** Default histogram buckets; limited histograms.


---


## 27. Structured logging pipeline

**Priority:** P1  
**Control family:** Observability  

### Checklist

- [x] **GAP04-C27-001** — Define a versioned telemetry schema/taxonomy and map signals to SLOs and failure modes.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-002** — Control cardinality, privacy, redaction, retention, and access.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-003** — Ensure telemetry pipelines are bounded and cannot block safety-critical control flow.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-004** — Correlate metrics/logs/traces/audit using stable identifiers without conflating diagnostic telemetry with authoritative audit.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-005** — Test telemetry correctness, missing-data behavior, and alertability under fault injection.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Synchronous logging.

- [x] **GAP04-C27-006** — Adopt a versioned structured log schema with timestamp, severity, event name, component, site/node/workload scope, decision ID, correlation/trace IDs, partition epoch, controller generation, and reason code.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-007** — Normalize identifiers and field names across GAP-04 and adjacent adapters.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-008** — Define data classification and field-level redaction; prohibit credentials, private keys, tokens, raw secrets, and unnecessary tenant payloads.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-009** — Separate audit records from diagnostic logs; diagnostic retention/rotation must not weaken audit guarantees.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-010** — Implement bounded asynchronous logging with defined behavior under sink slowdown or unavailability.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: synchronous writes

- [~] **GAP04-C27-011** — Prevent logging failures from recursively flooding logs or exhausting disk.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: no recursion guard

- [x] **GAP04-C27-012** — Support sampling for high-volume debug/info events while never sampling required security/audit events.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-013** — Define retention, rotation, compression, export, and deletion policies.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: backend policy

- [x] **GAP04-C27-014** — Include build/config/policy version at process start and relevant transition events.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-015** — Add tests scanning representative logs for secret patterns and forbidden fields.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C27-016** — Add schema/golden tests for critical lifecycle/security events.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-017** — Ensure timestamps include trusted-time quality or clearly distinguish untrusted wall-clock values.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: wall clock; no trusted-time quality field

- [x] **GAP04-C27-018** — Support correlation across decision, supervisor, replication, and reconciliation flows.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-019** — Document operator queries for common incidents.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: RUNBOOK lists entry points

- [~] **GAP04-C27-020** — Production gate: logs are structured, bounded, privacy-aware, correlatable, and cannot become a control-plane availability risk.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C27-021** — An approved design/ADR exists for **Structured logging pipeline** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C27-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C27-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C27-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C27-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/observability.py:StructuredLogger`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 10 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/observability.py:StructuredLogger`
- **Remaining gap:** Synchronous logging.


---


## 28. Distributed trace propagation

**Priority:** P1  
**Control family:** Observability  

### Checklist

- [x] **GAP04-C28-001** — Define a versioned telemetry schema/taxonomy and map signals to SLOs and failure modes.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C28-002** — Control cardinality, privacy, redaction, retention, and access.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C28-003** — Ensure telemetry pipelines are bounded and cannot block safety-critical control flow.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C28-004** — Correlate metrics/logs/traces/audit using stable identifiers without conflating diagnostic telemetry with authoritative audit.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C28-005** — Test telemetry correctness, missing-data behavior, and alertability under fault injection.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Context propagation only; no spans/exporter.

- [x] **GAP04-C28-006** — Adopt a standard trace context format (for example W3C Trace Context/OpenTelemetry) across supported transports.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C28-007** — Create spans for decision evaluation, lease verification, policy evaluation, journal commit, supervisor action, replication exchange, reconciliation, and dependency calls.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: no spans created

- [~] **GAP04-C28-008** — Propagate trace context only across authenticated boundaries and sanitize untrusted incoming baggage.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: malformed headers replaced; baggage not handled

- [x] **GAP04-C28-009** — Do not encode secrets, raw policy data, or high-cardinality sensitive attributes in spans.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C28-010** — Define sampling policy that preserves error/security traces while controlling fleet cost.
  - Note: not started

- [x] **GAP04-C28-011** — Correlate trace/span IDs with structured logs and audit references without making traces authoritative audit evidence.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C28-012** — Instrument retries as linked/child spans so duplicate attempts remain attributable to one logical operation.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: retries share parent context

- [ ] **GAP04-C28-013** — Capture stable error codes and component status on failing spans.
  - Note: not started

- [x] **GAP04-C28-014** — Bound span creation and exporter queues so telemetry backpressure cannot affect control-plane safety.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C28-015** — Add tests for propagation through each adapter and for missing/malformed/untrusted trace headers.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C28-016** — Verify context survives asynchronous callbacks, thread/process boundaries, and retry loops.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: not tested across threads

- [~] **GAP04-C28-017** — Define trace retention/access controls appropriate to potentially sensitive topology data.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented

- [-] **GAP04-C28-018** — Expose exporter health separately from controller readiness.
  - Note: N/A proposed: no exporter

- [~] **GAP04-C28-019** — Document how to trace a single offline decision through reconnect and reconciliation.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial (trace id in decision + batch)

- [~] **GAP04-C28-020** — Production gate: operators can follow a logical control action across supported services without telemetry changing business semantics.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C28-021** — An approved design/ADR exists for **Distributed trace propagation** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C28-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C28-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C28-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C28-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C28-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/observability.py:TraceContext`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (11 verified / 11 partial / 1 blocked / 2 not started / 1 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/observability.py:TraceContext`
- **Remaining gap:** Context propagation only; no spans/exporter.


---


## 29. Alerting and dashboards

**Priority:** P1  
**Control family:** Observability  

### Checklist

- [x] **GAP04-C29-001** — Define a versioned telemetry schema/taxonomy and map signals to SLOs and failure modes.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C29-002** — Control cardinality, privacy, redaction, retention, and access.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C29-003** — Ensure telemetry pipelines are bounded and cannot block safety-critical control flow.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C29-004** — Correlate metrics/logs/traces/audit using stable identifiers without conflating diagnostic telemetry with authoritative audit.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-005** — Test telemetry correctness, missing-data behavior, and alertability under fault injection.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Rules statically validated, not executed in Prometheus.

- [x] **GAP04-C29-006** — Define separate alert conditions for ordinary short partition, prolonged partition, stale policy, lease nearing expiry, lease expired, journal pressure, audit failure, storage critical, reconciliation conflict, duplicate controller, key failure, and software fault.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C29-007** — Base alerts on durable service symptoms/SLOs rather than single noisy samples where possible.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-008** — Define warning/critical thresholds with hysteresis and minimum duration to reduce flapping.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: for-durations; no hysteresis

- [~] **GAP04-C29-009** — Include actionable runbook links, affected scope, current version/config/policy, and stable reason code in alerts.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: runbook + class; version/config not in annotations

- [x] **GAP04-C29-010** — Create dashboards for connectivity/tier state, lease/policy freshness, decision outcomes, persistence health, reconciliation, dependencies, capacity, and security events.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-011** — Provide fleet, site, node, and workload drill-down while controlling high-cardinality queries.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: site variable only

- [ ] **GAP04-C29-012** — Correlate deploy/config/policy changes as annotations on dashboards.
  - Note: not started

- [x] **GAP04-C29-013** — Distinguish security indicators from reliability failures and route to appropriate responders.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-014** — Define paging ownership, escalation, acknowledgement, and auto-resolution behavior.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: severity mapping; owners unassigned (W-001)

- [~] **GAP04-C29-015** — Test alerts using synthetic fault injection and verify they fire, route, and resolve as designed.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: static validation only

- [x] **GAP04-C29-016** — Detect missing telemetry itself so silent exporter failure is visible.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-017** — Ensure dashboards use consistent units/time ranges and explicitly indicate stale data.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial

- [~] **GAP04-C29-018** — Document expected baseline ranges and known benign partition patterns.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial

- [~] **GAP04-C29-019** — Review alert noise and false-negative incidents on a recurring schedule.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: process defined

- [~] **GAP04-C29-020** — Production gate: each P0 failure mode has a tested detection path and an actionable operator view.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C29-021** — An approved design/ADR exists for **Alerting and dashboards** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C29-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C29-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C29-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C29-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`, `tests/test_p1_operations.py::HealthMetricsLogs`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (11 verified / 13 partial / 1 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `ops/alerts.rules.yml`, `ops/dashboard.grafana.json`
- **Remaining gap:** Rules statically validated, not executed in Prometheus.


---


## 30. Backpressure and load shedding

**Priority:** P1  
**Control family:** Resilience  

### Checklist

- [x] **GAP04-C30-001** — Define safety state transitions, resource budgets, overload/failure thresholds, and recovery prerequisites.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [x] **GAP04-C30-002** — Make overload and resource-failure handling deterministic and bounded.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [x] **GAP04-C30-003** — Prioritize safety-critical state/audit work over optional work.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [x] **GAP04-C30-004** — Expose saturation/freeze state through health, metrics, alerts, and machine-readable errors.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [~] **GAP04-C30-005** — Test resource exhaustion and dependency degradation at every relevant lifecycle state.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: partially implemented; Admission on decide only; no per-tenant fairness or jittered backoff.

- [~] **GAP04-C30-006** — Define bounded queues for every inbound work class: decision requests, supervisor commands, replication events, reconciliation work, telemetry, and operator actions.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: decide() bounded; other work classes not queued

- [~] **GAP04-C30-007** — Set concurrency limits per dependency and per workload/site to prevent a noisy tenant or reconnect storm from monopolizing resources.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: per-dependency breakers; no per-tenant limits · Waiver(s): W-013

- [~] **GAP04-C30-008** — Prioritize safety-critical work such as revocation, freeze, audit commit, and reconciliation checkpoints over optional telemetry/debug work.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: control frames get reserve; no queue priority

- [x] **GAP04-C30-009** — Use explicit overload errors with retryability and backoff hints instead of unbounded latency.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [x] **GAP04-C30-010** — Implement circuit breakers for failing adjacent services with half-open recovery and bounded probe rate.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [~] **GAP04-C30-011** — Define retry budgets and exponential backoff with jitter; prohibit infinite tight retry loops.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: retry budget; no jittered backoff

- [x] **GAP04-C30-012** — Drop or coalesce only operations proven safe to discard/merge; never silently drop accepted decisions, revocations, or required audit work.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [ ] **GAP04-C30-013** — Propagate cancellation/deadline from callers where safe to avoid orphaned expensive work.
  - Note: not started

- [~] **GAP04-C30-014** — Add overload tests for reconnect storms, slow disk, slow policy engine, slow supervisor, high decision volume, and telemetry outage.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: storm/burst; slow disk/policy not

- [~] **GAP04-C30-015** — Measure queue depth, queue wait, rejected work, shed work, circuit state, retry count, and saturation time.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: rejections + retries; queue wait not

- [~] **GAP04-C30-016** — Ensure overload handling cannot starve reconciliation indefinitely.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: not analysed

- [ ] **GAP04-C30-017** — Define per-site/fleet capacity limits and test fairness under mixed load.
  - Note: not started

- [~] **GAP04-C30-018** — Document operator tuning ranges and dangerous values.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: CONFIGURATION.md

- [x] **GAP04-C30-019** — Verify backpressure behavior during storage-pressure freeze.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [~] **GAP04-C30-020** — Production gate: sustained overload degrades predictably without unbounded memory growth, deadlock, or loss of safety-critical work.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: partially implemented; Admission on decide only; no per-tenant fairness or jittered backoff.


### Component acceptance evidence

- [~] **GAP04-C30-021** — An approved design/ADR exists for **Backpressure and load shedding** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C30-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [~] **GAP04-C30-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C30-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C30-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py`

- [~] **GAP04-C30-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/resilience.py`, `runtime/node.py:decide`, `tests/test_p1_operations.py::Backpressure`, `tests/test_p1_resilience_suites.py` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009, W-013
- **Status:** In progress (10 verified / 13 partial / 1 blocked / 2 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/resilience.py`, `runtime/node.py:decide`
- **Remaining gap:** Admission on decide only; no per-tenant fairness or jittered backoff.


---


## 31. Crash/restart recovery tests

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C31-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C31-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; No CI; one filesystem.

- [x] **GAP04-C31-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C31-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; No CI; one filesystem.

- [x] **GAP04-C31-006** — Build an automated harness that can terminate the controller at deterministic persistence/lifecycle fault points and restart it repeatedly.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-007** — Cover `kill -9`/TerminateProcess, power-loss simulation, process abort, unhandled exception, host reboot, container kill, and service-manager restart.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: kill -9 and os._exit; no host reboot/power cut

- [x] **GAP04-C31-008** — Inject crashes before/after lease commit, policy activation, epoch increment, journal append, audit append, supervisor dispatch, reconciliation remote commit, and acknowledgement persistence.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C31-009** — Verify startup integrity scans and recovery do not silently discard or duplicate durable decisions.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-010** — Verify pending side effects are queried/replayed idempotently after restart.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: resume_effects exists; not asserted after crash

- [x] **GAP04-C31-011** — Verify lease age, policy age, partition duration, revocation epoch, and controller generation remain safe across restart.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C31-012** — Verify corrupt/torn tail recovery and quarantine of unrecoverable mid-log corruption.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-013** — Run crash tests under normal, low-storage, key-rotation, and reconnect conditions.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: normal + reconnect; low-storage/key-rotation not

- [~] **GAP04-C31-014** — Repeat each critical crash point enough times to detect timing-sensitive races.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: random rounds (6); more in qualification

- [!] **GAP04-C31-015** — Execute tests on every supported filesystem/OS persistence profile.
  - Note: blocked: one OS/filesystem (W-008) · Waiver(s): W-008

- [x] **GAP04-C31-016** — Record durable-state hashes/sequence numbers before crash and after recovery for deterministic assertions.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C31-017** — Fail the suite on unreconciled orphan state, duplicate effect, lost acknowledged action, or rollback of authority generation.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C31-018** — Integrate the fault harness into release CI rather than keeping it manual.
  - Note: blocked: no CI (W-007) · Waiver(s): W-007

- [x] **GAP04-C31-019** — Archive representative recovery evidence with the release.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-020** — Production gate: every defined persistence transition has a passing crash-before/crash-after recovery test.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: most transitions covered


### Component acceptance evidence

- [~] **GAP04-C31-021** — An approved design/ADR exists for **Crash/restart recovery tests** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C31-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C31-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C31-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C31-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/faults.py`, `tests/crash_worker.py`, `tests/test_crash_recovery.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-008, W-009
- **Status:** In progress (13 verified / 9 partial / 4 blocked / 0 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/faults.py`, `tests/crash_worker.py`
- **Remaining gap:** No CI; one filesystem.


---


## 32. Partition/reconnect fault-injection suite

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C32-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [~] **GAP04-C32-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: partially implemented; Adapter-level simulation, not packet-level.

- [x] **GAP04-C32-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [!] **GAP04-C32-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; Adapter-level simulation, not packet-level.

- [~] **GAP04-C32-006** — Provide programmable network fault injection for full partition, asymmetric partition, latency, jitter, loss, duplication, reordering, corruption, DNS failure, and NAT rebinding.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: adapter-level injection

- [x] **GAP04-C32-007** — Exercise transitions at every tier threshold and immediately before/after lease expiry.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-008** — Simulate authority/policy/revocation changes while the node is disconnected.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-009** — Generate conflicting remote state during partition and verify reconciliation classification on reconnect.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-010** — Simulate rapid flap patterns and verify hysteresis prevents unsafe oscillation.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-011** — Simulate reconnect with degraded bandwidth and partial service reachability.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-012** — Verify revocation/policy synchronization and reconciliation ordering precede renewal when required.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [!] **GAP04-C32-013** — Test stale DNS and endpoint migration during long partitions.
  - Note: blocked: DNS is GAP-12's

- [x] **GAP04-C32-014** — Test simultaneous reconnect of many nodes/sites to expose thundering-herd behavior.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [x] **GAP04-C32-015** — Verify authenticated reachability cannot be spoofed by injected unauthenticated packets.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [~] **GAP04-C32-016** — Measure time to safe connected state, backlog drain, and error rate.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: storm timings recorded

- [x] **GAP04-C32-017** — Capture deterministic seeds/scenarios so regressions are reproducible.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [~] **GAP04-C32-018** — Run representative long-duration partitions measured in hours/days in scheduled qualification.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: logical multi-day; not wall-clock

- [x] **GAP04-C32-019** — Assert audit/journal continuity across every scenario.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [~] **GAP04-C32-020** — Production gate: supported partition classes recover deterministically without unauthorized extension of offline authority.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C32-021** — An approved design/ADR exists for **Partition/reconnect fault-injection suite** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C32-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [~] **GAP04-C32-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C32-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C32-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm`

- [~] **GAP04-C32-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/adapters.py`, `runtime/testing.py`, `tests/test_p1_resilience_suites.py::FaultInjection`, `tests/perf/bench.py:storm` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 8 partial / 3 blocked / 0 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/adapters.py`, `runtime/testing.py`
- **Remaining gap:** Adapter-level simulation, not packet-level.


---


## 33. Concurrency/race test suite

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C33-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C33-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C33-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Coarse lock serializes; limited race tooling in CPython.

- [x] **GAP04-C33-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C33-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; Coarse lock serializes; limited race tooling in CPython.

- [x] **GAP04-C33-006** — Identify shared mutable state and publish an explicit locking/transaction ownership model.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C33-007** — Race lease renewal against policy refresh, reconciliation, partition transition, operator override, journal compaction, and shutdown.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: decide vs reconnect raced; others not

- [x] **GAP04-C33-008** — Race multiple callers submitting duplicate and distinct decisions for the same resource.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C33-009** — Race controller ownership takeover against stale in-flight requests from the prior generation.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C33-010** — Stress journal append/rotation/compaction under concurrent readers and reconciliation exporters.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: not stressed concurrently

- [ ] **GAP04-C33-011** — Race security revocation updates against cached authorization decisions.
  - Note: not started

- [-] **GAP04-C33-012** — Use thread/process sanitizers, race detectors, deterministic schedulers, or model-based interleaving tools where available.
  - Note: N/A proposed: no race detector for CPython; coarse lock

- [~] **GAP04-C33-013** — Add high-iteration stress tests with randomized scheduling and reproducible seeds.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: seeded, modest iterations

- [~] **GAP04-C33-014** — Verify no deadlocks, lock inversions, starvation, double-commit, lost wakeups, or inconsistent snapshots.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: no deadlock observed; not proven

- [~] **GAP04-C33-015** — Set timeouts that detect hung tests and dump relevant thread/task state.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: harness timeouts only

- [ ] **GAP04-C33-016** — Test cancellation and shutdown while dependency calls and disk writes are in progress.
  - Note: not started

- [~] **GAP04-C33-017** — Verify health/readiness inspection cannot deadlock with control operations.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: health shares lock

- [x] **GAP04-C33-018** — Run concurrency tests under optimized/runtime production settings.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C33-019** — Track race regressions with minimized reproducer fixtures.
  - Note: not started

- [~] **GAP04-C33-020** — Production gate: concurrent operations preserve documented invariants under sustained stress and supported process/thread models.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C33-021** — An approved design/ADR exists for **Concurrency/race test suite** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C33-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C33-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C33-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C33-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C33-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py (single RLock)`, `tests/test_p1_resilience_suites.py::Concurrency`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (9 verified / 11 partial / 2 blocked / 3 not started / 1 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/node.py (single RLock)`
- **Remaining gap:** Coarse lock serializes; limited race tooling in CPython.


---


## 34. Fuzzing/property tests

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C34-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C34-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C34-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Seeded fuzz without coverage tooling.

- [x] **GAP04-C34-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C34-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; Seeded fuzz without coverage tooling.

- [x] **GAP04-C34-006** — Define state-machine properties for lease lifecycle, partition transitions, tier monotonicity, policy freshness, epoch monotonicity, and reconciliation idempotency.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C34-007** — Generate randomized valid/invalid event sequences including reboot, disconnect, reconnect, renewal, revocation, policy update, override, and storage fault.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C34-008** — Fuzz all accepted schema payloads with malformed types, duplicate fields, oversized values, invalid Unicode, numeric extremes, and nested-depth abuse.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C34-009** — Fuzz timestamps around epoch, boundaries, overflow, negative values, far future, leap events, and ordering violations.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial timestamp fuzz

- [x] **GAP04-C34-010** — Fuzz signed envelope parsing before signature verification to detect parser inconsistencies and resource exhaustion.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C34-011** — Property-test canonical serialization round trips and signature/hash stability.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C34-012** — Fuzz journal/audit record recovery with arbitrary truncation/bit flips/record reordering.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: bit-flip/deletion tests only

- [ ] **GAP04-C34-013** — Fuzz reconciliation batches with duplicates, missing IDs, conflicting versions, unknown operations, and partial acknowledgements.
  - Note: not started

- [x] **GAP04-C34-014** — Assert fail-closed behavior for malformed security-critical inputs.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C34-015** — Use corpus minimization and persist all crashing or invariant-violating inputs as regressions.
  - Note: not started

- [ ] **GAP04-C34-016** — Run fuzzers with memory/time limits and sanitizers where supported.
  - Note: not started

- [ ] **GAP04-C34-017** — Track code/branch/grammar coverage for parsers and lifecycle transitions.
  - Note: not started

- [~] **GAP04-C34-018** — Integrate bounded fuzz smoke tests into CI and longer campaigns into scheduled security testing.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: in-suite smoke; no CI · Waiver(s): W-007

- [ ] **GAP04-C34-019** — Version fuzz corpora alongside schemas/protocols.
  - Note: not started

- [~] **GAP04-C34-020** — Production gate: no known malformed input can violate safety invariants, crash the controller, or create unbounded resource consumption.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C34-021** — An approved design/ADR exists for **Fuzzing/property tests** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C34-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C34-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C34-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C34-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C34-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/canonical.py`, `runtime/trust.py`, `tests/test_p1_resilience_suites.py::PropertyFuzz`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (11 verified / 8 partial / 2 blocked / 5 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/canonical.py`, `runtime/trust.py`
- **Remaining gap:** Seeded fuzz without coverage tooling.


---


## 35. Security/adversarial tests

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C35-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C35-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C35-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; No PKI/IPC attack tests; no pentest.

- [x] **GAP04-C35-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C35-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; No PKI/IPC attack tests; no pentest.

- [x] **GAP04-C35-006** — Create a threat model covering malicious network peers, compromised adjacent services, hostile local processes, stolen disk, clock manipulation, rollback, operator misuse, and supply-chain tampering.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C35-007** — Test forged/modified leases, policies, capabilities, audit events, and reconciliation messages.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C35-008** — Test replay of old valid messages after revocation, restart, ownership change, and snapshot restore.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C35-009** — Test spoofed reachability and downgrade attacks against authentication, crypto algorithms, protocol versions, and policy schemas.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C35-010** — Test privilege escalation and confused-deputy paths through every adapter.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: adapter escalation partially

- [ ] **GAP04-C35-011** — Test malformed certificate chains, revoked credentials, wrong audience/issuer, expired credentials, and trust-store rollback.
  - Note: not started

- [~] **GAP04-C35-012** — Test journal/audit tampering and encrypted-state transplantation.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: tamper yes; transplantation no

- [~] **GAP04-C35-013** — Test resource exhaustion: disk, memory, queue, CPU, file descriptors, connection count, and oversized messages.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: disk/oversize/queue; FDs/connections not

- [ ] **GAP04-C35-014** — Test local IPC ACL bypass and same-host unprivileged attack attempts.
  - Note: not started

- [x] **GAP04-C35-015** — Test break-glass/override abuse including expired approval and scope expansion.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C35-016** — Perform dependency vulnerability scanning and targeted penetration testing for exposed management surfaces.
  - Note: blocked: independent pentest + scanner (W-009) · Waiver(s): W-009

- [x] **GAP04-C35-017** — Verify security failures produce sanitized external errors and sufficiently detailed protected audit evidence.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C35-018** — Map tests to threat-model controls and accepted residual risks.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C35-019** — Retest after cryptographic/protocol/identity changes.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: process in REVIEW_PROCESS

- [~] **GAP04-C35-020** — Production gate: all high/critical threat scenarios have passing controls or explicitly approved, time-bounded exceptions with compensating controls.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C35-021** — An approved design/ADR exists for **Security/adversarial tests** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C35-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C35-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C35-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C35-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C35-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/THREAT_MODEL.md`, `tests/test_p1_resilience_suites.py::Adversarial`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (12 verified / 9 partial / 3 blocked / 2 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `docs/THREAT_MODEL.md`
- **Remaining gap:** No PKI/IPC attack tests; no pentest.


---


## 36. Schema contract tests and compatibility fixtures

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C36-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [x] **GAP04-C36-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: partially implemented; No adjacent N-1 matrix.

- [x] **GAP04-C36-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [!] **GAP04-C36-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; No adjacent N-1 matrix.

- [~] **GAP04-C36-006** — Maintain authoritative machine-readable schemas for every external request, response, event, durable record, config file, and error envelope.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: 15 wire schemas; journal frames not schema-described

- [x] **GAP04-C36-007** — Version schemas explicitly and document backward/forward compatibility policy.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-008** — Create golden fixtures for minimum, typical, maximum, optional-field, deprecated-field, and invalid payloads.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: typical + invalid; not min/max/deprecated sets

- [x] **GAP04-C36-009** — Validate emitted messages against schemas in tests, not only accepted messages.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [x] **GAP04-C36-010** — Test unknown fields, missing fields, enum extension, numeric limits, Unicode, ordering-insensitive fields, and duplicate-key parser behavior.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-011** — Run supported N/N-1 or documented version-skew test matrices between GAP-04 and adjacent components.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: 4.2.0 views vs 4.3.0; adjacent N-1 not

- [x] **GAP04-C36-012** — Define negotiation/rejection behavior for unsupported major/minor versions.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [x] **GAP04-C36-013** — Pin canonical serialization fixtures for signed/hashed structures.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [ ] **GAP04-C36-014** — Generate or validate client/server models from schemas where practical to reduce drift.
  - Note: not started

- [x] **GAP04-C36-015** — Fail CI when code and published schemas diverge.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [x] **GAP04-C36-016** — Include machine-readable error schema fixtures.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-017** — Test migrations of persisted record schemas across supported releases.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: migration guard test only

- [x] **GAP04-C36-018** — Archive fixtures as part of release artifacts.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-019** — Document deprecation windows and removal criteria.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: documented

- [~] **GAP04-C36-020** — Production gate: every supported wire/disk contract has passing golden and version-skew tests.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C36-021** — An approved design/ADR exists for **Schema contract tests and compatibility fixtures** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C36-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C36-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C36-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json`

- [~] **GAP04-C36-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `schemas/`, `runtime/schema.py`, `tests/test_p1_contracts_integration.py::Contracts`, `tests/fixtures/golden_v1.json` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (13 verified / 10 partial / 2 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `schemas/`, `runtime/schema.py`
- **Remaining gap:** No adjacent N-1 matrix.


---


## 37. Adjacent-layer integration tests

**Priority:** P1  
**Control family:** Testing  

### Checklist

- [x] **GAP04-C37-001** — Link every scenario to explicit requirements/invariants and stable test IDs.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [x] **GAP04-C37-002** — Use deterministic seeds/fixtures and archive enough evidence to reproduce failures.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [~] **GAP04-C37-003** — Run tests under production-equivalent optimization, crypto, persistence, and concurrency settings.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Reference stack only (W-002, W-003). · Waiver(s): W-002, W-003

- [x] **GAP04-C37-004** — Include negative/fail-closed assertions, not only happy-path behavior.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [!] **GAP04-C37-005** — Integrate the suite into CI/release qualification with clearly defined blocking criteria.
  - Note: blocked; Reference stack only (W-002, W-003). · Waiver(s): W-002, W-003

- [!] **GAP04-C37-006** — Run GAP-04 against real or release-faithful GAP-01, GAP-05, GAP-12, GAP-13, and PLN-07 implementations rather than mocks alone.
  - Note: blocked: real adjacent implementations (W-002) · Waiver(s): W-002, W-003

- [!] **GAP04-C37-007** — Create a pinned compatibility environment containing exact versions/digests of each adjacent component.
  - Note: blocked (W-002) · Waiver(s): W-002, W-003

- [x] **GAP04-C37-008** — Exercise normal connected mode, partition entry, offline decisions, tier transitions, reconnect, reconciliation, renewal, and policy/security updates end to end.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [~] **GAP04-C37-009** — Verify identity and trust propagation across all boundaries.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: identity via principals; no real mTLS · Waiver(s): W-002, W-003

- [x] **GAP04-C37-010** — Verify policy digest, authority epoch, partition epoch, controller generation, decision ID, and trace context remain consistent across systems.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [x] **GAP04-C37-011** — Inject one dependency failure at a time and validate fail-closed or degraded behavior.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [~] **GAP04-C37-012** — Inject simultaneous failures that represent realistic outages.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: asymmetric only · Waiver(s): W-002, W-003

- [!] **GAP04-C37-013** — Test mixed-version rolling upgrades across the supported compatibility matrix.
  - Note: blocked (W-002) · Waiver(s): W-002, W-003

- [~] **GAP04-C37-014** — Verify machine-readable errors map consistently across layers.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial · Waiver(s): W-002, W-003

- [x] **GAP04-C37-015** — Verify metrics/logs/traces correlate one scenario across all services.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [~] **GAP04-C37-016** — Test supervisor side effects against replicated/reconciled authoritative state.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: reference only · Waiver(s): W-002, W-003

- [x] **GAP04-C37-017** — Include real persistence and key-store implementations in qualification runs.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [ ] **GAP04-C37-018** — Archive scenario logs and state snapshots for failed integration runs.
  - Note: not started · Waiver(s): W-002, W-003

- [~] **GAP04-C37-019** — Run a reduced integration suite in CI and full matrix before release.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: no CI · Waiver(s): W-002, W-003, W-007

- [!] **GAP04-C37-020** — Production gate: the supported adjacent-layer stack passes the documented end-to-end autonomy lifecycle.
  - Note: blocked (W-002) · Waiver(s): W-002, W-003


### Component acceptance evidence

- [~] **GAP04-C37-021** — An approved design/ADR exists for **Adjacent-layer integration tests** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001, W-002, W-003

- [x] **GAP04-C37-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [~] **GAP04-C37-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-002, W-003, W-007

- [!] **GAP04-C37-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-002, W-003, W-009

- [x] **GAP04-C37-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-002, W-003

- [~] **GAP04-C37-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/testing.py`, `runtime/adapters.py`, `tests/test_p1_contracts_integration.py::Integration`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001, W-002, W-003


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-003, W-007, W-009
- **Status:** In progress (10 verified / 9 partial / 6 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/testing.py`, `runtime/adapters.py`
- **Remaining gap:** Reference stack only (W-002, W-003).


---


## 38. Performance baselines/SLO measurements

**Priority:** P1  
**Control family:** Performance  

### Checklist

- [x] **GAP04-C38-001** — Define representative workload/hardware profiles and record exact test environment metadata.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C38-002** — Measure latency, throughput, resource use, queueing, and saturation with reproducible methodology.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-003** — Establish release-regression thresholds tied to SLO/capacity requirements.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Container measurements only (W-010).

- [x] **GAP04-C38-004** — Test both steady-state and degraded/reconnect/crypto/persistence-heavy conditions.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-005** — Archive raw results and trend them across releases.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Container measurements only (W-010).

- [x] **GAP04-C38-006** — Define service-level indicators for local decision latency, durable commit latency, reconnect convergence, reconciliation latency, and dependency call latency.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-007** — Measure p50/p95/p99/p99.9 and worst-observed latency under representative normal and degraded workloads.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: p50/p95/p99/max; p99.9 not

- [~] **GAP04-C38-008** — Measure sustainable throughput and saturation throughput for decisions, journal writes, audit writes, and reconciliation records.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: single-writer throughput; saturation not

- [~] **GAP04-C38-009** — Measure CPU, resident memory, heap growth, threads/tasks, file descriptors, disk IOPS, write amplification, and network bytes per decision.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: CPU/RSS/bytes; FDs/IOPS not

- [x] **GAP04-C38-010** — Measure cold/warm startup, recovery scan time, policy load, journal replay, and readiness time.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C38-011** — Measure impact of encryption, signature verification, tracing, and audit integrity controls.
  - Note: not started: ablation

- [!] **GAP04-C38-012** — Benchmark on each supported architecture/OS/storage class relevant to production.
  - Note: blocked (W-010) · Waiver(s): W-008, W-010

- [x] **GAP04-C38-013** — Define workload distributions and dataset sizes so results are reproducible.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-014** — Measure behavior at storage-pressure and queue-saturation thresholds.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial

- [~] **GAP04-C38-015** — Set explicit SLO targets and error budgets based on operational requirements rather than observed best case.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: proposed targets (SLO.md)

- [ ] **GAP04-C38-016** — Automate regression comparison and fail release qualification for statistically significant safety/latency regressions beyond budget.
  - Note: not started (only in-test regression guard) · Waiver(s): W-007

- [x] **GAP04-C38-017** — Capture compiler/runtime/build flags and hardware metadata with benchmark results.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-018** — Include long-tail analysis for fsync and dependency timeouts.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: max recorded; no tail analysis

- [!] **GAP04-C38-019** — Measure power/thermal impact where deployed on constrained edge hardware.
  - Note: blocked (W-010) · Waiver(s): W-010

- [!] **GAP04-C38-020** — Production gate: release artifacts meet documented SLO/capacity targets on representative production hardware.
  - Note: blocked (W-010) · Waiver(s): W-010


### Component acceptance evidence

- [~] **GAP04-C38-021** — An approved design/ADR exists for **Performance baselines/SLO measurements** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C38-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C38-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C38-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C38-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `tests/test_p1_resilience_suites.py::LatencyRegression`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-008, W-009, W-010
- **Status:** In progress (9 verified / 11 partial / 4 blocked / 2 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `tests/perf/bench.py`, `evidence/perf_baseline.json`
- **Remaining gap:** Container measurements only (W-010).


---


## 39. Soak/burst/fleet-scale tests

**Priority:** P1  
**Control family:** Performance  

### Checklist

- [x] **GAP04-C39-001** — Define representative workload/hardware profiles and record exact test environment metadata.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C39-002** — Measure latency, throughput, resource use, queueing, and saturation with reproducible methodology.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C39-003** — Establish release-regression thresholds tied to SLO/capacity requirements.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Logical-time soak; not multi-day wall clock.

- [x] **GAP04-C39-004** — Test both steady-state and degraded/reconnect/crypto/persistence-heavy conditions.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C39-005** — Archive raw results and trend them across releases.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Logical-time soak; not multi-day wall clock.

- [~] **GAP04-C39-006** — Run multi-day continuous operation with repeated partition/reconnect cycles and no process restart.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: logical multi-day

- [~] **GAP04-C39-007** — Run long single partitions at maximum supported offline duration with realistic decision volume.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: 3 logical days

- [~] **GAP04-C39-008** — Generate burst loads exceeding expected peak to validate queue bounds and load shedding.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: admission test only

- [x] **GAP04-C39-009** — Simulate fleet-wide reconnect storms with synchronized and jittered node recovery.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C39-010** — Exercise high journal/audit volume near retention/compaction thresholds.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial

- [ ] **GAP04-C39-011** — Run with periodic policy/config/key rotations during soak.
  - Note: not started

- [~] **GAP04-C39-012** — Inject intermittent dependency failures throughout soak rather than testing steady state only.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: flapping test

- [~] **GAP04-C39-013** — Monitor memory growth, file-handle leaks, queue drift, compaction debt, clock drift, and latency percentiles over time.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: peak RSS only

- [x] **GAP04-C39-014** — Verify audit/journal sequence continuity after the entire run.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C39-015** — Measure reconciliation convergence and backend load under fleet storms.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C39-016** — Use production-representative topology and workload mix or document scaling equivalence.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented equivalence only · Waiver(s): W-010

- [ ] **GAP04-C39-017** — Define pass/fail leakage thresholds for memory, storage, handles, and error rate.
  - Note: not started

- [x] **GAP04-C39-018** — Preserve seed/config/result artifacts for reproducibility.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C39-019** — Compare results to prior release baselines.
  - Note: no prior baseline (4.2.0 had none)

- [~] **GAP04-C39-020** — Production gate: no unbounded resource growth, data drift, or safety invariant failure appears under qualification-duration soak and fleet-scale burst tests.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C39-021** — An approved design/ADR exists for **Soak/burst/fleet-scale tests** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C39-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C39-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C39-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C39-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C39-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `tests/perf/bench.py`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009, W-010
- **Status:** In progress (9 verified / 13 partial / 1 blocked / 3 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `tests/perf/bench.py`
- **Remaining gap:** Logical-time soak; not multi-day wall clock.


---


## 40. Capacity model

**Priority:** P1  
**Control family:** Performance  

### Checklist

- [x] **GAP04-C40-001** — Define representative workload/hardware profiles and record exact test environment metadata.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-002** — Measure latency, throughput, resource use, queueing, and saturation with reproducible methodology.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C40-003** — Establish release-regression thresholds tied to SLO/capacity requirements.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Coefficients from build host only.

- [x] **GAP04-C40-004** — Test both steady-state and degraded/reconnect/crypto/persistence-heavy conditions.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C40-005** — Archive raw results and trend them across releases.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Coefficients from build host only.

- [x] **GAP04-C40-006** — Model maximum decisions per second and decisions per partition for each supported hardware tier.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-007** — Model journal bytes per decision including framing, index, integrity metadata, encryption overhead, and compaction amplification.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-008** — Model audit bytes per event and retained/export backlog.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-009** — Model reconciliation batch sizes, maximum backlog, remote request volume, and expected drain time.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C40-010** — Model CPU cost for crypto verification, policy evaluation, serialization, compression, and reconciliation.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: aggregate CPU only

- [~] **GAP04-C40-011** — Model memory for caches, queues, indexes, active decisions, and per-connection state.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: estimate

- [~] **GAP04-C40-012** — Model network bandwidth for reconnect storms, audit export, policy refresh, and replication catch-up.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: payload bytes only

- [~] **GAP04-C40-013** — Define maximum supported sites/nodes/workloads per controller scope where applicable.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: per state dir; fleet bound by peer

- [x] **GAP04-C40-014** — Include safety margin and degraded-dependency multipliers rather than sizing to nominal averages.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-015** — Derive storage reservation from maximum disconnected duration and peak decision rate.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-016** — Define saturation signals and thresholds that trigger backpressure/freeze before failure.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-017** — Validate the model empirically using load/soak test results.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-018** — Document assumptions and recalculate when schema/crypto/retention changes alter record sizes.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C40-019** — Provide an operator sizing worksheet or machine-readable calculator.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C40-020** — Production gate: supported deployment envelopes have measured headroom and deterministic behavior before saturation.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: needs representative hardware (W-010)


### Component acceptance evidence

- [~] **GAP04-C40-021** — An approved design/ADR exists for **Capacity model** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C40-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C40-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C40-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C40-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C40-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`, `evidence/perf_baseline.json`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 10 partial / 1 blocked / 0 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/capacity.py`, `docs/CAPACITY_MODEL.md`
- **Remaining gap:** Coefficients from build host only.


---


## 41. Backup/restore/migration tooling

**Priority:** P1  
**Control family:** Recovery  

### Checklist

- [x] **GAP04-C41-001** — Document authoritative state, RPO/RTO, trust/identity constraints, and rollback hazards.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C41-002** — Integrity-protect and version backup/migration artifacts.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C41-003** — Require validation/reconciliation before returning a restored node to normal autonomy.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; No site binding or forced post-restore reconciliation.

- [~] **GAP04-C41-004** — Audit all recovery operations and expose recovery-required state.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; No site binding or forced post-restore reconciliation.

- [ ] **GAP04-C41-005** — Exercise restore/migration regularly using production-representative data.
  - Note: not started in 4.3.0; No site binding or forced post-restore reconciliation.

- [x] **GAP04-C41-006** — Classify which state is authoritative and must be backed up versus reconstructible cache.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C41-007** — Create encrypted, integrity-protected backups containing schema/version metadata and controller/site binding.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: encrypted + digests; site binding not

- [~] **GAP04-C41-008** — Ensure backup capture is transactionally consistent across lease/policy/epoch/journal/reconciliation state or uses a verified snapshot protocol.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: stop-the-node or crash-consistent copy

- [~] **GAP04-C41-009** — Never restore controller-generation or revocation state in a way that can move authority backward.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: generation bumped; authority watermark relies on control plane

- [~] **GAP04-C41-010** — Define restore into same device, replacement device, and disaster-recovery environment separately.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in RUNBOOK

- [ ] **GAP04-C41-011** — Require explicit identity/key re-binding when hardware-bound keys change.
  - Note: not started

- [~] **GAP04-C41-012** — Provide pre-restore validation of checksum/signature, schema compatibility, site binding, backup age, and rollback risk.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: digests/schema/empty target; site/age not

- [~] **GAP04-C41-013** — Run post-restore integrity scan and reconciliation before enabling normal autonomy.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: chain verified; reconciliation not forced

- [~] **GAP04-C41-014** — Support forward schema migration with backups/checkpoints and tested rollback limits.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: framework + guard test

- [ ] **GAP04-C41-015** — Test restore from oldest supported release and representative large datasets.
  - Note: not started

- [~] **GAP04-C41-016** — Test corrupted/truncated/wrong-key/wrong-site backups and ensure fail-safe refusal.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: wrong key tested; corrupted/wrong-site not

- [ ] **GAP04-C41-017** — Audit backup creation, export, restore attempt, successful restore, migration, and failure.
  - Note: not started

- [~] **GAP04-C41-018** — Document RPO/RTO and recovery authority/approval process.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: RPO/RTO need owner

- [x] **GAP04-C41-019** — Store restore tooling/version alongside release artifacts.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C41-020** — Production gate: disaster recovery restores required state without reviving stale authority or losing accountable offline decisions.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C41-021** — An approved design/ADR exists for **Backup/restore/migration tooling** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C41-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C41-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C41-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C41-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C41-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/backup.py`, `runtime/node.py:migrate_state`, `tests/test_p1_operations.py::BackupRestore`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (6 verified / 15 partial / 1 blocked / 4 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/backup.py`, `runtime/node.py:migrate_state`
- **Remaining gap:** No site binding or forced post-restore reconciliation.


---


## 42. Quarantine and emergency disable mechanism

**Priority:** P1  
**Control family:** Security Ops  

### Checklist

- [~] **GAP04-C42-001** — Define operator roles, authentication strength, authorization scope, approval rules, and emergency-access policy.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Supervisor not instructed to freeze workloads.

- [x] **GAP04-C42-002** — Make operator actions durable, time-bounded where appropriate, and fully auditable.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-003** — Protect management interfaces against replay, stale commands, cross-site scope errors, and unauthorized local access.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-004** — Expose active emergency/override state prominently in health and dashboards.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C42-005** — Exercise operator workflows through tabletop/game-day and negative authorization testing.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Supervisor not instructed to freeze workloads.

- [x] **GAP04-C42-006** — Define distinct states for normal, degraded, frozen, quarantined, and administratively disabled operation.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-007** — Specify which read-only/diagnostic actions remain available in each state and which mutations are categorically denied.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-008** — Provide authenticated local and remote triggers with scoped authorization and stable reason codes.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-009** — Make quarantine/disable durable across restart and impossible to clear merely by reconnect or service restart.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-010** — Require explicit authenticated recovery action plus health prerequisites before returning to normal service.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C42-011** — Support automatic entry on selected critical conditions such as audit integrity failure, rollback detection, split-brain, key compromise, or unrecoverable journal corruption.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: storage freeze automatic; integrity failure refuses start

- [x] **GAP04-C42-012** — Ensure entering quarantine can still record the transition using reserved audit capacity.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C42-013** — Coordinate quarantine with GAP-01 supervisor to stop/freeze workloads safely where policy requires.
  - Note: not started

- [~] **GAP04-C42-014** — Prevent a stale controller generation from clearing quarantine established by a newer authority.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: generation not checked on release

- [~] **GAP04-C42-015** — Add tests for trigger races, reboot, disconnected operation, wrong operator role, expired approval, and partial dependency failure.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: reboot/role/binding tested

- [x] **GAP04-C42-016** — Audit trigger, initiator, reason, scope, resulting actions, and clear event.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-017** — Expose quarantine status prominently through health, metrics, and dashboards.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C42-018** — Document emergency procedures and recovery evidence requirements.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C42-019** — Exercise the mechanism in incident-response game days.
  - Note: not exercised

- [x] **GAP04-C42-020** — Production gate: critical integrity/security failures can force a durable safe state with a controlled, attributable recovery path.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`


### Component acceptance evidence

- [~] **GAP04-C42-021** — An approved design/ADR exists for **Quarantine and emergency disable mechanism** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C42-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C42-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C42-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C42-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C42-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`, `tests/test_p1_operations.py::Quarantine`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 8 partial / 1 blocked / 2 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/node.py:quarantine`, `runtime/node.py:release_quarantine`
- **Remaining gap:** Supervisor not instructed to freeze workloads.


---


## 43. Canary/staged rollout/rollback machinery

**Priority:** P1  
**Control family:** Deployment  

### Checklist

- [x] **GAP04-C43-001** — Define staged promotion criteria, rollback constraints, and supported mixed-version windows.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-002** — Verify exact artifact identity/signature/provenance before activation.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Decision logic only; no deployment integration.

- [x] **GAP04-C43-003** — Coordinate durable schema/protocol migration with rollback and compatibility strategy.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-004** — Expose rollout version/channel and health gates through telemetry.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Decision logic only; no deployment integration.

- [ ] **GAP04-C43-005** — Test upgrade/rollback during active partition and reconciliation.
  - Note: not started in 4.3.0; Decision logic only; no deployment integration.

- [x] **GAP04-C43-006** — Define release rings/stages and eligibility criteria for dev, lab, canary, limited production, and broad production.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-007** — Gate promotion on compatibility tests, health metrics, error budgets, reconciliation success, storage health, and security signals.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: health/denials gates

- [x] **GAP04-C43-008** — Support mixed-version operation only for versions explicitly listed in the compatibility matrix.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-009** — Coordinate schema/protocol changes with expand/contract or equivalent safe migration strategy.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented

- [x] **GAP04-C43-010** — Prevent rollout of a build that cannot read existing durable state or safely downgrade where rollback is required.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C43-011** — Define automatic halt conditions and manual approval points.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-012** — Support emergency rollback to the last known-good compatible version without rolling security epochs/policies backward.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: logic only

- [x] **GAP04-C43-013** — Tag every controller instance with release digest/channel and expose it in telemetry.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C43-014** — Stagger fleet reconnect/restart to avoid thundering-herd effects.
  - Note: not started

- [ ] **GAP04-C43-015** — Add canary scenarios that include active partitions and pending reconciliation, not only idle nodes.
  - Note: not started

- [ ] **GAP04-C43-016** — Test upgrade during partition, during reconciliation, during key rotation, and under storage pressure.
  - Note: not started

- [~] **GAP04-C43-017** — Preserve release evidence and exact artifact digests for every stage.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: history kept in object

- [~] **GAP04-C43-018** — Document rollback limitations for irreversible migrations.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented

- [ ] **GAP04-C43-019** — Integrate signing/provenance verification into deployment admission.
  - Note: not started

- [~] **GAP04-C43-020** — Production gate: promotion is evidence-driven and rollback cannot invalidate persisted safety or authority state.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C43-021** — An approved design/ADR exists for **Canary/staged rollout/rollback machinery** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C43-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C43-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C43-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C43-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/rollout.py`, `tests/test_p1_operations.py::Rollouts`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (9 verified / 11 partial / 1 blocked / 5 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/rollout.py`
- **Remaining gap:** Decision logic only; no deployment integration.


---


## 44. Dependency compatibility matrix

**Priority:** P1  
**Control family:** Release  

### Checklist

- [x] **GAP04-C44-001** — Make supported environments/dependencies explicit and machine-verifiable where possible.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-002** — Reject unsupported/incompatible environments before safety-critical operation.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Adjacent real versions unknown.

- [x] **GAP04-C44-003** — Retain exact build/dependency/version evidence with every release.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-004** — Automate compatibility and packaging checks in CI.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Adjacent real versions unknown.

- [x] **GAP04-C44-005** — Define deprecation/EOL handling for dependencies and runtime platforms.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-006** — List supported versions/ranges for `pk_core`, GAP-01, GAP-05, GAP-12, GAP-13, PLN-07, OS, Python/runtime, CPU architecture, crypto library/provider, storage engine, and key-store integration.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: adjacent real versions null (W-002) · Waiver(s): W-003

- [x] **GAP04-C44-007** — Distinguish build-time, runtime, protocol, and persisted-schema compatibility.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-008** — State minimum/maximum supported versions rather than relying on unbounded semver assumptions.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: ranges partial

- [~] **GAP04-C44-009** — Document required features/capabilities from each dependency, not only version numbers.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: features partial

- [~] **GAP04-C44-010** — Generate automated matrix tests for high-risk adjacent combinations.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: consistency test only

- [x] **GAP04-C44-011** — Reject startup or readiness when a required dependency advertises an unsupported incompatible major/protocol version.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-012** — Define N/N-1 rolling-upgrade support explicitly.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: 4.2.0→4.3.0 only

- [ ] **GAP04-C44-013** — Track CVE/security-support status that can deprecate an otherwise technically compatible version.
  - Note: not started

- [~] **GAP04-C44-014** — Pin known-good integration fixture versions in CI.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: golden fixtures

- [~] **GAP04-C44-015** — Record detected dependency versions in health/startup logs/release evidence.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: code version only

- [~] **GAP04-C44-016** — Define exception process for temporarily supporting out-of-matrix combinations.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: waiver process

- [~] **GAP04-C44-017** — Review matrix on every dependency upgrade and protocol/schema change.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: process

- [x] **GAP04-C44-018** — Version the matrix itself and ship it with release documentation.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-019** — Include hardware/firmware constraints for trusted time/TPM/HSM features.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial

- [!] **GAP04-C44-020** — Production gate: deployed combinations are represented by tested entries in the approved compatibility matrix.
  - Note: blocked (W-002) · Waiver(s): W-002


### Component acceptance evidence

- [~] **GAP04-C44-021** — An approved design/ADR exists for **Dependency compatibility matrix** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C44-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C44-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C44-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C44-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-002, W-003, W-007, W-009
- **Status:** In progress (8 verified / 15 partial / 2 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `COMPATIBILITY_MATRIX.json`, `runtime/adapters.py:negotiate`
- **Remaining gap:** Adjacent real versions unknown.


---


## 45. Packaging/dependency lock

**Priority:** P1  
**Control family:** Release  

### Checklist

- [x] **GAP04-C45-001** — Make supported environments/dependencies explicit and machine-verifiable where possible.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [~] **GAP04-C45-002** — Reject unsupported/incompatible environments before safety-critical operation.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: partially implemented; Hashes pending (W-004).

- [x] **GAP04-C45-003** — Retain exact build/dependency/version evidence with every release.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [~] **GAP04-C45-004** — Automate compatibility and packaging checks in CI.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: partially implemented; Hashes pending (W-004).

- [x] **GAP04-C45-005** — Define deprecation/EOL handling for dependencies and runtime platforms.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [~] **GAP04-C45-006** — Define package metadata with exact application version, build ID, source commit, target platform/architecture, runtime requirements, and entry points.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: no build id/commit (no VCS in candidate)

- [~] **GAP04-C45-007** — Pin production dependencies with hashes or an equivalently reproducible lock mechanism.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: pins without hashes (W-004) · Waiver(s): W-004

- [x] **GAP04-C45-008** — Separate direct from transitive dependencies and document why each privileged/security-critical dependency is required.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [x] **GAP04-C45-009** — Support deterministic/reproducible builds to the extent practical and record build environment/toolchain versions.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [ ] **GAP04-C45-010** — Provide offline installation artifacts for disconnected deployment environments.
  - Note: not started: wheelhouse

- [~] **GAP04-C45-011** — Validate installation without internet access, user-profile writes where prohibited, or hidden dynamic dependency fetches.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: not tested

- [~] **GAP04-C45-012** — Include platform markers and reject unsupported OS/architecture combinations clearly.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: python marker only

- [ ] **GAP04-C45-013** — Run clean-machine install/uninstall/upgrade tests for every supported platform.
  - Note: not started · Waiver(s): W-008

- [x] **GAP04-C45-014** — Verify package file permissions/ACLs, service identity, config directories, state directories, and key-store permissions.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [x] **GAP04-C45-015** — Do not bundle development/test secrets, private signing material, debug endpoints, or stale artifacts.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [x] **GAP04-C45-016** — Generate cryptographic checksums and signed manifests for package contents.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [x] **GAP04-C45-017** — Define upgrade behavior for existing durable state and preserve rollback compatibility rules.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [!] **GAP04-C45-018** — Scan locked dependencies for known vulnerabilities and license policy.
  - Note: blocked: no scanner/network (W-009) · Waiver(s): W-009

- [x] **GAP04-C45-019** — Archive lockfiles/manifests with release evidence.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [~] **GAP04-C45-020** — Production gate: the exact released package can be reproduced/verified and installed offline with only declared dependencies.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: hashes + offline install pending · Waiver(s): W-004


### Component acceptance evidence

- [~] **GAP04-C45-021** — An approved design/ADR exists for **Packaging/dependency lock** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C45-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [~] **GAP04-C45-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C45-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C45-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`

- [~] **GAP04-C45-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `pyproject.toml`, `requirements.lock`, `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-004, W-007, W-008, W-009
- **Status:** In progress (12 verified / 10 partial / 2 blocked / 2 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `pyproject.toml`, `requirements.lock`, `runtime/release.py`
- **Remaining gap:** Hashes pending (W-004).


---


## 46. SBOM, provenance, signing, and release verification

**Priority:** P1  
**Control family:** Supply Chain  

### Checklist

- [x] **GAP04-C46-001** — Document software supply-chain threat model, trusted builders/signers, and artifact verification policy.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C46-002** — Generate machine-readable composition/provenance evidence for every release.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C46-003** — Protect signing identities/keys and define rotation/revocation procedures.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Local signing key (W-006).

- [~] **GAP04-C46-004** — Verify artifacts at deployment/installation time rather than relying only on download-channel trust.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Local signing key (W-006).

- [!] **GAP04-C46-005** — Continuously reassess released artifacts for newly disclosed dependency vulnerabilities.
  - Note: blocked; Local signing key (W-006).

- [x] **GAP04-C46-006** — Generate an SBOM in an industry-standard machine-readable format covering direct/transitive libraries, runtime, bundled binaries, and relevant system components.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C46-007** — Record package names, versions, hashes, licenses, suppliers/origins, and dependency relationships.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: no wheel hashes/licenses · Waiver(s): W-004

- [~] **GAP04-C46-008** — Generate build provenance/attestation linking source revision, build workflow identity, builder, inputs, outputs, and artifact digests.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: local builder id

- [~] **GAP04-C46-009** — Sign release artifacts and manifests with protected release keys or keyless identity-based signing under an approved trust policy.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: ephemeral key (W-006) · Waiver(s): W-006

- [x] **GAP04-C46-010** — Publish/ship checksums and signatures separately enough that a single artifact replacement cannot replace both evidence and payload unnoticed.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C46-011** — Verify signatures/provenance before deployment and fail admission on mismatch or untrusted signer.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: tool exists; not in admission

- [!] **GAP04-C46-012** — Protect release-signing credentials with HSM/KMS or equivalent and documented access controls/rotation.
  - Note: blocked (W-006) · Waiver(s): W-006

- [!] **GAP04-C46-013** — Scan SBOM continuously for newly disclosed vulnerabilities affecting still-supported releases.
  - Note: blocked (W-009) · Waiver(s): W-009

- [ ] **GAP04-C46-014** — Define license/compliance policy and flag disallowed or unknown licenses.
  - Note: not started

- [~] **GAP04-C46-015** — Retain build logs/attestations for the supported lifecycle.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: not retained externally

- [x] **GAP04-C46-016** — Test tampered artifact, tampered SBOM, altered provenance, revoked signer, and expired credential paths.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C46-017** — Document emergency signer compromise and artifact revocation procedure.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: RUNBOOK/VULN doc

- [~] **GAP04-C46-018** — Include dependencies delivered through base images/runtimes, not only language package managers.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: runtime listed; no base image

- [~] **GAP04-C46-019** — Version the release verification policy.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial

- [~] **GAP04-C46-020** — Production gate: operators can cryptographically verify what was built, from which source/inputs, by which trusted workflow, and that the deployed bytes match.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C46-021** — An approved design/ADR exists for **SBOM, provenance, signing, and release verification** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C46-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C46-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C46-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C46-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C46-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/release.py`, `tests/test_p1_contracts_integration.py::CompatAndRelease`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-004, W-006, W-007, W-009
- **Status:** In progress (7 verified / 14 partial / 4 blocked / 1 not started / 0 N/A)
- **GO impact:** Required evidence
- **Implementation:** `runtime/release.py`
- **Remaining gap:** Local signing key (W-006).


---


## 47. Named accountable owner and escalation path

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C47-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [x] **GAP04-C47-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/GOVERNANCE.md` · Waiver(s): W-001

- [x] **GAP04-C47-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/GOVERNANCE.md` · Waiver(s): W-001

- [x] **GAP04-C47-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/GOVERNANCE.md` · Waiver(s): W-001

- [~] **GAP04-C47-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-006** — Assign a primary accountable owner for GAP-04 with a named role/team and maintained contact mechanism.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-007** — Assign secondary/on-call ownership for operational incidents and security escalation.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-008** — Define ownership for code, policy semantics, cryptography/key management, SRE/operations, release engineering, and adjacent integration contracts.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-009** — Publish a RACI or equivalent responsibility map for normal changes, emergencies, and production GO decisions.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-010** — Define escalation levels and maximum response times for P0 control failures.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-011** — Define handoff procedure when ownership changes teams or personnel.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-012** — Ensure repository metadata, CODEOWNERS/review rules, runbooks, and service catalog use consistent ownership.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-013** — Require owner approval for changes to safety-critical invariants and protocol/schema contracts.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-014** — Define 24x7 or business-hours support expectations explicitly based on service criticality.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-015** — Maintain vendor/dependency escalation contacts where external support is required.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-016** — Test paging/escalation contact paths periodically.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-017** — Record ownership in release evidence and operational dashboards.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-018** — Create a process for orphaned component detection.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-019** — Review ownership at least quarterly or on organizational change.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [!] **GAP04-C47-020** — Production gate: every critical alert, security event, change, and GO/NO-GO decision has an unambiguous accountable party.
  - Note: blocked; No named people (W-001). · Waiver(s): W-001


### Component acceptance evidence

- [~] **GAP04-C47-021** — An approved design/ADR exists for **Named accountable owner and escalation path** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/GOVERNANCE.md` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C47-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/GOVERNANCE.md` · Waiver(s): W-001

- [~] **GAP04-C47-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/GOVERNANCE.md` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-001, W-007

- [!] **GAP04-C47-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-001, W-009

- [~] **GAP04-C47-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/GOVERNANCE.md` · Note: partially implemented; No named people (W-001). · Waiver(s): W-001

- [~] **GAP04-C47-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/GOVERNANCE.md` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (4 verified / 11 partial / 11 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/GOVERNANCE.md`
- **Remaining gap:** No named people (W-001).


---


## 48. Architecture decision record (ADR)

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C48-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; ADRs proposed, not accepted. · Waiver(s): W-001

- [x] **GAP04-C48-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C48-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; ADRs proposed, not accepted.

- [x] **GAP04-C48-006** — Create ADRs for offline authority model, lease semantics, trusted time, persistence substrate, audit integrity, reconciliation strategy, fencing, identity/authentication, encryption, and rollout compatibility.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-007** — State context/problem, decision, alternatives considered, decision drivers, security implications, operational implications, and consequences.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-008** — Record rejected alternatives and why they were not selected.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-009** — Link each ADR to requirements, code modules, schemas, tests, and affected adjacent components.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-010** — Assign ADR status: proposed, accepted, superseded, deprecated, or rejected.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C48-011** — Require review by relevant architecture/security/operations owners for safety-critical ADRs.
  - Note: blocked (W-001) · Waiver(s): W-001

- [~] **GAP04-C48-012** — Version ADRs in source control and prohibit silent in-place rewriting of historical decisions.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: git history not available in candidate

- [~] **GAP04-C48-013** — Reference superseding ADRs rather than deleting obsolete rationale.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: convention stated

- [x] **GAP04-C48-014** — Include explicit threat assumptions and failure model for distributed/offline decisions.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C48-015** — Include compatibility/migration implications for decisions affecting persisted data or wire protocols.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C48-016** — Audit major implementation divergence from accepted ADRs.
  - Note: not started

- [~] **GAP04-C48-017** — Use ADR review as a release/change gate for material architecture changes.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: process

- [x] **GAP04-C48-018** — Maintain an ADR index by control/component.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C48-019** — Review stale ADR assumptions after major dependency/platform changes.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: process

- [~] **GAP04-C48-020** — Production gate: every safety-critical architectural choice is documented, reviewable, and traceable to implementation evidence.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; ADRs proposed, not accepted.


### Component acceptance evidence

- [~] **GAP04-C48-021** — An approved design/ADR exists for **Architecture decision record (ADR)** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C48-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C48-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C48-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [~] **GAP04-C48-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; ADRs proposed, not accepted.

- [~] **GAP04-C48-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/ADR/`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (12 verified / 10 partial / 3 blocked / 1 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/ADR/`
- **Remaining gap:** ADRs proposed, not accepted.


---


## 49. Requirements traceability matrix

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C49-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; No reviewer approvals (W-001). · Waiver(s): W-001

- [x] **GAP04-C49-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [~] **GAP04-C49-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: partially implemented; No reviewer approvals (W-001).

- [x] **GAP04-C49-006** — Create a unique immutable requirement/control ID for each GAP-04 requirement, including the original 100 checks and all post-audit missing-component controls.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-007** — Map each requirement to implementation module/function, configuration/policy field, schema, test case, operational monitor, evidence artifact, owner, and status.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-008** — Distinguish implemented, partially implemented, verified, waived, not applicable, and blocked states.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-009** — Require objective evidence references rather than narrative claims of completion.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [~] **GAP04-C49-010** — Version the matrix with each release and retain historical snapshots.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: versioned per release; no history yet

- [~] **GAP04-C49-011** — Automate links to CI test results and artifact digests where possible.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: local run ids

- [~] **GAP04-C49-012** — Flag orphan requirements with no implementation and orphan code/tests with no traced requirement where relevant.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: orphans flagged for requirements only

- [x] **GAP04-C49-013** — Map P0/P1/P2 priority and production gate impact.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-014** — Include adjacent-system dependencies and the exact versions used for verification.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-015** — Track known gaps and waiver IDs directly in the matrix.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [!] **GAP04-C49-016** — Require reviewer/approver and verification date for controls marked complete.
  - Note: blocked (W-001) · Waiver(s): W-001

- [x] **GAP04-C49-017** — Generate release summary from the matrix rather than manually maintained status prose.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [x] **GAP04-C49-018** — Add CI checks preventing deletion/renumbering of control IDs without migration.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [~] **GAP04-C49-019** — Review traceability after every material architecture change.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: process

- [~] **GAP04-C49-020** — Production gate: every claimed satisfied requirement points to reproducible implementation and verification evidence.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: partial


### Component acceptance evidence

- [~] **GAP04-C49-021** — An approved design/ADR exists for **Requirements traceability matrix** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C49-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py`

- [~] **GAP04-C49-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C49-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [~] **GAP04-C49-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: partially implemented; No reviewer approvals (W-001).

- [~] **GAP04-C49-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`, `tests/test_p2_governance.py` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (13 verified / 10 partial / 3 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `tools/build_status.py`, `evidence/CHECKLIST_STATUS.json`, `evidence/RTM.json`
- **Remaining gap:** No reviewer approvals (W-001).


---


## 50. Formal SLO/error-budget specification

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C50-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; Targets proposed only. · Waiver(s): W-001

- [x] **GAP04-C50-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/SLO.md`

- [~] **GAP04-C50-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/SLO.md` · Note: partially implemented; Targets proposed only.

- [x] **GAP04-C50-006** — Define SLIs for safety-readiness availability, local decision latency, durable decision success, reconciliation convergence, policy/revocation freshness, and dependency availability where applicable.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-007** — Set objective targets and measurement windows for each SLI.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-008** — Define which errors count against the budget and which expected partition states do not.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-009** — Define separate objectives for connected and disconnected operating modes where behavior differs.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-010** — Specify maximum tolerated time in stale-policy, unreconciled, safety-not-ready, or degraded states.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-011** — Define data sources and exact metric queries used to calculate each SLI.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-012** — Set alerting burn-rate thresholds and escalation policies.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-013** — Define release/change restrictions when error budget is exhausted.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-014** — Document exclusions carefully and prohibit ad-hoc post-incident exclusion of bad periods.
  - Evidence: `docs/SLO.md`

- [x] **GAP04-C50-015** — Review whether SLOs align with maximum lease and disconnect risk windows.
  - Evidence: `docs/SLO.md`

- [~] **GAP04-C50-016** — Backtest SLO calculations against load/soak/fault-injection results.
  - Evidence: `docs/SLO.md` · Note: partial

- [~] **GAP04-C50-017** — Publish dashboards showing current objective attainment and budget consumption.
  - Evidence: `docs/SLO.md` · Note: dashboard panels

- [!] **GAP04-C50-018** — Assign ownership for each objective.
  - Note: blocked (W-001) · Waiver(s): W-001

- [~] **GAP04-C50-019** — Review targets periodically based on production evidence and risk.
  - Evidence: `docs/SLO.md` · Note: process

- [~] **GAP04-C50-020** — Production gate: measurable reliability/safety objectives and response rules exist before declaring the service production-ready.
  - Evidence: `docs/SLO.md` · Note: pending approval


### Component acceptance evidence

- [~] **GAP04-C50-021** — An approved design/ADR exists for **Formal SLO/error-budget specification** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/SLO.md` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C50-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/SLO.md`

- [~] **GAP04-C50-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/SLO.md` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C50-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C50-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/SLO.md`

- [~] **GAP04-C50-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/SLO.md` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 8 partial / 3 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/SLO.md`
- **Remaining gap:** Targets proposed only.


---


## 51. Incident severity/paging/containment runbook

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C51-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; Not exercised. · Waiver(s): W-001

- [x] **GAP04-C51-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [~] **GAP04-C51-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: partially implemented; Not exercised.

- [x] **GAP04-C51-006** — Define severity levels with concrete GAP-04 examples: split-brain, audit integrity failure, lease verification failure, stale revocation, journal corruption, prolonged partition, data loss, security compromise.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [~] **GAP04-C51-007** — Map severity to paging targets, response times, incident commander role, security involvement, and executive/customer communication requirements.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: roles only; no paging targets

- [x] **GAP04-C51-008** — Provide first-response checks for health, version/config/policy, lease, epochs, storage, dependencies, and recent changes.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-009** — Document safe containment actions: freeze, quarantine, revoke lease, disable rollout, isolate node/site, rotate keys, and preserve evidence.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-010** — Explicitly warn against unsafe actions such as deleting journals, resetting epochs, rolling clocks, or restoring stale backups without authority review.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-011** — Define evidence collection preserving audit chain, logs, traces, state hashes, memory/core dumps where allowed, and artifact versions.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-012** — Provide decision trees for reconnect/reconciliation failures and data-integrity uncertainty.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-013** — Define recovery validation before unfreezing autonomy.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [~] **GAP04-C51-014** — Define post-incident reconciliation and customer/data impact assessment.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: outline only

- [x] **GAP04-C51-015** — Require incident timeline and root-cause analysis for specified severities.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [x] **GAP04-C51-016** — Link runbook steps to tested operator commands/tooling.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [!] **GAP04-C51-017** — Exercise runbooks through game days/tabletops.
  - Note: blocked: needs people (W-001) · Waiver(s): W-001

- [~] **GAP04-C51-018** — Keep offline copies accessible during control-plane outages.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: requirement stated

- [~] **GAP04-C51-019** — Version and review runbooks after incidents/major releases.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: process

- [~] **GAP04-C51-020** — Production gate: responders can contain critical failures without improvising dangerous state manipulation.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: pending exercises


### Component acceptance evidence

- [~] **GAP04-C51-021** — An approved design/ADR exists for **Incident severity/paging/containment runbook** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C51-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [~] **GAP04-C51-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C51-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C51-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`

- [~] **GAP04-C51-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (14 verified / 9 partial / 3 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/INCIDENT_SEVERITY.md`, `docs/RUNBOOK.md`
- **Remaining gap:** Not exercised.


---


## 52. Vulnerability response and end-of-life SLAs

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C52-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; No security contact or scan (W-001/W-009). · Waiver(s): W-001

- [x] **GAP04-C52-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [~] **GAP04-C52-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: partially implemented; No security contact or scan (W-001/W-009).

- [~] **GAP04-C52-006** — Define vulnerability intake channels for internal findings, dependency advisories, researchers, and customers.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: security contact unassigned

- [x] **GAP04-C52-007** — Define severity methodology and remediation SLAs for critical/high/medium/low findings.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-008** — Define emergency patch and release-signing process for critical vulnerabilities.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-009** — Map SBOM components to deployed/supported releases so impact can be assessed quickly.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-010** — Define coordinated disclosure and security contact procedures.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-011** — Define supported release windows and minimum upgrade cadence.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-012** — Publish deprecation and end-of-life timelines with advance notice.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-013** — Define behavior for dependencies/runtimes that reach upstream EOL before GAP-04.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-014** — Require compensating controls/waivers for overdue vulnerabilities with owner and expiry.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [x] **GAP04-C52-015** — Maintain ability to revoke compromised release artifacts/signers.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [~] **GAP04-C52-016** — Track vulnerability remediation to verification tests and release evidence.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: process

- [x] **GAP04-C52-017** — Define customer/operator notification thresholds for exploited or high-impact issues.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [~] **GAP04-C52-018** — Retain forensic/version data needed to identify exposed deployments.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: SBOM + version in health

- [~] **GAP04-C52-019** — Review EOL and vulnerability posture at every release.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: process

- [~] **GAP04-C52-020** — Production gate: supported versions have enforceable security maintenance windows and a tested emergency remediation path.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: not tested


### Component acceptance evidence

- [~] **GAP04-C52-021** — An approved design/ADR exists for **Vulnerability response and end-of-life SLAs** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C52-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [~] **GAP04-C52-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C52-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C52-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md`

- [~] **GAP04-C52-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/VULNERABILITY_AND_EOL.md` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (15 verified / 9 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/VULNERABILITY_AND_EOL.md`
- **Remaining gap:** No security contact or scan (W-001/W-009).


---


## 53. Recurring review process

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C53-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; Reviewers unassigned. · Waiver(s): W-001

- [x] **GAP04-C53-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [~] **GAP04-C53-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: partially implemented; Reviewers unassigned.

- [x] **GAP04-C53-006** — Schedule recurring reviews for access/identity, policy semantics, configuration, dependencies, cryptography, threat model, architecture, capacity, and incident lessons.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-007** — Define review frequency based on risk; security-critical controls should have explicit minimum cadence.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [~] **GAP04-C53-008** — Assign required attendees/approvers for each review domain.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: roles only (W-001)

- [x] **GAP04-C53-009** — Use checklists with evidence references rather than informal meetings.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-010** — Review active exceptions/waivers and force expiration or renewal decisions.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-011** — Review signer/trust-store contents and remove obsolete credentials.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-012** — Review dependency compatibility/CVE status and supported runtime/OS lifecycle.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-013** — Review policy/config drift across sites against approved baselines.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-014** — Review SLO/error-budget and alert quality.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [x] **GAP04-C53-015** — Review capacity assumptions against recent production/load evidence.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [~] **GAP04-C53-016** — Track findings to owners, deadlines, and closure evidence.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: process

- [~] **GAP04-C53-017** — Escalate overdue P0/P1 findings automatically.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: gate integration only

- [~] **GAP04-C53-018** — Retain review records with release/governance evidence.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: requirement stated

- [x] **GAP04-C53-019** — Trigger out-of-cycle review after major incident, security event, architecture change, or cryptographic migration.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [~] **GAP04-C53-020** — Production gate: recurring assurance is scheduled, owned, evidenced, and capable of blocking release for unresolved critical findings.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: no reviews held yet


### Component acceptance evidence

- [~] **GAP04-C53-021** — An approved design/ADR exists for **Recurring review process** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C53-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/REVIEW_PROCESS.md`

- [~] **GAP04-C53-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C53-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [~] **GAP04-C53-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: partially implemented; Reviewers unassigned.

- [~] **GAP04-C53-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/REVIEW_PROCESS.md` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (14 verified / 10 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/REVIEW_PROCESS.md`
- **Remaining gap:** Reviewers unassigned.


---


## 54. Exception/waiver/debt register

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C54-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; Waivers proposed, unapproved. · Waiver(s): W-001

- [x] **GAP04-C54-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C54-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Waivers proposed, unapproved.

- [x] **GAP04-C54-006** — Create a unique ID for every accepted exception, waiver, or known control debt.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-007** — Record affected control/component, risk statement, technical rationale, scope, environment, and why immediate remediation is not feasible.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C54-008** — Assign accountable owner and approving authority.
  - Note: blocked (W-001) · Waiver(s): W-001

- [~] **GAP04-C54-009** — Require compensating controls and evidence that they are deployed.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: compensating controls described, deployment evidence partial

- [x] **GAP04-C54-010** — Set creation date, review date, and hard expiration date.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-011** — Prohibit indefinite waivers for P0 controls without executive/security authority and explicit risk acceptance.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C54-012** — Link each waiver to tracking issue/remediation plan and target release.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: tracking field only

- [x] **GAP04-C54-013** — Surface active waivers in release/GO evidence automatically.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C54-014** — Prevent closed/expired waivers from being silently reopened without new approval.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: convention stated

- [~] **GAP04-C54-015** — Review waivers after related incidents or architecture changes.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: process

- [x] **GAP04-C54-016** — Track aggregate debt by priority/age/owner.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-017** — Define criteria that force a waiver to block production or rollout.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-018** — Retain historical waiver decisions for auditability.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C54-019** — Integrate register status with requirements traceability.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C54-020** — Production gate: every unsatisfied control is visible, owned, time-bounded, and either blocking or explicitly accepted by authorized governance.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: visible but not approved


### Component acceptance evidence

- [~] **GAP04-C54-021** — An approved design/ADR exists for **Exception/waiver/debt register** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C54-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C54-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C54-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [~] **GAP04-C54-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Waivers proposed, unapproved.

- [~] **GAP04-C54-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `docs/WAIVERS.md`, `evidence/waivers.json`, `tests/test_p2_governance.py`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (13 verified / 10 partial / 3 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `docs/WAIVERS.md`, `evidence/waivers.json`
- **Remaining gap:** Waivers proposed, unapproved.


---


## 55. Formal production exit gate

**Priority:** P2  
**Control family:** Governance  

### Checklist

- [!] **GAP04-C55-001** — Assign accountable owner, approver, review cadence, and evidence-retention policy.
  - Note: blocked; Gate implemented; currently NO_GO. · Waiver(s): W-001

- [x] **GAP04-C55-002** — Use stable IDs and version-controlled records so decisions/status changes are traceable.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C55-003** — Define objective completion/approval criteria and prohibit unsupported self-attestation.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C55-004** — Link governance records to implementation, tests, releases, incidents, and exceptions.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C55-005** — Review the control after major incident, architecture change, or release-process change.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Gate implemented; currently NO_GO.

- [x] **GAP04-C55-006** — Define machine-readable GO criteria covering all P0 controls and designated mandatory P1 evidence.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C55-007** — Consume objective artifacts: test results, SBOM/provenance verification, compatibility matrix, traceability matrix, vulnerability status, waivers, SLO baselines, and config/policy validation.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C55-008** — Refuse GO automatically when any required control is missing, failed, stale, unsigned, or supported only by narrative assertion.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C55-009** — Define freshness windows for evidence such as penetration tests, dependency scans, and soak tests.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C55-010** — Bind gate output to exact source commit, build digest, package digest, config class, and target environment.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: archive digest + environment; no source commit (no VCS)

- [x] **GAP04-C55-011** — Require named approvals from engineering, security, operations/SRE, and product/risk owners as appropriate.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Waiver(s): W-001

- [x] **GAP04-C55-012** — Separate technical pass from business acceptance of explicitly permitted residual risk.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C55-013** — Produce a signed/immutable release decision artifact with timestamp and evidence references.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: decision document unsigned · Waiver(s): W-006

- [x] **GAP04-C55-014** — Ensure an older GO decision cannot be replayed for a different artifact or newer environment.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C55-015** — Add gate tests containing intentionally missing/failed evidence to prove fail-closed behavior.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [ ] **GAP04-C55-016** — Integrate gate with deployment admission so a NO-GO artifact cannot enter production accidentally.
  - Note: not started

- [~] **GAP04-C55-017** — Define emergency release procedure with stricter, not weaker, explicit authorization and post-release obligations.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: documented in VULNERABILITY_AND_EOL

- [~] **GAP04-C55-018** — Retain all gate artifacts for the supported release lifetime.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: retention policy pending

- [x] **GAP04-C55-019** — Version the gate policy itself and review changes.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C55-020** — Production gate: production deployment requires a reproducible PASS tied cryptographically/logically to the exact release artifact and mandatory evidence set.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: returns NO_GO today


### Component acceptance evidence

- [~] **GAP04-C55-021** — An approved design/ADR exists for **Formal production exit gate** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C55-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C55-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C55-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [x] **GAP04-C55-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C55-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `runtime/gate.py`, `evidence/gate_decision.json`, `tests/test_p2_governance.py::Gate`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-006, W-007, W-009
- **Status:** In progress (14 verified / 9 partial / 2 blocked / 1 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `runtime/gate.py`, `evidence/gate_decision.json`
- **Remaining gap:** Gate implemented; currently NO_GO.


---


## 56. `MASTER.md` or equivalent master-prompt source

**Priority:** P2  
**Control family:** Documentation  

### Checklist

- [~] **GAP04-C56-001** — Treat the document set as versioned release-controlled artifacts with named ownership and review.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Master authored; approval pending.

- [x] **GAP04-C56-002** — Keep normative requirements synchronized with code, schemas, tests, and manifests.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-003** — Use stable cross-references and automated link/version consistency checks.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-004** — Document assumptions, non-goals, dependencies, and known limitations explicitly.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-005** — Require documentation updates as part of the definition of done for affected controls.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-006** — Recover or author the authoritative master source that defines GAP-04 purpose, scope, invariants, adjacent dependencies, implementation workflow, and acceptance gates.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-007** — Assign a document version and map it to the GAP-04 software/release series.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-008** — Include the 56 post-audit missing components and their control IDs or explicit references to this checklist.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-009** — Define normative versus informative sections so implementers know which statements are requirements.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-010** — Include architecture overview, data/control flows, trust boundaries, state machine, lease lifecycle, partition lifecycle, reconciliation lifecycle, and failure model.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-011** — Document required inputs/outputs and versioned contracts for GAP-01, GAP-05, GAP-12, GAP-13, PLN-07, and `pk_core`.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-012** — Include security assumptions, threat model references, cryptographic profiles, identity model, trusted-time requirements, and key-management dependencies.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-013** — Include persistence, crash recovery, storage pressure, backup/restore, and migration requirements.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-014** — Include test/verification strategy with links to contract, fault-injection, security, performance, and GO-gate evidence.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-015** — Include operational runbooks, health/metrics/logging expectations, alerting, ownership, and escalation references.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-016** — Correct any claims that a file/component is bundled when it is not actually present.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-017** — Add CI/documentation checks for broken links, stale version references, missing required sections, and mismatch with manifest.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [x] **GAP04-C56-018** — Include a machine-readable manifest of normative artifacts if practical.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [!] **GAP04-C56-019** — Require review/approval from architecture, security, operations, and component ownership.
  - Note: blocked (W-001) · Waiver(s): W-001

- [~] **GAP04-C56-020** — Production gate: the repository contains one authoritative, versioned, internally consistent master source that accurately describes what is implemented, what is required, and how production readiness is proven.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d` · Note: pending approval


### Component acceptance evidence

- [~] **GAP04-C56-021** — An approved design/ADR exists for **`MASTER.md` or equivalent master-prompt source** and identifies trust, failure, persistence, compatibility, and operational assumptions.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d` · Note: ADR drafted in docs/ADR (status: proposed); approval requires W-001 · Waiver(s): W-001

- [x] **GAP04-C56-022** — Implementation references are mapped to the control IDs above.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d`

- [~] **GAP04-C56-023** — Automated positive, negative, boundary, failure-injection, and version-compatibility tests required by this section are passing in release CI.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d` · Note: all suites pass locally (evidence/test_results.json); no release CI (W-007) · Waiver(s): W-007

- [!] **GAP04-C56-024** — Security review findings are closed or linked to active, approved, time-bounded waivers.
  - Note: no independent security review yet (W-009) · Waiver(s): W-009

- [~] **GAP04-C56-025** — Health/telemetry/runbook evidence exists for production diagnosis and recovery where applicable.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d` · Note: partially implemented; Master authored; approval pending.

- [~] **GAP04-C56-026** — The requirements traceability matrix lists this component as verified with exact evidence references and reviewer approval.
  - Evidence: `MASTER.md`, `tools/check_docs.py`, `tests/test_p2_governance.py::Docs`, `evidence/test_results.json#local-4beee8cb841d` · Note: listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001) · Waiver(s): W-001


### Exit record

- **Owner:** ________ (unassigned — W-001)
- **Reviewer/approver:** ________ (unassigned — W-001)
- **Target release:** 4.3.0
- **Evidence bundle / CI run:** `evidence/test_results.json` run `local-4beee8cb841d` (local; no release CI — W-007)
- **Waiver(s):** W-001, W-007, W-009
- **Status:** In progress (18 verified / 6 partial / 2 blocked / 0 not started / 0 N/A)
- **GO impact:** Governance
- **Implementation:** `MASTER.md`, `tools/check_docs.py`
- **Remaining gap:** Master authored; approval pending.


---


## Final Production-GO Checklist

- [ ] All 20 P0 component sections are verified with objective evidence.
- [ ] No unresolved P0 waiver is expired, unowned, or missing compensating controls.
- [ ] Required P1 controls defined by the release gate are verified.
- [ ] P2 ownership, traceability, incident, vulnerability, review, waiver, and master-document controls are active.
- [ ] Compatibility matrix matches the exact versions deployed.
- [ ] Release artifact signature, provenance, SBOM, checksums, and dependency lock are verified.
- [ ] Crash/restart, partition/reconnect, concurrency, fuzz, adversarial, integration, performance, and soak qualification evidence is current.
- [ ] Backup/restore and quarantine/emergency-disable procedures have current exercise evidence.
- [ ] Effective production configuration and policy artifacts are signed/verified and their digests are recorded in the GO bundle.
- [ ] Formal production exit gate returns PASS for the exact build digest and target environment.
- [ ] Signed/immutable GO evidence is retained with reviewer/approver identities and timestamp.
- [ ] Any post-GO deviation automatically reopens affected controls and triggers the configured change/incident governance process.

## Checklist metrics

This document contains 56 component sections. Each section includes implementation-specific controls plus universal architecture, security, compatibility, verification, observability, and evidence requirements. Control IDs are stable within checklist version 1.0.0 and should be referenced from issues, commits, tests, ADRs, runbooks, CI evidence, and release manifests.
