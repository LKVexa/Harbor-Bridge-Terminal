# ADR-002 — Capability model: worlds → descriptors → rights

**Status:** Accepted · **Date:** 2026-09-22

## Decision
* A **world** (WIT) fixes the maximum capability set for a workload class; worlds are least-privilege and there is no all-capabilities world (`WitSurface.test_worlds_are_least_privilege`).
* The **PolicyEngine** (deny-by-default, tenant-scoped) decides whether a workload may receive a world and which preopens/rights (`tests/test_authz.py::Policy`).
* Every grant is minted as an **INV-42-style descriptor** with a stable content-derived ID, owner, scope, rights and provenance `{decision digest, actor}`. Children may only attenuate; revocation cascades (`tests/test_authz.py::Descriptors`, `test_adversarial.py::Races.test_parallel_grant_revoke_check`).
* Every guest operation re-checks its descriptor (revocation is effective on the next call, not the next instantiation) — `test_integration.py::test_quota_quarantine_revocation`.

## Rejected alternatives
Implicit capabilities per environment (ambient-authority risk); string-named capabilities without descriptors (no revocation/provenance).

## Open
The real INV-42 service must implement the `DescriptorTable` interface (mint/derive/check/revoke/live). The in-process table is the reference.
