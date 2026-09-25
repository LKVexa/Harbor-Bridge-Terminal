# Technical debt and deprecations (MC-067-T03)

| ID | Kind | Item | Plan |
|---|---|---|---|
| D-01 | performance | One fsync per journal record; no group commit | Batch appends under one fsync, which raises throughput with the same durability. Measure with `tools/bench.py`. |
| D-02 | functional | The inventory stores admitted/delivered state only; observed runtime state from INV-63 is not ingested | Add an authenticated INV-63 status feed with versioned idempotent updates (MC-069-T03). |
| D-03 | scale | Inventory projection is one per replica, not sharded | Shard by tenant when inventory exceeds about 10⁶ entries. |
| D-04 | security | No re-encryption tool for sealed journal bodies after data-key rotation | A `cli rekey` that rewrites into a new journal and anchors the mapping. |
| D-05 | governance | No TTL/expiry on config generations or temporary grants | Add `not_after` on bindings; a review tool flags expired ones. |
| DEP-01 | deprecation | `control_plane.ControlPlane` (4.2.0 in-memory engine, unauthenticated `user` string) | Kept **only** as the pk_core behavioural fixture in `component.py`. It must not be used as a service. Removal planned for 5.0.0. |
