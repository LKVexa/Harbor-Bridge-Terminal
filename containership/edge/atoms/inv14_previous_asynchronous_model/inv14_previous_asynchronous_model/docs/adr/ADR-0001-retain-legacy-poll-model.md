# ADR-0001 — Retain the legacy poll model (INV-14) under a governed deprecation

## Status

PROPOSED

Drafted by the v4.3.0 build on 2026-09-22. It becomes APPROVED only when the
accountable owner and a governance reviewer named in `governance/OWNERS.json`
sign it; the build cannot approve its own decision record.

## Context

Components built against WASI 0.2 `wasi:io/poll` still exist and cannot all be
rewritten at once. The model is simple and works, but pollables do not compose
across component boundaries and a blocking poll is an availability hazard.
INV-15 (new asynchronous ABI) is the successor.

## Decision

Keep INV-14 running, deprecated, behind the v4.3.0 control surface:
bounded waits (60 s hard ceiling, monotonic clock), authenticated ownership
(capability tokens), admission ceilings, lifecycle with emergency disable,
tamper-evident audit, bounded telemetry, and INV-15 shims with a parity-gated
migration state machine. No new consumers are written against it.

## Limits

- No composition across component boundaries (refused with `PK_POLL_FOREIGN_OWNER`).
- No unbounded blocking; no poll over 60 s; no empty sets.
- Readiness is not persisted across restart (see `checkpoint.py`, RST-1..4).
- The Python reference is not proof of WASI interoperability; that gate is open.

## Migration target

INV-15 New asynchronous ABI, via `migration.py` (forward and reverse shims,
LEGACY → DUAL_STACK → CANARY → MIGRATED, rollback from DUAL_STACK/CANARY).

## Retirement criteria

Per `governance/EOL_POLICY.json`: registry closed to new consumers, then
waiver-only admission, then removal. Removal requires zero registered consumers
outside MIGRATED and no live waiver.

## Consequences

Legacy consumers keep working with explicit, audited limits. Operators gain a
kill switch and migration visibility. The cost is a larger control surface
around a deprecated primitive, which is itself retired with INV-14.
