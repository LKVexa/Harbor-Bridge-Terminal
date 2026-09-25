# ADR-0001 — Separate orchestration and bulk-data channels for high-performance VM I/O (Nexus)

| Field | Value |
|---|---|
| Status | **Proposed** (not Accepted — approval by accountable_owner and security_owner pending in `governance/APPROVALS.json`) |
| Date | 2026-09-22 |
| Requirement | INV-35-C010 (also C011, C021, C024, C031) |
| Deciders | accountable_owner, security_owner, runtime_platform_owner |

## Context

INV-35 exists to make virtio-style I/O fast (shared rings, notification
suppression, vhost-style offload keeping the VMM out of the hot path) without
letting a guest corrupt the host. The upstream series names the technology
"Nexus" and the function "separate orchestration and bulk-data channels". The
v4.2.0 audit found no decision record, no pinned Nexus specification and no
structural separation beyond interface names.

## Decision

1. **Two planes, one state.** Orchestration (`ControlPlane`) and bulk data
   (`Datapath`) are separate entry points over a shared `Runtime`. They require
   **disjoint capability actions**; a bulk credential cannot reconfigure,
   re-register or un-quarantine, and a control credential cannot move data.
2. **Validate a snapshot, then use it.** Every descriptor is validated against
   the queue's registered guest-memory regions on a host-owned snapshot
   (TOCTOU-safe). Production backends must copy descriptors out of guest memory
   before validation and apply IOVA translation only after it.
3. **Fail closed everywhere security-relevant.** Any refusal is a stable coded
   error (`schemas/errors/error_codes.json`), audited in a hash-chained log, and
   never mutates queue/quota/idempotency state.
4. **Nexus binding by specification, not by code.** "Nexus" is pinned as the
   *interface + conformance-fixture set* in `release/NEXUS_SPEC_MANIFEST.json`
   (interfaces `PK_VIRTQUEUE_SUBMIT/1`, `PK_VIRTQUEUE_COMPLETE/1`, error schema
   `INV35_ERROR/1`, fixtures digest). Any production backend claiming Nexus
   conformance must pass those fixtures byte-for-byte.
5. **Reference model stays dependency-free.** Performance claims about
   production line rate are the backend's; the reference model measures policy
   overhead only.

## Consequences

* ＋ A compromised vhost worker cannot escalate to the control plane (tested T01).
* ＋ Conformance is portable: fixtures + schemas are the contract.
* − Per-call capability checks cost CPU on the bulk path; mitigated by the
  measured verification cache (100 µs → 42 µs p50 per submit/complete cycle,
  `docs/performance/PERFORMANCE_MODEL.md`).
* − Two planes sharing one process means a process crash affects both;
  mitigated by journal recovery into FROZEN.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Single API with role flags | Ambient authority; one credential class would reach everything |
| Separate processes per plane | Correct long-term for production; out of scope for the reference model, recorded as TD for the backend |
| Trust ring index movement | Explicit non-goal in `contract.py` |

## Review

Re-review on any change to `io_model.py`, capability actions, or the Nexus spec
manifest; scheduled in `governance/REVIEW_SCHEDULE.json` (REV-ARCH).
