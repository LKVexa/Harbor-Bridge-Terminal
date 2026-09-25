# Changelog — INV-42

## 4.3.0 — 2026-09-22

This is the remediation pass against the 42-component missing-component checklist (junkyard chop-shop). The wire format `PK_DESCRIPTOR/2` is unchanged, so 4.3.0 is wire-compatible with 4.2.0.

### Fixed

- **Partial commit on mint failure.** `open()` committed the entry and consumed the number *before* minting the tag, so a failure while minting left an orphaned live entry. The descriptor is now fully built before any state changes.
- **Hostile-subclass bypass surface.** `from_wire()` accepted `dict` subclasses and `str`/`int` subclasses whose `keys`/`__eq__` could lie. Exact `type()` checks are now enforced on the payload and on every field.
- **Log injection through error text.** Attacker-supplied schema strings were echoed in full in error messages. They are now truncated.
- **Package import without pk_core.** The package root imported `component` eagerly, so nothing in the package could be imported without `pk_core`. The certification adapter now loads lazily.

### Added

- Runtime:
  - `outcomes.py`: the formal outcome taxonomy.
  - `audit.py`: a tamper-evident hash-chain/MAC audit sink.
  - `telemetry.py`: health, Prometheus metrics, redacted structured logs, W3C tracing, and an explain view.
  - `transport.py`: a TLS 1.3 mTLS profile.
  - `delegation.py`: policy-controlled delegation by re-issuance.
  - `adapters.py`: INV-41 and INV-13 adapters.
- New `DescriptorTable` hooks:
  - `DescriptorTable(observer=..., key_provider=...)`
  - `fingerprint`
  - process-wide `emergency_disable()` / `INV42_EMERGENCY_DISABLE`
  - `ComponentDisabled` and `KeyUnavailable` error codes
- Tests: 17 → 58, covering fuzzing, adversarial cases, concurrency, fault injection, audit, telemetry, transport, delegation, integration, and operations tooling.
- Tooling: `certify.py`, `bench.py`, `coverage_gate.py`, `release.py`, `traceability.py`, `exit_gate.py`, `rollout.py`, `review_due.py`.
- Supply chain and CI:
  - `pyproject.toml`
  - `SPEC_MANIFEST.json`
  - WIT contract
  - event and delegation schemas
  - CI and review workflows
  - alerts and dashboards
- Governance and operations docs:
  - Planning and ownership: `NFR.md`, `THREAT_MODEL.md`, `OWNERS.yaml`, ADR-0002 through ADR-0004.
  - Policies: `SLO.md`, `TELEMETRY_POLICY.md`, `VULNERABILITY_POLICY.md`.
  - Procedures: `ROLLOUT.md`, `INCIDENT_RUNBOOK.md`, `RELEASE.md`, `KEY_MANAGEMENT.md`.
  - Registers and legal: `WAIVERS.json`, `REVIEWS.json`, `LICENSE`, `NOTICE`.

### Production status

The exit gate verdict is **NOT_ELIGIBLE**. Three blocker waivers stay open, each tied to something only the owner or the platform can supply:

- W-001: the `pk_core` pin;
- W-004: the KMS/HSM signing key;
- W-005: the deployment PKI.

## 4.2.0 — 2026-09-22

Security and correctness hardening pass.

### Fixed

- Closed an authority-forgery flaw in which a caller that knew a live table id, descriptor number, and type could construct a `Descriptor` object accepted by the issuing table.
- Replaced unauthenticated `PK_DESCRIPTOR/1` with authenticated `PK_DESCRIPTOR/2`; the HMAC binds schema, table id, number, and resource type.
- Added strict `from_wire()` parsing and explicit rejection of unknown fields, malformed payloads, tampering, and legacy v1 descriptors.
- Corrected checklist-evidence placement so secure-default, isolation/adversarial, typed-schema, explicit-capability, and structured-error evidence maps to matching checklist requirements.
- Eliminated the false-green test posture where the repository could report success with every test skipped when `pk_core` was absent; standalone runtime/security tests now execute independently.

### Hardened

- Added thread-safe allocation/resolve/close operations and a concurrent uniqueness test.
- Made table identities issuer-generated and added per-table 256-bit keys.
- Redacted authentication tags from descriptor `repr` and prohibited table pickling.
- Added fork detection to prevent cloned tables from issuing divergent authority under one identity.
- Added live-table and total-session allocation ceilings with typed failure codes.
- Removed the unbounded closed-number set; authenticity lets an absent, valid descriptor be classified as permanently closed without retaining every closed number.
- Added explicit `destroy()` lifecycle revocation and best-effort key zeroization.
- Added bounded non-secret status/security counters and read-only entry snapshots.
- Added stable machine-readable error codes.

### Documentation and contracts

- Added JSON Schemas for descriptor v2, close v2, and table status v1.
- Added security model, compatibility/migration notes, operations guidance, and ADR-0001.
- Corrected the README claim about `MASTER.md`; the file is not present in this archive and remains an audited missing artifact.
- Added a post-update missing-component audit and machine-readable inventory.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

- Replaced bare behavioral `assert` statements with `_verify()` so checks survive `python -O`.
- Added explicit failure when expected refusal paths do not occur.
- Added stdlib conformance tests and version pinning.
- Added descriptor carried-type verification and constant-time table-id comparison.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
