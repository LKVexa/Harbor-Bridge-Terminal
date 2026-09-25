# Capacity, quota, fairness and saturation (MC-018, MC-065, MC-066, MC-067)

| Resource | Bound | Where |
|---|---|---|
| admissions per tenant | token bucket (rate, burst), default 50/s burst 20 | `resilience.Admission` |
| admissions in flight (global) | 32 | same |
| running instances per tenant | `quotas.max_instances_per_tenant` (default 16) | `service.UnikernelService.run` (atomic under lock) |
| image size / parser work | 64 MiB / 20M work units | `image.elf.Limits` |
| serial output before ready | 256 KiB | `vmm.Supervisor` |
| token TTL / nonce store | 15 min / 100,000 | `authz.Authenticator` |
| audit buffer | 100,000 events then refuse | `audit.AuditLog` |

## Capacity model

These figures come from `evidence/PERF_RESULTS.json` on a 2-vCPU Linux container with CPython 3.11
and pure-Python Ed25519. Admission of a typical 9 KB image costs about 6 ms of CPU per request,
most of it the signature check. With the 32-slot in-flight cap and CPU-bound Python, one controller
process saturates at about `1000 / p50_ms` ≈ 170 admissions/s per core.

Saturation signals are `uk_inflight / 32`, `rate(uk_shed_total)` and the p99 of
`uk_run_latency_ms`. Swapping in the `cryptography` backend (`signing.set_backend`) removes most of
the signature cost.

## Edge power and thermal (MC-066)

Not measured. This needs instrumented edge hardware (W-HW).
