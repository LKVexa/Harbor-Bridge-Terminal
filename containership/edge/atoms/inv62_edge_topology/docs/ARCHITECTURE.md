# INV-62 Edge Topology — Architecture (v4.3.0)

Traceability: C001–C008, MC-002 (inputs to the ADR), MC-022, MC-031.

## Responsibility and scope

INV-62 owns the **topology graph** of the estate (cloud → region → site → device), live-link latency and
health, **policy-aware nearest-capable resolution**, **designated-cloud partition detection**, and **fenced
site-local coordinator leases**. It does not own workload scheduling (GAP-03), WAN transport (GAP-12),
device provisioning, data placement, or hardware discovery (GAP-02).

| Mandatory capability | Implementation |
|---|---|
| Model every node in a tier with its parent | `topology.py::Topology.add` |
| Resolve the lowest-latency capable node under policy | `production/policy.py::resolve` |
| Detect when a site loses its uplink | `production/service.py::_partitioned_sites`, `Topology.partitioned` |
| Elect a local coordinator in a partitioned site | `production/election.py::LeaseAuthority` |
| Never route across a down link | `Topology._neighbours` (down links are never yielded) |

Optional optimisations: per-revision reachability cache, lazy early-terminating Dijkstra, batching (atomic
multi-mutation apply), per-tenant tuning via overlays. Unsupported patterns and non-goals: a global
singleton lease authority spanning sites; routing decisions by clients that bypass `PK_TOPO_NEAREST`;
cross-tenant graphs; disabling authentication (the config schema makes `require_auth` a constant).

## Layering

```
 GAP-02 discovery ─┐                         ┌─ GAP-03 scheduler (resolve)
 GAP-12 WAN probes ─┼─ PK_TOPO_GRAPH/1 ──┐   │  GAP-04 disconnected ctl (status/acquire/renew)
                    │                     ▼   ▼
               wire.py  decode → negotiate → schema  (size/depth/dup-key/NaN guards)
               service.py  readiness → authn (PKT1) → authz (default deny, tenant, node binding)
                           → admission (per-tenant bucket, in-flight bound) → nonce spend
                           → idempotency → mode gate → deadline → dispatch
               policy.py / election.py / health.py / lifecycle.py
               topology.py   validated graph engine (stdlib, no pk_core)
               persistence.py (WAL + snapshot, MAC'd, optional AES-GCM)   audit.py (hash chain)
               config.py (schema, overlays, secrets, generations)          telemetry.py
```

## Source of truth

The **per-tenant topology graph held by the site's INV-62 instance**, as mutated only through
authenticated `PK_TOPO_GRAPH/1 apply` calls and persisted in its WAL, is authoritative. A node's own idea of
its location is advisory. Link latency is authoritative only while fresh (`health.stale_after_s`).
Election terms are authoritative from the persisted high-water mark; leases are never restored after restart.

## Boundaries

* **Tenant** — each tenant has an independent graph, quarantine set, health trackers and lease keys
  (`tenant/site`). Credentials name explicit tenants; there is no wildcard.
* **Environment** — `dev|test|staging|prod`; prod adds validation rules (no debug logs, audit fsync,
  residency required).
* **Site** — one instance per site is the supported deployment; the lease authority for a site lives in
  that site's instance so it keeps working when the uplink is lost.
* **Workload** — callers are identified by role credentials; per-tenant admission buckets provide fairness.

## Dependencies

| Dependency | Direction | Contract | Failure behaviour |
|---|---|---|---|
| GAP-02 Hardware capability discovery | upstream | `PK_TOPO_GRAPH/1 apply add_node` (see `adapters.HardwareDiscoveryFeed`) | stale capabilities remain until removed |
| GAP-12 WAN resilience / NAT traversal | upstream | `apply probe` / `connect` with `measured_at` | missing probes → SUSPECT → STALE → excluded |
| GAP-03 Topology-aware scheduler | downstream | `PK_TOPO_NEAREST/1 resolve` | receives `NO_CAPABLE_NODE` or `degraded` outcomes |
| GAP-04 Disconnected operation controller | peer | `PK_TOPO_PARTITION/1 status/acquire/renew/validate_token` | fenced by term |
| Secret provider | infra | `SecretProvider.resolve` | activation fails closed |
| Trusted time / key service / policy | infra | `Clock`, `KeyRing`, `Authorizer` availability | `TOPO.DEPENDENCY_UNAVAILABLE`, not ready |
| wasmCloud lattice (transport, host) | platform | see `WASMCLOUD_PIN.md` | NOT verified in this archive |

## Assumptions

Every peer, path and store can fail independently; callers are untrusted until authenticated; clocks may
step (token buckets and deadlines tolerate backward steps; credential validity allows ±30 s skew);
storage may tear the last write; the transport may be observed by an attacker (message-level MACs on
credentials; confidentiality from lattice mTLS — not verifiable here).

## Artifact / configuration / state separation (MC-022)

| Class | Location | Mutability | Integrity |
|---|---|---|---|
| Immutable artifact | this package, `schemas/`, `fixtures/` | never modified at runtime | `RELEASE_MANIFEST.json` digests + signature |
| Configuration | operator-supplied JSON + overlays → numbered generations in `<state_dir>/config/` | new generation per change | digest, provenance, optional HMAC signature |
| State | `<state_dir>/state/{wal.jsonl,snapshot.json}`, `<state_dir>/audit.jsonl` | append/atomic replace | HMAC chain, optional AES-GCM |

`state_dir` must not be inside the artifact directory.
