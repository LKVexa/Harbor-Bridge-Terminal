# ADR-0001 — GAP-02 production layer architecture (GAP02-MC-49)

- **Status:** Proposed (awaiting accountable-owner acceptance)
- **Date:** 2026-09-22
- **Accountable owner:** _UNASSIGNED — must be named by the GAP-02 owner; this build cannot assign one_
- **Reviewers:** _UNASSIGNED_

## Context
v4.2.0 shipped a sound three-state model but no production probes, signing envelope, executor, or operations surface (55 missing components).

## Decision
1. A single promotion gate (`production/evidence.promote`) is the only path from probe evidence to report state; evidence kinds are split into *proof* and *observation*, and observations can never produce `present`.
2. All host access goes through an injectable `Host` seam with bounded reads, absolute-path no-shell commands and deadlines — the same code runs against real hosts and synthetic fixtures.
3. Sweeps are built fresh and published by a single reference swap (generation id), never merged.
4. Signing is behind `Signer`/`Verifier` protocols; the in-package `HmacSigner` is a reference implementation only and is disabled by default config. Production binds GAP-07.
5. Stdlib only; optional OpenTelemetry.

## Consequences
- Platforms/devices without an authoritative API stay `unprobed` (Apple GPU scheduling, consumer NVIDIA without ECC reporting, NPUs without a configured runtime check). This under-reports on purpose.
- Physical-hardware verification, sibling integration and the pk_core gate remain open and are tracked BLOCKED in `COMPONENT_STATUS.json`.
