# GAP-01 Normative Requirements (v5.0.0)

Keywords SHALL / SHOULD / MAY per RFC 2119. Each requirement ID is referenced from `TRACEABILITY.json` and from tests.

## Lifecycle (R-LC)

- **R-LC-1** The supervisor SHALL expose exactly the states `joining, ready, cordoned, draining, stopped` and the legal transitions in `supervisor.TRANSITIONS`; `stopped` is terminal.
- **R-LC-2** A transition to `stopped` SHALL be refused while any workload is resident (`E_DRAIN_INCOMPLETE`).
- **R-LC-3** A transition to `ready` or an `uncordon` SHALL require an aggregate-healthy evaluation at the moment of the request.
- **R-LC-4** After any restart, a persisted `ready` SHALL be restored as `cordoned` with a new cordon generation.
- **R-LC-5** Leaving `draining` for `cordoned` SHALL cancel the drain intent.

## Admission (R-AD)

- **R-AD-1** Admission SHALL be refused unless the node is `ready`, healthy, not partitioned, not in emergency, not disabled, and not under resource pressure.
- **R-AD-2** Workload identities SHALL be unique; duplicates are rejected (`E_DUPLICATE_WORKLOAD`).
- **R-AD-3** Resident workloads SHALL NOT exceed `max_workloads` (`E_CAPACITY`).
- **R-AD-4** A runtime launch failure SHALL roll back the admission.

## Drain (R-DR)

- **R-DR-1** Drain SHALL release workloads in trust order `hostile → untrusted → third-party → first-party → trusted`, then by name.
- **R-DR-2** A workload SHALL leave the resident set only with a proven reclaim (terminated and resources released).
- **R-DR-3** Before the deadline the supervisor SHALL signal graceful stop without blocking; at `deadline + drain_kill_after_s` it SHALL force-kill.
- **R-DR-4** A deadline breach SHALL be recorded once per distinct observation and SHALL hold the node in `draining`.
- **R-DR-5** Operators with `drain.override` MAY extend the deadline or force immediate termination; overrides are audited.
- **R-DR-6** Drain intent SHALL survive restart.

## Health (R-HE)

- **R-HE-1** Only registered signals are accepted; reporters MAY be restricted per signal.
- **R-HE-2** Aggregate health SHALL be false if any required signal is missing, stale, failing, or if the optional quorum is not met, or if no required signal is registered.
- **R-HE-3** Observation timestamps SHALL NOT regress per signal; future-dated evidence is stale.

## Security (R-SE)

- **R-SE-1** Every mutating or reading request SHALL be authenticated (per-caller HMAC-SHA256), fresh (±`request_skew_s`), and non-replayed (nonce window).
- **R-SE-2** Authorization SHALL be deny-by-default via role → capability bindings; overrides SHALL carry a reason and expire within 1 h.
- **R-SE-3** Security-sensitive operations and denials SHALL be written to a hash-chained audit log.
- **R-SE-4** Secrets SHALL be loaded only from 0600 files or environment variables and SHALL NOT appear in logs, diagnostics, or reprs.
- **R-SE-5** Signed configuration SHALL be rejected on signature mismatch; unknown knobs SHALL be rejected.

## Resilience (R-RS)

- **R-RS-1** Every durable change SHALL be journaled before being applied and checkpointed after.
- **R-RS-2** If a checkpoint fails after apply, the supervisor SHALL enter emergency mode.
- **R-RS-3** On start, the supervisor SHALL terminate running workloads it has no intent for (orphans) and drop intent for workloads no longer running (lost).
- **R-RS-4** Partition state SHALL progress `connected → suspect (> lease/2) → partitioned (> lease) → autonomy-expired (> lease + max_autonomy)`; autonomy expiry SHALL enter emergency.
- **R-RS-5** A stalled control loop (no tick for `watchdog_timeout_s`) SHALL fail liveness and enter emergency.
- **R-RS-6** `request_id` completion records SHALL make retries idempotent across restarts within `replay_window`.

## Failure semantics

| Class | Meaning | Examples | Caller action |
|---|---|---|---|
| success | applied and durable | `ok: true` | none |
| partial | drain in progress | `PK_DRAIN/1` with `remaining` | poll / wait for tick |
| degraded | op refused by mode | `E_PARTITIONED`, `E_EMERGENCY`, `E_CAPACITY` | retry after condition clears |
| retryable | transient | `E_RATE_LIMITED`, `E_PERSISTENCE`, `E_RUNTIME` | retry with same `request_id`, backoff+jitter |
| terminal | will never succeed as sent | `E_BAD_REQUEST`, `E_FORBIDDEN`, `E_ILLEGAL_TRANSITION` | fix request |

## Precedence when requirements conflict

1. Safety/security (fail closed, audit) → 2. Drain completeness (never stop with residents) → 3. Isolation proof → 4. SLO/latency → 5. Availability of admission. Example: under persistence failure the node stops admitting (1 beats 5).

## Environments

Cloud, datacenter, near-edge and far-edge use the same binary. Differences are configuration only (lease, autonomy window, ceilings); see `CAPACITY.md` for the recommended profiles.

## Non-goals

Deciding where drained workloads go; provisioning hardware; acting as a control-plane member; declaring a node healthy on missing evidence; multi-tenant fairness *between tenants* (see `CAPACITY.md` §Fairness).
