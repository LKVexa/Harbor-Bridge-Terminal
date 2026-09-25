# INV-24 normative requirements (MC-009)

Keywords per RFC 2119. IDs are stable and referenced from `traceability/TRACEABILITY.json`.
Precedence on conflict: **security > tenant isolation > safety/cleanup > availability > performance**.

## All environments
- **REQ-001** The runtime SHALL boot only devices in the minimal model and SHALL reject any other device before any VMM side effect. (`DEVICE_OUTSIDE_MODEL`, terminal)
- **REQ-002** The runtime SHALL NOT launch a VMM unless Firecracker, kernel and rootfs digests match approved pins. (`ARTIFACT_*`, terminal)
- **REQ-003** The runtime SHALL NOT launch without a passing KVM ioctl preflight. (`HOST_KVM_*`; `HOST_KVM_TRANSIENT` retryable, others terminal)
- **REQ-004** Admission SHALL authenticate, authorize (`microvm:create` for the tenant), check operator controls, idempotency, quotas and host readiness before any side effect.
- **REQ-005** Retries with the same operation key SHALL NOT create a second microVM, including across controller restart.
- **REQ-006** Stop SHALL destroy instance state and release every tenant-owned resource (TAP, MAC, CID, writable drive).
- **REQ-007** Every security-relevant decision SHALL be recorded in the hash-chained audit log.
- **REQ-008** Logs, metrics, traces, diagnostics and evidence SHALL NOT contain secret values.
- **REQ-009** Cold boot SHALL be reported against the budget; a breach SHALL fail the instance (`BOOT_BUDGET_EXCEEDED`, terminal for that instance).
- **REQ-010** Overload SHALL be rejected with `OVERLOADED` (retryable) once bounded queues are full.

## Per environment
| ID | cloud | datacenter | near-edge | far-edge |
|---|---|---|---|---|
| REQ-020 boot budget (ms, SHALL ≤) | 125 | 125 | 125 | 125 (site MAY lower) |
| REQ-021 max instances/node (SHALL ≤) | config | 512 | 128 | 16 |
| REQ-022 permitted devices | all 5 | all 5 | all 5 | no `virtio-net` by default |
| REQ-023 control plane unreachable | SHALL refuse new admissions (`DEGRADED_REFUSED`) | same | same | same |
| REQ-024 running guests when degraded | SHALL stop unless `degraded_policy=serve_existing` | same | MAY serve existing | SHOULD serve existing |
| REQ-025 network-offline operation | n/a | n/a | SHALL keep audit locally and reconcile | same |

## Terminal vs retryable outcomes
Authoritative table: `inv24_microvm_runtime/errors.py::ERROR_CODES` (`retryable` flag), schema `PK_MICROVM_ERROR/1`.
