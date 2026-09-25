# PLN-05 semantics specification (PLN05_SEMANTICS 1.0.0)

Normative language: **SHALL / SHALL NOT** per RFC 2119. Scope per ADR-0001 (PROPOSED). Compatibility: a change to any SHALL statement below is a semantic change and bumps the minor version of this document; a change that alters an emitted outcome for an identical input bumps the major version and the package minor version.

## 1. Deployment contexts

| Context | Clock | Network to demand source / coordination | Storage | Profile |
|---|---|---|---|---|
| public cloud | NTP-disciplined, skew ≤ 1 s | reliable, < 10 ms | durable volume | default config |
| private cloud / datacenter | NTP, skew ≤ 1 s | reliable | durable | default |
| near-edge | NTP, skew ≤ 2 s | intermittent, partitions of minutes | durable local disk | `stale_after_s` 60, `degraded_after_s` 600 (site overlay) |
| far-edge / occasionally connected | local RTC, skew ≤ 5 s | partitions of hours | local flash, power loss possible | `stale_after_s` 120, `degraded_after_s` 1800, `lease.duration_s` 60 |

Unsupported: running without a coordination service when more than one plane instance can serve a scope (split-brain risk); running with wall-clock skew larger than `future_skew_s`.

## 2. Outcome classes (every observation cycle yields exactly one)

`scale-up`, `scale-down`, `hold`, `constrained-hold` (floor or ceiling reached), `stale-input-hold`, `frozen`, `degraded`, `recovery` — the `outcome` enum of `PK_CAPACITY_TARGET/1`. Failures are **errors**, not outcomes: retryable (`E_NOT_LEADER`, `E_OVERLOADED`, `E_CIRCUIT_OPEN`, `E_STATE_UNAVAILABLE`, `E_SECURITY_DEPENDENCY`, `E_AUDIT_UNAVAILABLE`, `E_DEADLINE`) or terminal (all others). Partial success does not exist for a decision: a decision is either persisted-and-(attempted-)published or not taken at all (MC-18 persist-before-publish; memory is rolled back on persistence failure).

## 3. Lifecycle

See `spec/pln05_state_machine.mmd`. Plane states: initializing → ready → active ↔ degraded ↔ unready, stalled, draining → stopped, failed. Scope modes: active, stale, degraded, frozen, quarantined, disabled. Readiness is false in unready/stalled/failed/draining and the plane SHALL refuse to decide under the same predicates.

## 4. Time

- Freshness and staleness use the plane's wall clock (the trusted time source) compared with `observed_at`; a sample older than `stale_after_s` SHALL be rejected (`E_STALE_INPUT`), one more than `future_skew_s` in the future SHALL be rejected (`E_FUTURE_SKEW`).
- Stall detection SHALL use monotonic time.
- A wall-clock step backwards of more than 1 s SHALL set `time_fault`; while set the plane SHALL NOT decide (`E_SECURITY_DEPENDENCY`) and SHALL report `R_TIME_FAULT`. It clears when the clock passes the last observed value.
- Grace windows are counted in **samples**, not seconds; clock behaviour cannot shorten a grace window.

## 5. Stale / absent demand and partitions

| Partition between PLN-05 and… | Behaviour |
|---|---|
| demand source | after `stale_after_s`: publish one `stale-input-hold` (same target); after `degraded_after_s`: publish one `degraded` hold; never scale on missing data; exit on the first fresh, authenticated, in-order sample (`recovery`). |
| coordination service | keep deciding only while the granted lease is valid; after expiry `E_NOT_LEADER`, publish nothing. Downstream keeps its last applied target. |
| target consumer (SCH-01/provider) | decisions are persisted; publication fails into the sink breaker; `republish_last` re-emits with the same `decision_id` after recovery. |
| policy service | none: capability policy is versioned inside the package. |
| observability backend | none: telemetry never blocks decisions. |

## 6. Precedence (highest first)

1. hard safety: never outside `[floor, ceiling]` of the active envelope; never publish without a lease;
2. emergency controls: disable > quarantine > freeze (any active control wins over demand, limits and config);
3. security posture: degraded security (audit pressure ≥ 75 %, no active key) forbids scale-up; audit full / time fault forbids deciding;
4. external lowered ceiling (GAP-10 power/thermal) — monotonic, cannot cross the floor;
5. declared envelope (PLN-01 intent plane: floor, ceiling, thresholds, grace);
6. site / tenant / environment configuration overlays (in `config/schema.json` precedence);
7. demand signal (input, never authority); low-confidence samples hold.

Residency and cost are not decided here: residency is enforced by placement (SCH-01) and cost by the intent plane's ceiling; PLN-05 can only be *more* conservative than either. Contradictory rapid policy changes resolve by revision number: a limits revision ≤ the active one is rejected (`E_OUT_OF_ORDER`).

## 7. Envelope changes during a grace window

A limits change or `lower_ceiling` SHALL reset pending scale-down evidence and SHALL clamp the current target into the new envelope. A configuration change SHALL NOT reset hysteresis state.

## 8. Idempotency and ordering

`message_id` is the idempotency key (last 256 per scope retained and persisted); a repeat is `E_DUPLICATE` with no effect. `seq` is per source and SHALL strictly increase; otherwise `E_OUT_OF_ORDER`. Decisions carry a `decision_id`; consumers de-duplicate on it and reject fencing tokens lower than the highest seen.

## 9. Numeric domains

Capacity units are integer replicas in `[0, 1 000 000]`; utilisation is a dimensionless ratio in `[0, 1000]` (values > 1 mean oversubscription); thresholds satisfy `0 < scale_down_at < scale_up_at < 1`; grace `1..1000` samples. NaN/Infinity are rejected at the tokenizer; integers are never rounded; scale-up doubles (minimum +1) and saturates at the ceiling; scale-down halves (floor division) and saturates at the floor. Rate of change: at most ×2 per sample upward, at most ÷2 per `grace_samples` samples downward.

## 10. Tenancy and state scope

State is **per workload scope** `tenant/site/workload`; one controller instance per scope; one plane process may serve many tenants, with every lookup keyed by the scope derived from the authenticated message and authorised against the credential's tenant/site scope before lookup.

Only the scope's leaseholder may change it; a new lease term reloads the scope from shared state before acting (see `ops/reliability/degraded_modes.md`). Envelope changes that move the current target publish a `constrained-hold` (`R_ENVELOPE_CHANGED`) immediately, even while frozen, because the envelope outranks controls (§6); only `disabled` suppresses it.

## 11. Data classification

| Field | Class |
|---|---|
| tenant, site, workload ids | internal — never used as metric labels |
| utilisation, targets | internal operational |
| credentials, keys | secret — never logged, never persisted by PLN-05 |
| audit records | restricted — integrity-protected |

## 12. NFR → verification map

See `spec/pln05_nfr.json`; every NFR names its test or benchmark and threshold.
