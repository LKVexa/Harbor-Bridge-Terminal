# Changelog - INV-58

## 4.3.0 - 2026-09-22

Execution of `INV58_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (41 work packages MC-001..MC-041) through the junkyard chop shop. All 4.2.0 invariants preserved: one retry owner per route, bounded total attempts, strict/fail-closed SPIFFE mapping, bounded bypass evidence, bounded route registry, copy-on-write revisioned route migration.

### Added (executable)
- `service.py` `MeshLayerService`: single boundary enforcing validate -> authenticate -> authorize -> lifecycle/freeze/quarantine -> admission -> execute -> journal/audit/metrics for every operation; tenant-keyed registries, evidence and journals; idempotent, fenced route migration; version negotiation; payload ceilings; health/readiness/stall detection; status surface; explain view; sealed snapshot/restore; two-person break-glass.
- `authz.py`: boundary matrix for 17 operations, SPIFFE and signed-token authentication (audience, TTL, skew, single-use nonce, fail-closed key outage), deny-by-default capability policy with separation of duties, 16 stable decision codes.
- `config.py` + `secret_refs.py`: `PK_MESH_CONFIG/1`, secure defaults, env/site overlays, structural+semantic validation that rejects any security downgrade or literal secret, provenance, atomic activation with optimistic concurrency, automatic rollback on failed post-activation probe, operator rollback by digest.
- `audit.py`: hash-chained, HMAC-sealed, bounded audit trail with anchor and optional 0600 append-only JSONL sink.
- `resilience.py`: retry-safety classification, full-jitter bounded backoff executor with deadline/cancel, circuit breaker, token-bucket admission with per-tenant fair share, lifecycle FSM, fencing tokens, freeze/quarantine switches.
- `telemetry.py`: metric catalogue (rate/errors/latency/saturation/backlog/resource) with label-cardinality bounds, structured JSON logs with keyed pseudonyms, W3C trace context.
- `integrity.py`: artifact manifest verification (provenance fields, signature, digest, approved version, revocation).
- `errors.py`: `PK_MESH_ERROR/1` envelope, 22 stable codes.
- 7 new schemas, 18 golden fixtures, tools (`rtm`, `gen_fixtures`, `bench`, `bootstrap`, `run_tests`, `release_gate`, `checklist_status`), CI workflow, `pyproject.toml`.
- Docs: requirements (SHALL ids), ADR-001 (PROPOSED), interfaces, threat model (+JSON, 18 threats), failure taxonomy, performance/capacity, SLO, runbooks, incident response, security policy, backup/restore, telemetry policy, review process, residual risks. Ops dashboards/alerts. Governance: RTM (100 rows), ownership roles, waiver/debt/deprecation register, BOM, compatibility matrix.

### Changed (compatibility impact)
- SPIFFE mapping now also refuses an uppercase scheme, an empty `?`/`#`, and path characters outside `[A-Za-z0-9._-]` (SPIFFE ID spec). Peers emitting such IDs fail with `E_IDENTITY_UNMAPPABLE` (DEP-01). No other payload change; all `/1` interfaces unchanged.

### Defects found by this pass's own tests and fixed
1. Config activation replaced the admission controller, so in-flight requests released into the new one and raised `release without acquire` (test_config_swap_during_traffic).
2. Concurrent duplicates of one idempotency key both executed (revision 2) - now reserved before execution (test_idempotency_key_race_executes_once).
3. A frozen component answered mutations with `E_NOT_READY` instead of `E_FROZEN`.
4. `urlsplit` lower-cased `SPIFFE://` so an uppercase scheme was silently normalised and accepted (fuzz).
5. An empty query/fragment (`...?`, `...#`) was silently dropped and accepted (fuzz).
6. Path characters outside the SPIFFE charset (`,`, `;`, non-ASCII) were accepted (fuzz).
7. Redaction replaced the whole status entry of the dependency named `key` with `***REDACTED***`.
8. `PK_MESH_CONFIG-1.schema.json` omitted 7 keys the validator requires (schema drift).
9. RTM referenced its own output and the release record, which can never resolve before generation.
10. Performance: every decision record deep-copied the whole active config, so boundary latency grew with tenant count (200-vs-1 tenant p50 ratio ≈1.3, now ≈1.0; boundary reconcile p99 ≈144 µs → ≈90 µs). Found by the per-tenant overhead benchmark; baseline re-recorded after the fix.
Review finding (not test-found): the unknown-tenant check ran before authentication, letting unauthenticated callers probe tenant existence; moved after authorization with an identical denial code.

### Verification
See `AUDIT_REPORT.md` (v4.3.0 section) and `release/ACCEPTANCE_RECORD.json`. Engineering gate PASS; production NO_GO with named blockers (owners, ADR approval, independent review, MASTER.md, pk_core pin, Istio range, licence, signing key, and the PARTIAL/BLOCKED RTM rows).

### Known residual limitations
RR-01..RR-08 in `docs/RESIDUAL_RISKS.md`; TD-01..TD-03 in `governance/waivers.json`.

## 4.2.0 - 2026-09-22

Repository audit, correctness fix, security hardening, test expansion, and post-update gap audit.

### Correctness and resilience

- Fixed retry-ownership contract violation: `reconcile()` can no longer leave retries active in both app and mesh simply because the multiplicative total fits the budget. Exactly one layer owns retries, or neither does when the budget is one/no retries are requested.
- Preserved the existing `reconcile()` dictionary keys and added `budget`, `effective_attempts`, and a stable decision `reason`.
- Added `RoutePolicyRegistry`, a thread-safe, revisioned, copy-on-write route migration registry with an explicit route-capacity ceiling.

### Security and resource hardening

- Moved dependency-free policy logic to `mesh_logic.py` so critical checks can run without the external `pk_core` framework.
- Made framework-bound package exports lazy so `__version__` and standalone mesh logic import cleanly without `pk_core`; component/contract access still requires the framework.
- Hardened SPIFFE identity mapping: foreign trust domains, empty/dot path segments, query/fragment data, percent-encoded ambiguity, backslashes, invalid trust domains, whitespace/control characters, and malformed URI forms fail closed.
- Hardened bypass detection with strict boolean mTLS input, immutable meshed destination membership, bounded destination configuration, bounded evidence retention, and lock-protected snapshots.
- Added explicit route, identity, destination, evidence, and registry capacity limits.

### Interface and verification

- Added Draft 2020-12 JSON Schemas for `PK_MESH_RECONCILE/1`, `PK_MESH_IDENTITY/1`, and `PK_MESH_BYPASS/1`; the binding contract now references those schema files.
- Added dependency-free unit tests for retry reconciliation, strict identity mapping, bounded/thread-safe bypass detection, and route migration.
- Added schema-validation tests.
- Added audit-artifact consistency tests and changed the framework smoke test to require 100 unique reported findings without falsely forcing every finding to pass.
- Local verification: 22 tests discovered, 20 passed and 2 framework-level tests skipped because `pk_core` is not included in this archive. The dependency-free suite also passes under `python -O`.

### Audit artifacts

- Added `AUDIT_REPORT.md`, `POST_AUDIT_MISSING_COMPONENTS.md`, and `MISSING_COMPONENTS.json`.
- Corrected the README's claim that `MASTER.md` is present; it remains a tracked missing source artifact rather than being silently reconstructed.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::effective_attempts/reconcile: zero, negative, bool or non-int attempts/budget accepted (budget=0 still returned app attempts > budget) -> _attempts() validation raising ValueError
- component.py::map_identity: bare trust-domain SAN ("spiffe://td/") mapped to empty identity "runtime:", non-str input crashed -> refuse with Unmappable

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
