# Interface and resource ceilings (work item 13 — C017, C028, C067, C069)

| Limit | Value | Enforced in | Error |
|---|---|---|---|
| Devices per catalogue | 64 | `model.MAX_DEVICES` (register, parse) | INV25_LIMIT_EXCEEDED |
| Registers per device | 256 | `model.MAX_REGISTERS_PER_DEVICE` (checked before iteration) | INV25_LIMIT_EXCEEDED |
| Aggregate registers | 4096 | `model.MAX_AGGREGATE_REGISTERS` (register, replace) | INV25_LIMIT_EXCEEDED |
| Name / class / version | 64 chars | `_clean_text` + regex | INV25_INVALID_* / LIMIT |
| Environment | 64 chars, device-name grammar | `DeviceCatalogue.__post_init__` | INV25_INVALID_FIELD |
| Register id | 128 chars | regex | INV25_INVALID_REGISTER |
| Rationale / reviewer | 1024 / 256 chars | `_clean_text` | INV25_LIMIT_EXCEEDED |
| Raw string pre-scan | 4 × field limit | `_clean_text` (bounds work on hostile input) | INV25_LIMIT_EXCEEDED |
| Serialized catalogue / diff / payload | 1 MiB | `export()`, `catalogue_from_export()` (before parse) | INV25_LIMIT_EXCEEDED |
| Pending candidates (queue) | 32 | `CatalogueStore.MAX_PENDING` | INV25_LIMIT_EXCEEDED |
| Token size | 4 KiB | `Verifier.max_token_bytes` | INV25_UNAUTHENTICATED |
| Mutation rate | 5/s, burst 20, per subject | `store._Bucket` | INV25_RATE_LIMITED |
| Concurrent writers | 1 (serialized by lock) | `CatalogueStore._lock` | — |

Constants are compile-time; changing them is a reviewed code change (`CODEOWNERS`). Python ints do
not overflow. Fairness: rate limiting is per authenticated subject, so one tenant/automation cannot
starve another. Burst behaviour: excess mutations are rejected (load shedding), reads are never throttled.

## Capacity model / saturation signals (C069)
Worst case is 64 devices × 64 registers ≈ 31 KB export, ~0.4 MB peak allocation (measured).
Saturation signals: `RATE_LIMITED` count, `pending_candidates` near 32, `last_activation_seconds`
above the p99 budget, `surface_registers` approaching 4096.
