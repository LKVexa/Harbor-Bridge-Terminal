# Boundaries with adjacent layers

| Concern | Owner | INV-27's side |
|---|---|---|
| Building images and toolchains | INV-28 | toolchain profiles + provenance policy |
| Hypervisor / VMM | INV-23 | adapter, version probe, hardened argv, supervisor |
| Placement / residency / failover | PLN-04, placement | precedence rule; refuses unsupported architectures |
| Transport security for the control API | host API layer | none: INV-27 exposes a Python API, not a network listener |
| Secret store / KMS | host | `secret_ref` only; KeyRing takes keys it is given |
| Wasm payloads | INV-29 | shares the sealed-image model (not implemented here) |
