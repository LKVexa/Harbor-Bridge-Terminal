# PLN-04 — Execution Plane

**Version:** 4.3.0 · **Group:** 02_Synthesis_Planes · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 controls in `CHECKLIST.json`; the 48 post-4.2.0 missing components are tracked in `docs/TRACEABILITY.md`.

PLN-04 picks the weakest attested isolation tier that still meets a workload's trust class. From 4.3.0 it also drives that tier's provider through a fenced, durable, audited lifecycle. The runtime uses only the Python standard library (CPython ≥ 3.10).

## Release status: NO_GO (exit 3). This is honest, not a failure.

All technical lanes pass. The gate is NO_GO because human or external inputs are still missing:

- owners
- waiver approvals
- ADR approval
- a licence
- a `pk_core` gate result
- a signed release approval

The full list is in `evidence/RELEASE_GATE.json`. The gate never mints approvals.

| RTM status (M01–M48) | Count |
|---|---|
| PRESENT: implemented and tested in-tree | 23 |
| PARTIAL: in-tree part done; the acceptance gate needs an external dependency or approval | 22 |
| BLOCKED: waiting on an owner-supplied artifact or decision (M02 pk_core, M47 licence, M48 re-certification) | 3 |

## Architecture

```
transport.py (HTTP/JSON)  ->  plane.ExecutionPlane  ->  providers.ProviderRegistry -> ExecutionProvider (process | wasm | command driver)
                                   |  security.py   authn/authz, signed classification, artifact allowlist, attestation + nonce/freshness
                                   |  policy.py     config (PK_PLANE_CONFIG/1), residency, co-residency, rollout / kill switch
                                   |  resilience.py retry+jitter, circuit breaker, fair share, bounded admission queue
                                   |  store.py      durable CAS state (WAL + snapshot), leases with global fencing epochs, backup/restore/migrate
                                   |  observability.py durable audit chain + anchors, event outbox, metrics/logs/traces, SLO
                                   `- runtime.py    dependency-free policy kernel (unchanged API from 4.2.0)
```

## Quick start (development profile)

```python
from pln04_execution_plane import ExecutionPlane, PlaneConfig, ProviderRegistry, ProcessProvider, ReferenceProvider

reg = ProviderRegistry(allow_reference=True)          # production refuses reference providers
reg.register(ProcessProvider())                        # real POSIX process tier
reg.register(ReferenceProvider("microvm"))             # stand-in until a microVM driver is registered
plane = ExecutionPlane(PlaneConfig.load(), reg)
for tier in reg.tiers():
    plane.attest_tier(tier)                            # dev: provider probe only; production: signed evidence
decision = plane.admit({"schema": "PK_ADMISSION/1", "kind": "request", "request_id": "r1",
                        "workload": "w1", "tenant": "t1", "trust_class": "trusted"},
                       command=("/bin/sleep", "60"))
plane.teardown("w1", "t1")
```

The production profile (`config/production.example.json`) refuses to start unless all of these are wired:

- an authenticator
- a classification verifier
- an artifact policy
- an attestation verifier
- a durable state store
- a durable audit sink
- no reference providers

The legacy 4.2.0 API (`Node`, `admit`, `teardown`) is unchanged and still exported.

## Tests and evidence

```bash
python -m unittest discover -s pln04_execution_plane/tests -v        # 76 tests, 3 declared skips
python -O -m unittest discover -s pln04_execution_plane/tests
python pln04_execution_plane/tools/fuzz.py --iterations 5000         # M23
python pln04_execution_plane/tools/perf.py --mode quick --gate       # M22/M27
python pln04_execution_plane/tools/release_gate.py                   # M28 -> evidence/RELEASE_GATE.json
```

Declared skips:

- two `pk_core` certification tests (M02)
- the real `wasmtime` lane, because the runtime is not installed

## Documents

| Document | Contents |
|---|---|
| `MASTER.md` | Replacement master specification (the original is unrecoverable), MR-001…MR-030 |
| `docs/ADR-0001-execution-tier-semantics.md` | Tier order and providers. PROPOSED; it flags the source order's Wasm-before-process divergence. |
| `docs/TRACEABILITY.md` | M01–M48 status, files, tests and residuals |
| `docs/ERRORS.md` | Stable error codes |
| `docs/SECURITY.md` | Security boundary |
| `docs/THREAT_MODEL.md` | Threats, controls and tests |
| `docs/RUNBOOK.md` | Day-0/1/2 procedures and incidents |
| `docs/TELEMETRY.md` | Telemetry, privacy and retention |
| `docs/COMPATIBILITY.md` | Compatibility matrix |
| `docs/PATCH_EOL_POLICY.md` | Patch, vulnerability and EOL policy |
| `ops/*.json` | Owners, waivers, SLO, perf thresholds, alerts, dashboard, external dependencies. All unapproved. |
| `NOTICE.md`, `THIRD-PARTY-NOTICES.md` | Licence status (not declared) and third-party code (none) |
