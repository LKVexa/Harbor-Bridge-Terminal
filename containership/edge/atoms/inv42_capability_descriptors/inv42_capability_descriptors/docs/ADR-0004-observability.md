# ADR-0004: Redacted observer event stream (MC-017, MC-020 to MC-026)

**Status:** Accepted in 4.3.0.

## Decision

`DescriptorTable(observer=...)` emits one `PK_DESCRIPTOR_EVENT/1` event per operation. The event is emitted after the decision has been made, and a failure in the observer is swallowed.

Each event contains:

- `op`
- `outcome` code
- `table_fp`, a 64-bit SHA-256 label derived from the table id (not reversible to the id)
- `number`
- `type`
- `duration_ns`
- `ts`

It never contains the auth tag, the table id, the key, or the resource.

The following sinks all consume this one stream:

- metrics
- logs
- tracing
- audit
- rollout

## Consequences

- Telemetry cannot change a security outcome.
- Descriptor numbers appear in events. They are not authority, but they have high cardinality, so metrics exclude them (TELEMETRY_POLICY.md).
