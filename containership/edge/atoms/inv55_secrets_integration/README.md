# INV-55 - Secrets integration

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`  
**Master prompts:** referenced by the series, but `MASTER.md` is not present in this standalone repository snapshot (WAIVERS.json W-010).

Secrets integration lets an application reference a secret by name and obtain its value at run time without embedding that value in ordinary configuration, logs, or application images. Access is scoped per application and per secret, values are versioned, and broker-mediated access is lease-bound.

## Responsibility

Own secret resolution for applications: reference-by-name, per-application scoping, versioned rotation, leased access, and redaction of secret-bearing diagnostics.

## Owns

- Secret references in configuration
- Per-application, per-secret access scoping
- Versioned rotation semantics
- Leased broker-mediated access
- Redaction of secret-bearing reference objects and audit records

## Explicitly does not own

- Secret storage backends
- Key custody and HSMs
- Identity issuance
- Application logic
- Durable audit storage

## Non-goals

- Persisting production secrets
- Holding root keys
- Issuing identities
- Treating an in-process Python object as a hard confidentiality boundary

## Interfaces

- `resolve` - PK_SECRET_RESOLVE/1 - name to a leased, versioned capability
- `rotate` - PK_SECRET_ROTATE/1 - add a new version
- `scope` - PK_SECRET_SCOPE/1 - which applications may resolve which secrets

## 4.3.0: standalone production runtime

4.3.0 adds `runtime/`, a stdlib-only service layer around the reference model: a public wire boundary (`PK_SECRET_RESOLVE/1`, `ROTATE/1`, `SCOPE/1`, JSON schemas in `schemas/`), signed workload-token authentication, deny-by-default tenant-scoped authorization, a provider interface with a HashiCorp Vault KV v2 adapter (TLS/mTLS, AppRole), retry/deadline/circuit-breaker/bulkhead/quota, lease cache with offline-deny, read-only failover, operator freeze, a hash-chained audit log, metrics/logs/traces, health/readiness, declarative configuration with overlays, provenance, two-person activation and rollback, and a bootstrap tool. `tools/` adds a secret scanner, SBOM, benchmark, status/traceability builder and the production exit gate.

**Status:** `EXECUTION_REPORT.md` shows where each of the 100 checklist components stands. `COMPONENT_STATUS.json` and `TRACEABILITY.json` are the machine-readable versions. The gate returns **NO_GO**: nothing has been approved by a named human, the Vault adapter has only been run against an in-repo wire double, and `pk_core` is still absent.

```text
sh inv55_secrets_integration/tools/ci.sh        # compile, scan, sbom, status, 110 tests, -O run, gate
python3 inv55_secrets_integration/tools/bootstrap.py inv55_secrets_integration/deploy/config/base.json --author you --source ref
```

Documentation map: `docs/requirements/` (REQUIREMENTS, NFR, VERSIONING), `docs/architecture/` (ADR-0001, deployment patterns), `docs/security/` (threat model, fail-closed matrix, identity/policy, at-rest, memory/privacy), `docs/operations/` (runbooks, incident response, backup/restore, rollout, SLO, FMEA, capacity, telemetry, reviews), `docs/governance/` (ownership, compatibility, waivers, approvals), `SECURITY.md`, `CONTRIBUTING.md`, `CODEOWNERS`.

## Security behavior in 4.2.0 (unchanged in 4.3.0)

The executable reference model no longer subclasses `str` for secret-bearing values. This prevents accidental plaintext materialization through inherited string operations such as slicing, encoding, case conversion, replacement, joining, and indexing. Secret-bearing objects redact `repr`, `str`, and formatted output, reject serialization, and are only revealed through `SecretBroker.use()` after broker, application, secret-name, revocation/retirement, and lease-expiry checks.

Application and secret identifiers are validated before they can enter diagnostics, audit events are structured and exclude values, lease TTLs must be finite and positive, and the broker fails closed if its monotonic clock moves backwards.

A lease cannot retroactively erase plaintext that application code has already received. Where post-delivery expiry or revocation is required, the production provider or downstream service must enforce the credential lifetime.

## Service-level objectives

- **no leakage** - zero secret values in component logs or errors (error budget: no budget)
- **scoping** - zero component-mediated resolutions outside scope (error budget: no budget)
- **resolution latency** - p99 under 5ms from cache (error budget: 1% may exceed)

The latency SLO is contractual only in this standalone snapshot; there is no benchmark harness here yet. See `MISSING_COMPONENTS.md`.

## Verification

From the directory containing this package:

```text
python -m compileall -q inv55_secrets_integration
python -m unittest discover -s inv55_secrets_integration/tests -v
python -O inv55_secrets_integration/tests/test_secrets_primitives.py
```

The focused security tests can run without the external `pk_core` package by installing import-only test stubs. The conformance tests in `tests/test_component.py` require the real `pk_core`; when it is not importable they are skipped rather than reported as passes.

With the full estate installed:

```text
python -m pk_core list
python -m pk_core run INV-55 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-55 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2 intent

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-55`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-55`; a `NO_GO` verdict blocks rollout, and `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

These are intent-level instructions, not a complete production runbook. The repository still lacks provider integration, deployment automation, dashboards, incident procedures, backup/recovery material, and other production artifacts listed in `MISSING_COMPONENTS.md`.

## Repository audit status

`AUDIT_REPORT.md` records the 4.2.0 audit/fix/hardening pass and verification evidence. `MISSING_COMPONENTS.md` is the post-fix production-completeness audit. The latter intentionally distinguishes implemented reference behavior from checklist requirements that still lack concrete code, schemas, tests, operational assets, or external dependencies in this repository.
