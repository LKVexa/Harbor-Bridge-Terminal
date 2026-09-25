# ADR-0002: Fencing And Journal

- Status: PROPOSED
- Approver: UNASSIGNED
- Supersedes: none
- Date proposed: 2026-09-23

## Context
In-process lock cannot prevent two scheduler processes from double-booking.

## Decision
Journal-first commit with a fencing epoch checked atomically at append time. File-based epoch authority for one host; a linearizable store is required for multi-host (EXT).

## Consequences
Stale owners are refused (FENCED) and cannot write. Multi-host deployment remains blocked until a consensus store is bound.
