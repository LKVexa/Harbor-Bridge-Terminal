# External interfaces (MC-023, MC-026)

| Operation | Input | Output | Capability | Idempotency | Deadline | Errors |
|---|---|---|---|---|---|---|
| `admit` / `run` (PK_UNIKERNEL_IMAGE/1 → PK_UNIKERNEL_INSTANCE/1) | token, tenant, image bytes, bound digest, `PK_UNIKERNEL_SEAL_MANIFEST/1`, DSSE envelope with `PK_UNIKERNEL_PROVENANCE/1`, idempotency key (8–128), optional fence, `deadline_ms` (1–60000), W3C `traceparent` | `Instance` (schema `PK_UNIKERNEL_INSTANCE/1`), seal `PK_UNIKERNEL_IMAGE/1` | `image.admit` + `instance.run` in tenant scope | same (tenant, key) returns the same instance; the same key with a different image gets `UK_INSTANCE_DUPLICATE` | `UK_DEADLINE_EXCEEDED` | any `UK_*` in `ops/ERROR_CODES.json` |
| `stop` | token, instance id, optional fence | Instance (state `stopped`) | `instance.stop` in tenant scope | yes | grace 2 s then SIGKILL | `UK_UNKNOWN_INSTANCE`, `UK_FORBIDDEN`, `UK_STALE_FENCE` |
| `quarantine` | token, image digest and/or tenant | stopped instance ids | `instance.quarantine` | yes | — | `UK_FORBIDDEN` |
| `disable` / `enable` | token, reason | — | `component.disable` | yes | — | — |
| `health` | — | `PK_UNIKERNEL_STATUS/1` | none (local) | yes | — | — |
| `explain` | decision or instance id | text | `audit.read` (host-enforced) | yes | — | `UK_UNKNOWN_INSTANCE` |

JSON Schemas are in `schemas/`. Backpressure means `UK_OVERLOADED`, which is retryable with backoff
(`resilience.retry`, full jitter, at most 5 attempts, deadline-aware). Cancellation uses
`resilience.CancelToken`.
