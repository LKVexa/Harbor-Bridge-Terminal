# INV-44 - Wasm hardening system

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

> Source-package note: the original archive referenced MASTER.md, but that file
> was not present in the supplied archive. Version 4.2.0 no longer claims that
> missing source material is bundled. See `MISSING_COMPONENTS.md` for the
> evidence-based post-update completeness audit.

The Wasm hardening system is a fail-closed reference model for a hardened Wasm
execution boundary: the declared hardening set must be complete, compiled
output must receive an explicit verification verdict, execution is fuel
metered, and linear memory is capped.

## Responsibility

Own the hardened Wasm runtime configuration: require the full hardening set,
verify compiled-module output before execution, enforce fuel and memory ceilings
at run time, and refuse execution under a partial hardening configuration.

## What 4.3.0 adds (missing-components pass)

4.3.0 applies `INV44_v4.2.0_Missing_Components_Professional_Checklist.md` to
this repository. Status of the 19 missing components (`COMPONENTS_STATUS.json`):

| # | Component | Status | What still closes it |
|---:|---|---|---|
| 1 | Original master-source artifact | **BLOCKED** | Owner supplies the original MASTER.md (or a signed release archive holding it) with its source-side digest. |
| 2 | Pinned pk_core dependency | **BLOCKED** | Owner supplies pk_core (version + sha256 or a registry coordinate). |
| 3 | Python packaging/build metadata | **IMPLEMENTED_LOCAL** | Reproducible-build digest comparison across two hosts; publication target. |
| 4 | License/notice artifacts | **BLOCKED** | Owner chooses a license. |
| 5 | CI/release automation | **IMPLEMENTED_LOCAL** | The workflow has never run on a real GitHub runner; branch protection and a protected release environment are repository settings. |
| 6 | Concrete PK_WASM_HARDENING/1 schema | **IMPLEMENTED_LOCAL** | Peer (INV-45/INV-29/PLN-04) consumption tests need those components. |
| 7 | Concrete PK_WASM_INSTANCE/1 schema | **IMPLEMENTED_LOCAL** | Cancellation and deadlines are declared in the schema but not enforced by the Python model, which has no long-running execution to cancel. |
| 8 | Production Swivel/compiler/runtime integration | **BLOCKED** | Swivel (or chosen successor) pinned by digest, a real compile of fixtures, and Spectre PoC evidence on target CPUs. |
| 9 | Cryptographic compiled-output verifier | **PARTIAL** | HMAC is symmetric (asymmetric keys/KMS pending); structural validation is not semantic validation; no Swivel output to verify. |
| 10 | Signed provenance/attestation | **PARTIAL** | Asymmetric/Sigstore signing and key custody; a hosted builder identity. |
| 11 | Declarative configuration/provenance subsystem | **IMPLEMENTED_LOCAL** | Approval workflow for config changes (who may activate) is not bound to people. |
| 12 | Identity/capability enforcement layer | **PARTIAL** | No real IdP, mTLS, node/peer attestation, or KMS; keys are constructor arguments. |
| 13 | Tenant isolation integration | **PARTIAL** | Host isolation (process/VM, caches, kernel, FS, network, devices) is not provable in-process and needs the component 8 runtime. |
| 14 | Tamper-evident security audit log | **IMPLEMENTED_LOCAL** | Where the head anchor and log are shipped (WORM storage, retention) is an operations decision. |
| 15 | Production observability stack | **PARTIAL** | No Prometheus/Alertmanager/tracing backend provisioned; fuel_exhaustions is declared but only counted when callers route traps through metrics. |
| 16 | Performance certification suite | **PARTIAL** | Real Swivel overhead vs. baseline, soak/fleet/power runs, approved SLO thresholds. |
| 17 | Fault/disaster testing suite | **PARTIAL** | Node/VM/site/network partition and failover testing needs an environment. |
| 18 | Operations/governance artifacts | **PARTIAL** | Owner names people, approves the ADR, signs waivers. |
| 19 | External machine-readable release evidence | **PARTIAL** | pk_core PK_GATE_RESULTS and a human release approval. |

Audit matrix: **27 verified / 56 partial / 17 missing** (was 11 / 31 / 58).
Release gate: **NO_GO** (`python release_gate.py`, exit 3) — by design until
pk_core gate results and a human release approval exist.

