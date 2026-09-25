# Interfaces: PK_FASTBOX_RUN / RESULT / HOSTCALL (C023, C025, C027, C093)

## Request (PK_FASTBOX_RUN/2)
`{"token", "versions":[1|2], "result_versions"?, "program" | "module"+"manifest", "caps"?, "fuel"?, "idempotency_key"?}` plus an optional `traceparent` header.

## Authentication
- Tokens are `base64url(claims).base64url(HMAC-SHA256)`. Claims: `sub, ten, cap[], aud="inv70", iat, exp, jti, kid`.
- Maximum lifetime 900 s, clock skew ±30 s, `jti` replay cache, key purpose must be `caller`, immediate revocation.
- Failures are rejected before any validation or execution: `FB-S010..S016`.

## Timeouts, cancellation, retry, idempotency, backpressure
- Wall clock per run: `wall_clock_ms`. The child process is killed at the deadline → `FB-T001`.
- Host call timeout: `host_call_timeout_ms` (≤ wall clock) → `FB-H003`. At most 1,000 host calls per run.
- Cancellation: a `CancelToken` is checked before RUNNING and while waiting → `FB-T002`.
- Idempotency: the key is scoped per tenant. Same request → cached result with `replayed:true`. Different request → `FB-D001`. Concurrent duplicate → `FB-D002`. Infrastructure failures are not cached.
- Backpressure: requests are shed immediately with `FB-C001` (concurrency, tenant quota, rate). There is no unbounded queue.
- Retries are the caller's job, using `resilience.RetryPolicy`: only idempotent requests, only `overloaded`, `circuit open`, `backend unavailable` or `worker crashed`, capped full-jitter backoff, a retry budget, and the caller's deadline is respected.

## Result (PK_FASTBOX_RESULT/2)
`{"run_id","status":"ok|trap|error","value","reason","reason_code","class","fuel","state"}`. RESULT/1 is `{"ok"|"trap","fuel"}`. `fuel:-1` means the worker was killed, so the count is unknown.

## Versions
- Negotiation picks the highest common version. With no overlap → `FB-V001`.
- Supported peer releases: N-1 minor (`4.2`, `4.3`). RUN/1 and RESULT/1 are deprecated as of 2027-06-30.
