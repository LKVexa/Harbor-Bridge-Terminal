# Placement precedence (M14) — generated from fabric/placement.py

Policy `inv60-precedence/1.0.0`. Hard (absolute, in order): security, isolation, residency, capacity, anti_affinity. Soft (optimised lexicographically): slo, cost, then load, then host id.

Only `capacity` may be relaxed, and only with a break-glass decision id; the relaxation is recorded.

## Worked example
Hosts: `a` (eu, latency 1, cost 2), `b` (eu, latency 1, cost 2), `c` (us, latency 0, cost 9). Request: component `x`, regions `[eu]`.

1. security/isolation pass for all. 2. residency removes `c`. 3. capacity/anti-affinity pass. 4. soft: `a` and `b` tie on latency and cost and load. 5. tie-break by id → **a**. The decision record lists all 15 rule evaluations.