New modules (all stdlib-only): `wasm_verify.py` (structural Wasm validator +
digest/toolchain/profile-bound receipts), `capability.py` (authenticated
principals, sealed capability tokens, ambient-import refusal), `gateway.py`
(the tenant-bound PK_WASM_INSTANCE/1 admission path), `audit_log.py`
(hash-chained tamper-evident log), `config.py` (declarative, versioned,
atomically activated configuration), `observability.py`, `lifecycle.py`,
`errors.py`, `schema.py` + `schemas/`, `provenance.py` (in-toto/DSSE),
`release_gate.py`, `bench/perf_suite.py`, `tools/differential_v8.py`.

Use `TenantGateway.instantiate(...)` for anything production-shaped. The
Boolean `Engine.instantiate(output_valid=...)` path is **deprecated**: it is
kept only for the pk_core component model and trusts its caller.

## Security invariants (4.2.0, still in force)

- Every feature in `REQUIRED_HARDENING` is load-bearing; removing one prevents instantiation.
- `Instance` objects are factory-gated through `Engine.instantiate()` so callers cannot accidentally bypass hardening and verification checks.
- Public runtime accounting state is immutable; fuel, page, consumption, and trap state cannot be rewritten by ordinary callers.
- Step cost must be a strictly positive integer. Zero-cost, negative, Boolean, and non-integer costs fail closed.
- Memory values are strict non-negative integers and are enforced against an immutable per-engine ceiling.
- Security-sensitive labels reject control characters to prevent log/diagnostic injection through engine or module identifiers.
- Fuel and memory accounting updates are serialized with a private lock to prevent same-process race corruption.
- The runtime enforcement model lives in `runtime.py` and has no `pk_core` dependency, so its security tests still run when the external conformance framework is unavailable.
- Package initialization is lazy for the optional `pk_core` layer; importing the standalone runtime no longer fails solely because the external framework is absent.
- `CHECKSUMS.sha256` covers every shipped repository file other than the manifest itself and is verified by `tools/audit_repository.py`.

## Owns

- Required hardening-feature completeness
- Post-compilation output-verdict enforcement
- Fuel metering and exhaustion behavior
- Linear-memory ceiling enforcement
- Fail-closed refusal of partially hardened configurations
- Atomic same-process fuel and memory accounting

## Explicitly does not own

- The Wasm specification
- A production compiler or JIT implementation
- The module source
- The host image
- Workload placement
- Host-level sandboxing outside this reference model

## Non-goals

- Implementing a Wasm compiler
- Extending the Wasm specification
- Running unhardened for performance
- Treating this Python reference model as a production Wasm sandbox by itself

## Interfaces

- `configure` - `PK_WASM_HARDENING/1` - declared hardening feature set and applied state
- `instantiate` - `PK_WASM_INSTANCE/1` - verified, metered module instance

Both are concrete JSON Schemas under `schemas/` (4.3.0), enforced by `schema.py`.

## Service-level objectives

- **hardening completeness** - zero instances executed with a partial hardening set (error budget: no budget)
- **output verification** - zero instances created after a negative verification verdict (error budget: no budget)
- **memory ceiling** - zero instances growing past their configured ceiling (error budget: no budget)

## Running the local audit/tests

From this repository directory:

```text
python -B tests/run_all.py            # 51 tests; pk_core, PACKAGING and NODE_WASM lanes skip with reasons
python -B -O tests/run_all.py         # same suite under the optimizer
python -B tools/audit_repository.py   # repository-local audit
python -B release_gate.py             # writes evidence/RELEASE_EVIDENCE.json; NO_GO exit 3
python -B bench/perf_suite.py         # MEASURED results, thresholds UNAPPROVED
python -B tools/differential_v8.py    # verifier vs. V8 WebAssembly.validate (needs node)
```

The local runtime and repository-invariant tests use only the Python standard
library. If `pk_core` is installed elsewhere, set `PK_CORE_PATH` and the two
additional conformance tests will run instead of skipping:

```text
set PK_CORE_PATH=C:\path\to\pk_core_parent
python tests\test_component.py
```

When the wider framework is available, the repository also expects the normal
`pk_core` list/run/gate/verify workflow used by the surrounding component
estate. The supplied archive does not contain `pk_core` itself or a lockfile
pinning it, so this release does not claim that external gate was executed here.

## Day-0 / day-1 / day-2

- **Day 0:** run the standalone tests, provide/install the approved `pk_core` dependency, then generate and archive an initial evidence ledger.
- **Day 1:** run the external conformance gate before rollout; reject partial hardening and negative output-verification verdicts.
- **Day 2:** rerun tests and the external gate on every runtime/configuration change and verify the evidence chain against the previous trusted head.

This is a reference enforcement component, not yet a complete production Wasm
hardening stack. The exact remaining production components are enumerated in
`MISSING_COMPONENTS.md` and `POST_AUDIT_MATRIX.json`.
