# Changelog - INV-66

## 4.3.0 - 2026-09-22

Executes the 71-component / 1,420-item *INV-66 v4.2.0 Missing Components Implementation & Verification
Checklist*. The ledger is `release/mc_status.json`, and the annotated checklist is
`governance/INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.executed.md`. **Not production-certified:
the exit gate is NO_GO.**

### Added: production layer (`production/`, stdlib + `cryptography` only)
- Authentication boundary: EdDSA JWT (issuer/kid/aud/exp/nbf/lifetime/jti, optional single use) and mTLS SPIFFE peers. A caller-supplied username is no longer an identity.
- RBAC with org → tenant → lattice scopes, capability roles, groups, workload principals, deny-overrides and escalation-free delegation. Overlay bindings carry journaled creator authority and optimistic concurrency.
- Provenance: mandatory digest pinning in prod, Ed25519 signatures bound to digest + component name, signer scope/revocation/expiry, attestations with trusted builders, and a registry-resolver slot.
- Organisation policy engine with a fixed precedence lattice and refused-exemption reporting. A GAP-13 (OPA data API) client that is version-pinned, cached for fresh positive answers only, and fails closed.
- Durable journal as the source of truth: fsync + cross-process flock, hash chain, Ed25519 anchors, torn-tail recovery, compaction with legal holds and checkpoints, verifiable export, background verification, and a SIEM exporter with a durable checkpoint.
- Config generations: `PK_ECP_CONFIG/1` schema, layered env/site overrides, provenance, N distinct approvers (author excluded, never lower than the active bar), CAS activation and rollback, and a dry-run policy impact query.
- Lifecycle state machine, quotas, load shedding, deadlines, retry with jitter, circuit breaker, dependency health and degraded mode, freeze/quarantine/emergency disable (release needs 2 votes).
- INV-63 delivery adapter (`PK_ECP_DELIVER/1`, idempotent on decision id, resumable after a crash), GitOps ingestion, and a cross-lattice inventory with pagination.
- Single-writer lease with fencing epochs for HA over shared storage.
- HTTPS API (`/v1/admit|rbac|audit|inventory|explain|quarantine`, `/healthz`, `/readyz`, `/version`, `/metrics`), a service entry point, and a CLI (verify/anchor/export/backup/restore/validate-config/demo).
- Prometheus metrics with bounded series, structured JSON logs with redaction, W3C trace context propagated to GAP-13 and INV-63.

### Added: contracts, tests, operations
- 10 generated JSON Schemas, a pinned error registry (32 codes), and frozen compatibility fixtures.
- 135 tests (132 run and pass here; 3 pk_core tests skip because pk_core is not bundled): unit, contract (cross-checked against reference `jsonschema`), security T01–T17 + R1–R3, fuzz, fault, multi-process concurrency, HTTP/mTLS end-to-end against stub peers, disaster/partition.
- Benchmark/soak harness, perf gate, capacity model, CI lane runner, RTM, requirements spec, MASTER.md (derived), recurring review extraction, waiver register, SBOM, provenance, evidence bundle, signed manifest, exit gate.
- ADR-0001 (PROPOSED), topology, source of truth, lifecycle, partition semantics, precedence, interfaces, threat model, telemetry policy, runbooks for day 0/1/2, backup and incident.

### Fixed: defects found while applying (all have regression tests)
- D1 `import inv66_enterprise_wasm_control_plane` failed without `pk_core` (hard import in `__init__`).
- D2 A rollback to the bootstrap generation was impossible.
- D3 SPIFFE `.`/`..` path segments were accepted and could alias another tenant.
- D4 Two unleased processes appending to one journal would fork the hash chain.
- D5 `ecp_shed_total` was declared but never incremented.
- D6 Replay was O(n²) (5k admissions → 4.3 s startup).
- D7 Adapter endpoints accepted `file://` / `ftp://` (local file read / SSRF).
- D8 A `None` principal on activation crashed instead of returning a typed refusal.
- D9 A lattice-only read filter was authorised against the wrong scope.
- D10 Health schema growth briefly made new fields required (breaking change caught by a frozen fixture).
- R1 (adversarial review, HIGH) A config change could lower its own approval bar.
- R2 (MEDIUM) A tenant admin could remove an org-admin's deny binding.
- R3 (LOW) Idempotency keys were not scoped to the principal.

### Deprecated
- `control_plane.ControlPlane` is kept only as the pk_core behavioural fixture (DEP-01). Removal is planned for 5.0.0.


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
