# ADR-0001: Governed Placement Path

- Status: PROPOSED
- Approver: UNASSIGNED
- Supersedes: none
- Date proposed: 2026-09-23

## Context
4.2.0 decided placement from caller-mutated NodeReports with no identity, policy revision, or durable state.

## Decision
Add `scheduler.Scheduler` as the production path. `engine.place` remains the v1 contract and is unchanged. All policy inputs come from a signed, versioned `ConfigStore` revision.

## Consequences
Two paths exist; v1 is deprecated per docs/COMPATIBILITY.md. Every v2 decision names its config revision and code digest.
