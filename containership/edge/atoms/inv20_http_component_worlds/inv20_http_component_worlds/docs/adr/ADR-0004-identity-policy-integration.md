# ADR-0004 — Identity and policy integration
- **Status:** Proposed · **Work item:** WI-INV20-06

Principals are typed (`tenant`, `workload`, `component_instance`, `node`, `operator`, `external_peer`).
Production identity is expected to be an mTLS/SPIFFE-equivalent SVID verified at the adjacent layer and
bound to the attested artifact digest; `IdentityVerifier` is the reference implementation (HMAC-attested
documents) used by tests. The PDP is wrapped by `Authorizer`: unavailable ⇒ deny new privileged actions,
except a cached **allow** younger than `cache_seconds` (default 0 = no cache). Cached denies never flip.
Clock skew tolerance: 30 s. Trust-root ownership and rotation cadence: UNASSIGNED (blocker).
