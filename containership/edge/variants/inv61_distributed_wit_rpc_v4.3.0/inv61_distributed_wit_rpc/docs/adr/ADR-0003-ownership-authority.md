# ADR-0003 — Ownership, failover and split-brain control

* **Status:** Proposed (W-001) · **Date:** 2026-09-22

Mutating exports run only on the holder of a time-bounded lease; each grant increments a fencing epoch; resources reject epochs lower than the highest seen. `state.LeaseAuthority` is the reference contract. **Production MUST back it with a linearizable store** (etcd/Consul/ZooKeeper lease with revision as epoch); that integration is not in this archive (W-007). Partition behaviour: a node that cannot renew stops mutating (its calls return `fenced`), read-only exports continue (degraded operation, C056). Failover never crosses a site or residency boundary: leases are scoped per site resource name.
