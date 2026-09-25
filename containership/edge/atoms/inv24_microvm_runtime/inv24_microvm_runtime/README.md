# INV-24 - MicroVM runtime

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements in `CHECKLIST.json`; 64 missing-component work packages in
`../docs/checklist/` with closure status in `../docs/CLOSURE_REPORT.md`.

The microVM runtime is the Firecracker-shaped tier: a stripped VMM with a minimal device model
that boots in milliseconds. It refuses any configuration that widens the attack surface or
destroys the boot budget.

**Production status: NO_GO** (`python tools/production_gate.py`). The code paths are implemented
and verified locally; production certification is blocked on named owners/approvers, approved
Firecracker/kernel/rootfs pins, and real KVM-host evidence.

## Package map
| Module | Purpose | MC |
|---|---|---|
| `runtime.py` | pure MicroVM domain state machine (unchanged contract) | — |
| `errors.py` | stable error codes with `retryable` flag | 001, 013, 028 |
| `adapters/firecracker.py` | typed, whitelisted Firecracker API plan + fail-closed launcher | 001 |
| `supervision/vmm_process.py` | no-shell process supervision, bounded capture, deterministic cleanup | 001 |
| `virtualization/kvm.py` | real `/dev/kvm` ioctl preflight + host profile | 002 |
| `devices/specs.py` | typed specs for the five devices, host-wide ownership registry | 003 |
| `snapshot/store.py` | crash-consistent snapshot metadata + restore validation | 004 |
| `admission/controller.py` | PLN-04 admission: auth, controls, idempotency, quotas, fair bounded queue | 005, 029, 037 |
| `io/datapath.py` | optional INV-35 negotiation, region/descriptor bounds | 006 |
| `config/loader.py` | layered narrow-only config, transactional activate/rollback | 015 |
| `security/*` | artifacts pins, keys, tokens/capabilities, audit chain, secrets, jailer policy | 016, 018, 021–025 |
| `resilience/*` | retry/deadline/cancel, breaker, leases+journal, health, operator controls | 027–032 |
| `observability/*` | metrics, structured logs, tracing, decision records | 040–044 |
| `perf/bench.py` | benchmark harness, targets, regression gate | 034, 035, 039 |
| `schemas/` | 10 JSON Schemas + bounded validator | 013 |

## Running it
```
python -m unittest discover -s inv24_microvm_runtime/tests -t .      # from the repository root
python -O -m unittest discover -s inv24_microvm_runtime/tests -t .
python tools/run_evidence.py && python tools/production_gate.py
```
Real-host suites: `INV24_REAL_HOST=1 INV24_FIRECRACKER=… INV24_KERNEL=… INV24_ROOTFS=… INV24_MANIFEST=…`.
Framework conformance (`tests/test_component.py`) still needs the external `pk_core`.

Operations: `../docs/RUNBOOKS.md`, `../docs/ROLLOUT.md`, `../docs/INCIDENT_RESPONSE.md`.
