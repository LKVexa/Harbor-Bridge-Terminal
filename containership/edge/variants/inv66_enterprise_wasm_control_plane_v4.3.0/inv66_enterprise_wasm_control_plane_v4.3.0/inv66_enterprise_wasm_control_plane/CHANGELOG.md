# Changelog - INV-66

## 4.3.0 - 2026-09-23

Production remediation pass executing `INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md`
(71 components, 1,420 items, 12 program gates). Per-item record: `governance/CHECKLIST_STATUS.md`.

### Added — runtime (stdlib + `cryptography`)
- `service.py` production service: journal-first state, authenticated/authorized admission, idempotency,
  quotas, bulkhead shedding, deadlines, freeze/quarantine with TTL + ticket, lifecycle state machine,
  transactional outbox to INV-63, inventory, explain, audit query/export, access review, config
  activation with two-person rule, optimistic concurrency, privilege-escalation guard and rollback.
- `store.py` durable hash-chained journal with fsync, torn-tail recovery, corruption refusal, lease/epoch
  fencing under `flock`, sealed archive segments, HMAC snapshots and external WORM anchors.
- `identity.py` JWS bearer verification (EdDSA/HS256, iss/aud/lifetime/jti replay, mTLS `cnf` binding).
- `provenance.py` digest-pinned images, Ed25519 signature verification, signer expiry, attestation policy.
- `rbac.py` org/tenant/lattice capability model with groups, service principals, expiry, deny-wins.
- `config.py`, `schema.py`, `schemas/*.json` typed PK_ECP_ADMIT/RBAC/AUDIT/ERROR/CONFIG v1 contracts.
- `errors.py` stable error catalog; `resilience.py` retry/breaker/deadline/bulkhead/token bucket;
  `adapters.py` GAP-13, INV-63, INV-64 adapters + WORM sink; `gitops.py`; `observability.py`;
  `http_api.py`; `backup.py`; `cli.py` (`inv66 serve|validate-config|verify|backup|restore`).
### Added — verification, governance, operations
- 66 tests (52 new + 11 retained v4.2 engine tests + 3 pk_core-gated): service E2E, contracts vs reference jsonschema, security/fuzz,
  durability/fault injection/DR, multi-process HA races, live-HTTP integration.
- `tools/bench.py` perf gate (fsync on): p99 3.9 ms sequential, ~440/s, shedding verified, bounded RSS.
- MASTER.md (generated, digest-pinned), REQUIREMENTS, RTM, ADR, ownership, architecture, threat model,
  API/compatibility, operations/runbooks/incident response, testing, supply chain, waivers, SBOM,
  acceptance evidence, production exit gate, CI workflow, Dockerfile, systemd unit, rollout, alerts, dashboard.
### Fixed (found while executing the checklist)
- Deeply nested requests crashed canonical JSON with `RecursionError` (fuzz suite) — now rejected.
- Concurrent writers in separate processes could fork the hash chain (multi-process race test) —
  appends now re-sync from disk under an exclusive lock and check the fencing epoch.
- Unbounded memory growth of in-memory journal/decisions (bench RSS gate) — compaction + bounded cache.
### Compatibility
- `control_plane.ControlPlane` (4.2 in-process engine) retained unchanged; package import no longer
  requires `pk_core` (`PK_CORE_AVAILABLE` flag).

## 4.2.0 - 2026-09-22

Second audit and hardening pass.

### Security and correctness

- Extracted the local admission/audit engine to `control_plane.py` so it can be verified without `pk_core`.
- Hardened malformed-input handling, including missing component names, non-canonical JSON values, duplicate names, invalid identities, and invalid policy configuration.
- Defensively copied and froze activated RBAC/registry/signer policy to prevent caller-side policy mutation.
- Replaced live mutable audit/forwarded exposure with defensive snapshots.
- Bound every audit decision to a canonical manifest SHA-256 digest, manifest size, component count, monotonic sequence, and previous hash.
- Added domain separation to the SHA-256 audit record hash.
- Added component-count and manifest-size limits and serialized admission/audit mutation with an `RLock`.

### Verification and packaging

- Added 11 dependency-light unit/security tests, including optimized-mode and concurrent-admission coverage.
- Corrected README packaging metadata: `MASTER.md` is not present in this archive.
- Added `AUDIT_REPORT.md`, local `VERIFICATION.json`, and a 71-item post-update `MISSING_COMPONENTS.md` gap inventory.
- Bumped package/version pins to 4.2.0.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::ControlPlane.admit: forwarded list stored the caller's manifest by reference, so post-admission edits (e.g. swapping image to an unapproved registry) bypassed admission -> deepcopy on forward
- component.py::ControlPlane._record: audit entry aliased the decision dict returned to the caller, so mutating the return value silently rewrote history -> deepcopy entry
- component.py::ControlPlane.admit: malformed manifest (no components, missing image, image without registry) crashed with KeyError; empty components list was admitted -> refused with reasons

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
