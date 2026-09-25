# INV-14 contract compatibility policy (v4.3.0)

Applies to `PK_POLL/1`, `PK_POLLABLE/1`, `PK_POLL_ERROR/1`, `PK_POLL_METRICS/1`, `PK_POLL_LOG/1`,
`PK_POLL_AUDIT/1`, `PK_POLL_CONFIG/1`, `PK_CLOCK_CONFIG/1` and `pk:inv14@4.3.0` WIT.

- **Widths/bounds.** Indexes and sizes are u32 (JSON: integer 0..2^32-1); counters u64. Set size ≤ 65,536 by
  schema, ≤ `max_pollables` (default 4,096) at runtime. Strings ≤ 256; error message ≤ 1,024; log line ≤ 4 KiB.
- **Timeout ticks.** Integer ≥ 1. 0, negatives, booleans, floats and strings are `PK_POLL_INVALID_TIMEOUT`.
  Above `max_timeout_ticks` → `PK_POLL_TIMEOUT_LIMIT`; `ticks × tick` > 60 s → `PK_POLL_DURATION_LIMIT`.
  No rounding: tick→ns is exact integer multiplication. Timeout is measured from after validation, at waiter
  registration (one monotonic deadline).
- **ready_indexes.** Ascending positions into the request sequence; unique; `ready[i]` is the name at
  `ready_indexes[i]`. Names are unique per request (duplicates refused). Pollables are not removed mid-poll
  (the request is a tuple snapshot).
- **Metrics.** Counters are monotonic per process and reset on restart (process-local; `process_epoch`
  identifies the series generation). `max_*` fields are configuration gauges.
- **Additive policy.** New optional fields may be added within a major version; consumers MUST ignore unknown
  fields they do not need **only on output payloads**; inputs (config) reject unknown fields. New error codes are
  additive; consumers MUST treat an unknown code by its `retry_class` family default (`permanent`).
- **Breaking changes** (removing/renaming a field, changing units or tick semantics) require a new major
  schema id (`/2`), a migration note, regenerated fixtures (`tools/gen_fixtures.py`), an updated WIT package
  version and an approved review record. `tools/gen_contracts.py --check` and the golden fixtures make any
  drift fail CI.
