# ADR-0001 — Transient-execution defense: read-back posture, fail-closed co-tenancy

**Status:** PROPOSED — drafted 2026-09-22 in the 4.3.0 remediation pass. **Not approved.** Approval needs the accountable owner named in `governance/OWNERS.json` (currently unassigned). Until then remediation item 05 stays open and the production gate stays NO_GO.
**Controls:** C001, C002, C005, C007, C008, C010, C012, C013

## Context

Transient-execution flaws (Spectre-class, L1TF, MDS, MMIO stale data, …) let one tenant infer another's data through shared micro-architectural state. Mitigations are imperfect, cost measurable performance, differ per CPU/kernel/microcode, and new classes keep appearing. A placement system must know, per node, which mitigations are *actually* in force before it lets mutually distrusting workloads share hardware.

## Decision

1. **Source of truth is the node's own read-back** (`/sys/devices/system/cpu/vulnerabilities/*`, SMT control), collected by `collector.py`. CPU model, kernel version and configuration intent are never evidence of a mitigation (C004).
2. **Posture is authenticated, fresh and provenance-bound**: collector envelopes are HMAC-signed with per-node enrolled keys, sequence-numbered (replay-proof), epoch-tagged (split-brain-proof) and expire. Posture older than `min(collector TTL, config TTL)` is treated as absent.
3. **Fail closed everywhere**: unknown / stale / unattested / partially mitigated (`… BHI: Vulnerable`) / unmeasured-cost / GAP-02-contradicted mitigations do not satisfy a requirement; unreadable SMT state is treated as SMT on; core scheduling is only credited when attested.
4. **Requirements come from a versioned, digest-sealed policy** (`policy/default_policy.json`) keyed by workload trust class, PLN-04 isolation tier and INV-34 CPU lineage. The pair requirement is the union of both sides.
5. **INV-43 decides, it does not place**: SCH-01 calls the filter adapter (`placement.py`) and receives eligible nodes plus structured refusals.
6. **Posture is stateless, controls are not**: a restart forgets all posture (restart closed); quarantine/freeze are rebuilt from the audit chain.
7. **Mandatory vs optional (C007)**: mandatory = read-back, attestation, freshness, fail-closed decision, audit, refusal codes. Optional = service transport (`service.py`) when embedded in-process, cost-aware selection, automatic SMT disable (not implemented; non-goal for 4.3.0).

## Functional scope across contexts (C012)

| Context | Supported in 4.3.0 | Notes |
|---|---|---|
| Cloud / datacenter Linux (x86-64, arm64) | Yes (collector reads sysfs) | Hypervisor guests see the *guest* view; host posture must come from a host collector. |
| Near-edge Linux | Yes, same collector | Power/thermal cost unmeasured (item 36 BLOCKED). |
| Far-edge / RTOS / non-Linux | **No** | No read-back source → every mitigation `unknown` → cross-tenant refused. |
| Windows / macOS hosts | **No** | Unsupported deployment pattern (C008). |

## Non-functional requirements (C013) — PROPOSED

- Decision latency p99 ≤ 2 ms in-process (measured 0.46 ms, `evidence/perf/baseline.json`).
- Availability: a decision service outage must never yield a permit; SCH-01 must treat INV-43 unreachability as refusal.
- Consistency: per-node linearizable (single registry lock); no cross-replica consistency claimed (single instance, see ADR notes in RECOVERY.md).
- Determinism: same inputs + same policy/config digests ⇒ same verdict (property-tested).

## Unsupported deployment patterns / non-goals (C008)

- Running the HTTP service on a non-loopback address without TLS (refused at construction).
- Multi-replica active/active registries (not designed; split-brain is only defended per-node by epochs).
- Implementing, enabling or tuning mitigations; applying microcode; placing workloads; CPU procurement.
- Treating CPU generation or documentation as mitigation evidence.

## Consequences

Every cross-tenant permit now costs: an enrolled collector, a benchmark-supplied measured cost per active mitigation, and a fresh envelope. Fleets without those get refusals — by design.
