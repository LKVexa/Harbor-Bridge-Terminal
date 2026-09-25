# Release/infra lineage correlation (INV-38-C078)

Canonical resource identifiers (`observability/resource-identity.schema.json`)
link INV-38 instances to node/site/environment/workload/tenant/device/release/
config-generation. Release/build identifiers are received at the boundary rather
than inferred from mutable labels; tenant labels cannot overwrite authoritative
identities. Lineage attaches to logs, traces, decisions, benchmarks and audit
events. **Status:** `IN_PROGRESS` — live infra-graph correlation needs the graph
service.
