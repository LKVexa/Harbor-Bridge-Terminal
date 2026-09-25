# Changelog - INV-62

## 4.3.0 - 2026-09-23

Missing-components pass: the supplied *INV-62 v4.2.0 Missing Components Engineering Completion Checklist*
(94 MC items) was applied. Status per item is in `conformance/mc_status.json`: 67 engineered (awaiting human
review), 15 partial, 9 need an owner decision, 3 need an external runtime or hardware. **The exit gate is NO_GO.**

### Added
- `production/` control plane (stdlib only): typed wire protocols with version negotiation and limits (`wire.py`,
  `schema.py`), PKT1 authentication with key rotation and replay protection, default-deny authorisation (`auth.py`),
  error/outcome model (`errors.py`), lifecycle machines and degraded modes (`lifecycle.py`), link health with
  hysteresis/flap/staleness (`health.py`), fenced site leases with quorum (`election.py`), precedence-aware routing
  with decision records and explain view (`policy.py`), config schema/overlays/secrets/generations/rollback
  (`config.py`), WAL + snapshot persistence with optional AES-GCM (`persistence.py`), hash-chained audit
  (`audit.py`), metrics/logs/traces with governance (`telemetry.py`), retry/deadline/admission/breaker/idempotency
  (`resilience.py`), the `TopologyService` boundary, reference client, adjacent-layer adapters, deterministic bootstrap.
- Engine: `iter_by_distance`, `distances`, `candidates`, `remove`, `disconnect`, `clone`, `from_snapshot`,
  `TopologyLimits`/`CapacityExceeded`, residency labels, `measured_at` on links, revision counter, adjacency index.
- 7 JSON Schemas + error registry (`schemas/`), 22 conformance fixtures, 45 SHALL requirements with generated
  SPEC/RTM, 21 docs (architecture, ADR draft, NFR, semantics, interfaces, compatibility, capacity, security,
  threat model, failure catalog, performance, observability, runbooks, incident response, support, governance,
  ownership, testing, master-source status, wasmCloud pin status), ops dashboards/alerts, waiver and debt registers.
- 15 new test suites (147 tests in total), CI runner with 18 fail-closed lanes, benchmark + perf gate, reproducible
  release build with manifest/SBOM/provenance/signature verification, exit gate, `pyproject.toml`, CI workflow.

### Fixed (found while applying the checklist)
1. Identifiers were silently `strip()`ped, so `"x"` and `"x\n"` aliased one node — now rejected.
2. Neighbour lookup scanned every link per heap pop (O(E) per step) — adjacency index.
3. Token bucket drained on a backward clock step — elapsed time clamped at zero.
4. WAL chain digest was computed over the record *including* its MAC on write but excluding it on read, so any
   restart after two records refused to start — digest now computed before the MAC.
5. Health trackers created for already-registered links started UNKNOWN, so the first failed probe marked a
   healthy uplink DOWN (bypassing hysteresis) — trackers are seeded from the link state.
6. An anonymous flood could drain a victim tenant's admission bucket — admission now runs after authorisation.

Found by an independent adversarial review of the 4.3.0 candidate and fixed before release (regressions in
`tests/test_review_regressions.py`):
7. Spent nonces were memory-only, so a captured mutating credential replayed after a restart — spends are now
   persisted (WAL + snapshot) before the request proceeds.
8. Removing a lease holder left its lease valid and renewable, locking the site out — leases are revoked on
   removal/quarantine and re-checked on renew/validate.
9. Link-health hysteresis was not snapshotted, so state after restart differed from before — trackers are persisted.
10. Probes in a rejected batch mutated live health trackers (shallow copy) — copy-on-write per batch.
11. Far-future `at`/`measured_at` made links permanently "fresh" — rejected beyond 30 s skew.
12. Idempotency keys were not bound to the caller; `explain()` leaked decision existence across tenants; WAL replay
    under tightened limits could brick startup; trackers leaked on node removal; refused requests grew the WAL
    unboundedly — all fixed (principal-bound fingerprint, uniform answer, replay with maximal limits + live refusal
    of limits below current size, cleanup, size-triggered compaction with expired-nonce pruning).

### Performance
Wire resolve at 1 000 nodes: p50 9.3 ms → about 1 ms (lazy early-terminating search, per-revision partition cache).

### Compatibility
Public engine API is backward compatible except identifiers with surrounding whitespace (now rejected).
`tests/test_component.py` expects 4.3.0.

## 4.2.0 - 2026-09-22

Repository audit, correctness repair, hardening, and post-fix gap audit.

### Correctness fixes

- Added `topology.py` as a dependency-free executable topology engine.
- Added and now retain the mandatory cloud → region → site → device parent hierarchy.
- Fixed `Topology.partitioned(site, cloud=...)`: the supplied cloud node is now actually used, must exist, and must be cloud-tier.
- Fixed partition semantics to test live-path reachability to the designated cloud instead of looking for any off-site `control` capability.
- Fixed coordinator election so only explicitly eligible nodes can win; a site without a candidate fails closed with `NoCoordinatorCandidate`.
- Reworked the sample estate to include a region and an eligible site gateway while preserving the 5 ms on-site GPU versus 82 ms cloud-route example.

### Hardening

- Reject duplicate nodes instead of silently overwriting topology state.
- Reject unsupported tiers, invalid parent relationships, cross-site device parents, empty identifiers, and malformed capability collections.
- Reject self-links, dangling links to unregistered nodes, non-Boolean link state, and negative/NaN/infinite/non-numeric latency.
- Added `set_link_state()` so health changes do not silently rewrite measured latency.
- Added deterministic shortest-path tracking and a deterministic JSON-serializable diagnostic snapshot.
- Moved stable element metadata into `metadata.py` so it does not depend on `pk_core`.
- Made package import lazy with respect to the external `pk_core` conformance layer.

### Verification hardening

- Added 10 standalone stdlib unit tests covering hierarchy, routing, partitions, election, invalid inputs, fail-closed references, and diagnostic snapshots.
- Verified those tests under both normal Python and `python -O`.
- Direct execution of `tests/test_component.py` now exits non-zero when `pk_core` is unavailable instead of returning success with the conformance class skipped.
- Updated the conformance version pin to 4.2.0.

### Documentation/audit

- Removed the unsupported README claim that a bundled `MASTER.md` exists.
- Clarified that the declared logical interfaces do not yet have bundled typed schemas/WIT/RPC contracts.
- Added `AUDIT_REPORT.md` with the post-fix missing-component inventory and verification limits.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: expected-refusal checks were hardened so a missing refusal cannot silently retain a default finding.
- `tests/test_component.py`: added stdlib conformance coverage for 100 findings, optimised-mode parity, and version pinning.
- Added `VERSION` and `__version__`.

### Defects fixed

- Unknown origin and dangling-node traversal no longer produce incidental `KeyError` failures.
- Self-links and negative latency are rejected.
- Empty sites fail explicitly rather than being treated as partitioned by vacuous truth.
- Empty-site election no longer leaks `min()`'s generic `ValueError`.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
