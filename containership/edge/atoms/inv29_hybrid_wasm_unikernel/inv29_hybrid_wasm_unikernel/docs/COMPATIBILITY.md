# Supported-version and compatibility matrix (INV29-MC029, MC030, MC031, MC095)

Legend: ✅ tested in this archive's CI evidence · ⚠️ supported by design, not yet tested · ❌ unsupported (refused) · ⛔ blocked — needs external lab

## Runtime
| Component | Versions | Status |
|---|---|---|
| CPython | 3.10, 3.11, 3.12, 3.13 (`requires-python >=3.10`) | ✅ 3.11 (this run) · ⚠️ others via CI matrix |
| pk_core | ≥ 4.0.0, < 5 (API `pk_core.contract/1`) | ⛔ not available here; incompatible versions refused at startup (tested with fakes) |
| INV-11 | typed-link API `check_link`/`classify` | ⛔ |
| INV-27 / INV-44 | attestation producers | ⛔ (test doubles only) |
| PLN-04 | must call `verify_record` | ⛔ (test double only) |
| INV-30 | optional | ⛔ (P2) |

## Architecture matrix (MC029)
| Host CPU \ Wasm target | wasm32 | wasm64 | other |
|---|---|---|---|
| x86_64 | model ✅ · real host ⛔ | model ✅ · real host ⛔ | ❌ refused ✅ |
| aarch64 | model ✅ · real host ⛔ | model ✅ · real host ⛔ | ❌ refused ✅ |
| anything else | ❌ refused ✅ | ❌ refused ✅ | ❌ |

"model ✅" = the decision logic is exercised (`test_model`, `test_properties`); "real host ⛔" = executing a real module inside a real unikernel on that ISA requires a hardware lab.

## Hypervisors (MC030) — ⛔ all
Firecracker, Cloud Hypervisor, QEMU/KVM, Hyper-V, Xen. INV-29 does not talk to the hypervisor (contract non-goal); evidence must come from INV-27 runs on each.

## Wasm runtimes (MC031) — ⛔ all
Wasmtime, WAMR, Wasmer, WasmEdge. Evidence must come from INV-44 hardening runs; INV-29 consumes only their `hardened` attestation.

## Mixed-version rules (MC095)
Upgrade consumers before producers (see `docs/SCHEMA_EVOLUTION.md`). An INV-29 4.3.x producer with a PLN-04 that does not verify signatures is an **unsupported combination**.
