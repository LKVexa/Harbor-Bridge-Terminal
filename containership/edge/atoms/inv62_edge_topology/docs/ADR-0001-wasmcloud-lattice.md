# ADR-0001 — wasmCloud lattice as the INV-62 deployment substrate

* **Status:** PROPOSED — *not approved.* Approval requires the accountable architecture and operations
  owners named in `OWNERSHIP.md` (currently UNBOUND). Until approved, MC-002 stays `open_human`.
* **Date proposed:** 2026-09-23 · **Supersedes:** none · **Traceability:** C010, MC-002

## Problem

INV-62 must provide secure host discovery/routing across heterogeneous infrastructure (cloud, datacenter,
near-edge, far-edge) and keep each site working when its uplink is lost. It needs a substrate that runs the
same component on very different hosts, carries authenticated control traffic, and tolerates partitions.

## Decision (proposed)

Deploy INV-62 as a per-site component on a **wasmCloud lattice**; the lattice supplies placement of the
component on site hosts and the NATS-based transport between components. INV-62 itself does **not** depend on
lattice membership for correctness: authority for a site's graph and leases stays in that site's instance, and
all security decisions (PKT1 credentials, default-deny authorisation, audit) are made inside the component.

### Assumptions
Lattice transport provides mutual TLS between hosts; a site host can run at least one instance while
partitioned; the lattice does not re-order messages within a request/response pair.

### Non-goals
Using lattice link definitions as the topology source of truth; relying on lattice-level auth for
authorisation; cross-site singleton election.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Service-mesh-native discovery (Istio/Linkerd) | assumes Kubernetes and a connected control plane; far-edge devices and partitioned sites unsupported |
| Kubernetes-only topology (node labels + topology spread) | no per-link latency, no partition-local election, heavy for far-edge |
| Custom gossip control plane | large bespoke distributed-systems surface; security review cost |
| Another lattice/actor runtime | no advantage identified for this component; revisit at next review |

## Trust boundaries and failure domains

Client ↔ INV-62 (PKT1 + authz); INV-62 ↔ state disk (MAC chain); INV-62 ↔ secret provider; lattice host ↔
lattice host (mTLS, outside this component). Failure domains: process, host, site, region, cloud.
Consistency: single-writer per site instance; clients see linearisable revisions (CAS via
`expected_revision`).

## Consequences

Upgrade coupling to the lattice host version (see `WASMCLOUD_PIN.md`); portability risk if the lattice is
unavailable on a device class; observability must be exported by the component itself (done: metrics, logs,
traces); blast radius of a bad config is one site instance (overlays are per site).

## Rollback / reversal

Triggers: lattice cannot be pinned to a supported version with provenance; lattice transport cannot
provide mTLS on a required device class; two consecutive releases blocked by lattice defects. Migration:
the component is plain Python with a byte-in/byte-out `handle()` boundary and can be hosted by any RPC
server; state is portable via `export_state()` / `import_state()`.

## Approval record

| Role | Name | Decision | Date |
|---|---|---|---|
| Architecture owner | UNBOUND | pending | — |
| Operations owner | UNBOUND | pending | — |
| Security reviewer | UNBOUND | pending | — |

Change control: any change to the substrate, trust boundaries, or source of truth requires a superseding ADR.
