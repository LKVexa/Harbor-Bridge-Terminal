# INV-41 - Capability security

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements in `CHECKLIST.json`

INV-41 models least-authority, in-process capability references. A component can use only references explicitly bound into its immutable `Holder`; delegation can only attenuate; references can be revoked through shared membranes; and no resource-returning global registry is provided.

## Security boundary

Version 4.2.0 hardens the package against accidental/API-level authority forgery. `Reference` objects are sealed, immutable, process-local, non-serializable, and bound to an explicit `Authority` domain. `Holder` objects reject cross-domain references and cannot be mutated through the supported API. This is **not** a hostile-code sandbox for arbitrary Python/native code in the same interpreter. Use process, Wasm, VM/microVM, or hardware isolation for adversarial workloads. See `SECURITY.md`.

## Core API

- `Authority(policy)` - creates one explicit authority domain from an immutable resource/operation policy.
- `Authority.grant(resource, operations)` - mints a sealed reference within that bootstrap policy.
- `Authority.bind_holder(name, held)` - creates an immutable holder and rejects foreign authority domains.
- `Holder.use(alias, operation)` - invokes only an explicitly held capability.
- `Holder.delegate(alias, operations)` / `Reference.attenuate(operations)` - mints an equal-or-narrower reference.
- `Membrane.wrap(reference)` / `Membrane.revoke()` - provides revocation that follows attenuated and nested-wrapped descendants.

`PK_REFERENCE/1` and `PK_MEMBRANE/1` result schemas are documented under `schemas/`.

## Dependency-free verification

From the directory containing `inv41_capability_security`:

```text
python inv41_capability_security/tests/test_primitives.py -v
python -m inv41_capability_security.selfcheck
python -O -m inv41_capability_security.selfcheck
```

These checks require only the Python standard library and remain active under optimized mode.

## Estate integration

The 100-item gate adapter remains in `component.py` and requires the external `pk_core` package:

```text
python inv41_capability_security/tests/test_component.py -v
python -m pk_core run INV-41 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-41 --out conformance/PK_GATE_RESULTS.json
```

This archive does **not** contain `pk_core`; integration/gate tests therefore skip unless `PK_CORE_PATH` or an installed package supplies it. The post-update audit records that as an unresolved integration dependency rather than treating skipped tests as a pass.

## Responsibility

Own ambient-authority elimination at the application object/API level: each resource is reached through an explicitly supplied capability; delegation can only narrow; holders cannot recover an unheld capability by resource name; and revocation can invalidate all live descendants behind a membrane.

### Owns

- Explicit authority domains and sealed resource references
- Immutable holder binding
- Delegation/attenuation
- Cross-authority rejection
- Process-local reference semantics
- Revocation membranes

### Explicitly does not own

- Isolation from hostile code executing in the same Python interpreter
- Hardware capability enforcement
- Network capability grants
- Policy authorship
- Placement or scheduling
- OS/process/VM sandboxing

## Operational baseline

- **Day 0:** run the standalone test suite and self-check; then run the `pk_core` gate when the integration dependency is available.
- **Day 1:** bind only reviewed bootstrap policies, archive machine-readable gate evidence, and block rollout on failed requirements.
- **Day 2:** re-run the standalone suite and estate gate for every implementation, policy, or contract change; revoke affected membranes for emergency containment.

The previous release artifact is the rollback target.

## 4.3.0 remediation (missing-component checklist)

4.3.0 executes the *INV-41 v4.2.0 Missing Component Remediation Checklist* (24 sections, 85 non-verified audit IDs). Decision record: `docs/ADR-0001-explicit-capabilities.md` (PROPOSED). Where to look:

| Area | Files |
|---|---|
| Governance | `OWNERS.json`, `OWNERS.md`, `CODEOWNERS`, `EXCEPTIONS.json`, `BLOCKERS.json` |
| Requirements & traceability | `requirements/REQUIREMENTS.json`, `docs/REQUIREMENTS.md`, `evidence/TRACEABILITY.{json,md}` |
| Contracts | `contracts/INTERFACES.json`, `contracts/SUPPORT_MATRIX.json`, `schemas/`, `tests/vectors/` |
| New runtime modules | `errors.py`, `audit.py`, `config.py`, `identity.py`, `telemetry.py`, `resilience.py`, `broker.py`, `preflight.py`, `isolation.py` |
| Security analysis | `docs/THREAT_MODEL.md`, `docs/threats.json`, `docs/DATA_PROTECTION.md`, `tools/mutation.py` |
| Operations | `docs/OPERATIONS.md`, `docs/OBSERVABILITY.md`, `ops/alerts.json`, `docs/COMPATIBILITY.md` |
| Verification & release | `tools/run_ci.py`, `tools/bench.py`, `tools/scale_soak.py`, `tools/compat.py`, `tools/estate_gate.py`, `tools/build_release.py`, `tools/release_gate.py`, `.github/workflows/ci.yml` |

```text
python inv41_capability_security/tools/run_ci.py            # every suite + generators + gates (PR tier)
python inv41_capability_security/tools/mutation.py          # security-control mutation testing
python inv41_capability_security/tools/release_gate.py      # production exit gate (currently NO_GO)
```

Production verdict: **NO_GO**. Everything that can be built and verified inside the repository is; what remains needs people or infrastructure this archive does not contain (named owners and approvals, a licence, a release-signing identity, KMS, pk_core, a hostile-code isolation runtime, a multi-runtime CI matrix, a deployment). Each is a named blocker in `BLOCKERS.json`; see `REMEDIATION_REPORT.md`.
