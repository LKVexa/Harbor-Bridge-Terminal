# INV-55 - Secrets integration

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Release verdict:** `NO_GO` (`evidence/exit_gate.json`) - blocking items are listed in `docs/governance/waiver-register.md`.

Secrets integration lets an application reference a secret by name and obtain its value at run time without embedding that value in ordinary configuration, logs, or application images. Access is scoped per tenant, application and secret; values are versioned; access is lease-bound; every decision is authenticated, authorized, durably audited and explainable.

## Layout

| Path | What |
|---|---|
| `inv55_secrets_integration/service.py` | `SecretsService` - the production facade for the three protocols |
| `inv55_secrets_integration/providers/` | provider abstraction, in-memory reference provider, HashiCorp Vault adapter |
| `inv55_secrets_integration/{identity,resilience,audit,telemetry,config,errors,secretvalue,bootstrap}.py` | authn/authz, resilience, tamper-evident audit, observability, configuration, error taxonomy, secret container, bootstrap |
| `inv55_secrets_integration/schemas/` | JSON Schemas (2020-12) for every request, response, error and the config |
| `inv55_secrets_integration/component.py`, `contract.py` | 4.2.0 pk_core reference model/contract (needs the external `pk_core`) |
| `config/` | base config + env/site overlays |
| `tests/` | contract, adversarial, Vault (fake over HTTP/TLS and gated real), resilience/fault-injection, fuzz/property, concurrency, schema/fixture, tooling suites |
| `tools/` | secret scan, benchmark + regression gate, traceability matrix, release evidence + SBOM, exit gate |
| `evidence/` | generated traceability, release evidence, SBOM, benchmark baseline, exit-gate verdict |
| `docs/` | architecture, requirements (SRS/NFR), security (threat model...), operations (runbooks, IR), governance, performance - index at `docs/README.md` |

## Interfaces

- `resolve` / `use` / `revoke` - `PK_SECRET_RESOLVE/1` - name -> leased, versioned capability -> value
- `rotate` / `retire` - `PK_SECRET_ROTATE/1` - add a version (idempotency key, optional CAS) / retire or destroy one
- `set_scope` - `PK_SECRET_SCOPE/1` - which applications of a tenant may resolve which secrets

Errors are `PK_SECRET_ERROR/1` objects with stable codes (`docs/architecture/outcome-semantics.md`).

## Quick start

```text
pip install -r requirements-test.txt                     # test-only deps; runtime has none
python -m unittest discover -s tests -v                  # 130 tests; 6 skip without Vault / pk_core
python -m inv55_secrets_integration.bootstrap --config-dir config --env prod --check
python tools/secret_scan.py .
python tools/benchmark.py --compare evidence/benchmark_baseline.json
python tools/release_evidence.py && python tools/exit_gate.py
INV55_VAULT_ADDR=http://127.0.0.1:8200 INV55_VAULT_TOKEN=<dev-token> python -m unittest tests/test_vault_real.py
```

A skipped mandatory test (real Vault, pk_core conformance) is **not** a pass; the exit gate returns `NO_GO` while they skip.

## Status against the v4.2.0 missing-component checklist

`evidence/traceability.json` maps all 100 components to artifacts, tests and residual gaps:

| Priority | Implemented | Partial | Open |
|---|---|---|---|
| P0 | 19 | 9 | 3 |
| P1 | 16 | 15 | 3 |
| P2 | 16 | 15 | 4 |

"Partial" and "Open" items need something outside this repository (a real Vault run, pk_core, owner approvals, a licence choice, signing-key custody, the identity/policy services, deployment platform, fleet measurements). Each is a row in `docs/governance/waiver-register.md`.
