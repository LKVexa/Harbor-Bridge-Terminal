# ADR-0003: Concurrency limits are process-local; single-owner topology is mandatory

**Status:** accepted (4.3.0). **Decision:** in-flight, re-entrancy and queue limits are enforced by one
`RLock` inside one process. A logical instance must have exactly one owner process. Distributed admission
(leases, fencing) is out of scope. **Enforcement:** `preflight` rejects any `INV16_TOPOLOGY` other than
`single-owner`. **Revisit when** a deployment needs a shared instance across workers or nodes.
