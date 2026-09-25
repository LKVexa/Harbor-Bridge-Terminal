# INV-32 Test program (v4.3.0)

| Tier | Where | Prereqs | Status |
|---|---|---|---|
| Pure unit (model) | `tests/test_model.py` | none | runs |
| Contract/schema/conformance | `tests/test_security.py::SchemaConformanceTest`, `conformance_check.py` | none | runs |
| Adapter simulation | `tests/test_adapter_contract.py` | none (FakeHypervisor) | runs |
| Durability / fencing / crash injection | `tests/test_durability.py` | Linux (fcntl) | runs |
| Controls (config/health/resilience/quota/telemetry/bootstrap) | `tests/test_controls.py` | none | runs |
| Security & fuzz (deterministic seeds) | `tests/test_security.py` | none | runs |
| Release tooling / bench gate | `tests/test_release.py` | none | runs |
| pk_core adapter | `tests/test_component.py`, `tests/test_pk_core_compat.py` | pk_core | skips (BLOCKED) |
| Single-host integration (real hypervisor) | — | disposable VMs + HyperFlux | BLOCKED |
| Multi-controller integration | — | consensus lease store | BLOCKED |
| Performance | `bench.py` | reference HW for gating | runs (sandbox numbers) |
| Soak / fleet scale / disaster | — | CI capacity, real env | BLOCKED |

Determinism: fuzz tests use fixed seeds (`20260922`, `4242`, `99`); the controller rig uses `random.Random(7)`.
Destructive hypervisor tests must only target disposable infrastructure (never production hosts).
