# ADR-001 — GAP-11 control-plane technology choices (GAP11-P2-45)

**Status:** PROPOSED (not approved). **Decision owner:** UNASSIGNED. **Date proposed:** 2026-09-22.
**Supersedes:** none. **Superseded by:** none.

## Decisions proposed

| ID | Decision | Alternatives considered | Trade-off |
|---|---|---|---|
| DEC-01 | State store: single-writer append-only WAL + snapshot with multi-key CAS (`store.py`) as the reference backend behind a narrow `commit/get/scan` interface | etcd, FoundationDB, PostgreSQL SERIALIZABLE | Zero dependencies and provable crash points today; no replication. A production deployment should swap in a replicated linearizable KV implementing the same interface (BLK-ENV). |
| DEC-02 | Fencing at the store, token = leader epoch | Fencing at each device agent | Store fencing makes deposed-leader writes impossible without trusting agents; device-side side-effects must re-check the token (recorded as a requirement on P0-08 backends). |
| DEC-03 | Lease-based leader election on the same store with a safety margin | Raft inside GAP-11 | Reuses the store's linearizability; correctness never depends on the local clock because the fence rejects stale writers. |
| DEC-04 | Reuse the audited v4.2.0 `AcceleratorPool` as the placement kernel over a transient view rebuilt from durable truth | Re-implement placement against the store | Keeps one audited selection rule set; costs O(devices) per decision (measured: see evidence/benchmark.json). |
| DEC-05 | JSON wire format with closed request schemas / open response schemas | Protobuf, WIT | Stdlib only; closed requests turn typos into errors. |
| DEC-06 | HMAC workload-identity credentials as the in-process verifier; mTLS/SPIFFE at a terminating proxy in production | Direct mTLS in the service | No PKI exists here (BLK-PKI). |
| DEC-07 | Scrub failure, timeout, partial verify, or unknown outcome ⇒ QUARANTINED; no configuration can skip scrub | Configurable skip for trusted tenants | Availability cost accepted for isolation. |

## Consequences

Every DEC-xx is referenced from `tools/registry.py` design records and from `docs/EXCEPTIONS.json` where it creates a residual gap. Approval of this ADR is a precondition of GAP11-EXIT-01 and is **not** given by this build.
