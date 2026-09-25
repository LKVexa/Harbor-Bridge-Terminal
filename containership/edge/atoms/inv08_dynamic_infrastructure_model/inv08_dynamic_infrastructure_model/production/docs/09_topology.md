# INV-08 deployment topology (PROPOSED)

Source of truth: `production/topology.json`, validated by `production/topology.py` (rules T1-T7).

```
            PLN-05 elasticity plane (demand, bounds)
                       | PK_DYN_SCALE/1 (control)
 +-------------- site-a (cloud, fd-a1..a3) ---------------+
 | pool_controller[tenant-x]@fd-a1 --PK_DYN_LEASE/1--> lease_store[tenant-x]@fd-a2 |
 |        |  provider adapter (absent)        audit_sink (per-tenant stream)       |
 +--------|-----------------------------------------------+
          | upstream lease store
 +-- site-e (far_edge, fd-e1) --+
 | pool_controller[tenant-x]    |
 +------------------------------+
 INV-68 packer <-- PK_DYN_COST/1 + membership (data plane)
```

Placement rules: cloud/datacenter may host controller, lease store, audit sink
(lease store needs >= 3 failure domains); near-edge controller + store;
far-edge controller only, with an upstream lease store for the same tenant.
One controller per tenant per site (no global singleton; no intra-site split
brain).  Tenants never share a lease store; shared services must declare their
isolation mechanism.  Physical diagrams (racks, regions, networks) are BLOCKED on
a real target environment.
