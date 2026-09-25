# Day 2 — operation (M82)

## Host loss {#host-loss}
Detector: suspect after 3 s, lost after 8 s (production defaults). On loss the controller must hold the quorum lease; components move to eligible hosts in precedence order (security → isolation → residency → capacity → anti-affinity; then latency, cost, id). A component with no eligible host goes to `failed` with `NO_ELIGIBLE_TARGET` — it is **not** moved outside its residency. Check `decisions.query(kind="failover")`.
If failover returns `PARTITIONED`, the controller is in a minority: do not force; restore connectivity to a voter majority.

## Latency {#latency}
`Inv60RoutingP99Burn`: check `inv60_call_seconds` by host, circuit breakers (`CIRCUIT_OPEN` codes), rate limiting (`RATE_LIMITED`/`OVERLOADED`). Shed load via `limits.*` overlay change (two-phase activation).

## Routine
- Re-run the gate on every contract/implementation change; the ledger must chain onto the previous anchored head.
- Rotate credentials: tokens are ≤ 15 min; revoke a principal with `TrustDomain.revoke`; re-enrol with a new one-time code.
- Trust root refresh: `TrustPolicy.trust_root_issued_at` older than 30 days makes admission fail closed — refresh before expiry (disconnected sites carry the root in their overlay bundle).
