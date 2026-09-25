# INV-32 interface schemas

Version 4.2.0 makes the reference model's public record formats explicit. These are Python mapping contracts in this standalone package; a language-neutral JSON Schema/WIT/RPC definition is still a documented production gap in `AUDIT_REPORT.md`.

## `PK_RESOURCE_ADJUSTMENT/2`

All successful guest mutations use this schema. Common fields are `schema`, `kind`, `operation_id`, `host`, `guest`, `tenant`, `reason`, `audit_schema`, `sequence`, `prev_hash`, and `event_hash`.

Memory adjustments additionally carry `from_mib`, the caller's original `requested_mib`, the bounded `target_mib`, `applied_mib`, `honoured_requested`, effective `honoured`, `clamped_to_ceiling`, `reversible_to`, and post-operation `host_free_mib`.

vCPU adjustments carry `from_vcpus`, `requested_vcpus`, `applied_vcpus`, and `reversible_to`.

Rollback events use `memory_revert` or `vcpu_revert` and link to the original v2 event using `reverted_event_hash`. A v2 rollback request is accepted only when the supplied record exactly matches an event in the host's verified audit history and the live guest state still matches the recorded applied state.

### Legacy compatibility

`PK_RESOURCE_ADJUSTMENT/1` rollback records are accepted only when their kind can be inferred unambiguously and their target passes current floor/ceiling/vCPU/reserve checks. Because v1 records have no authenticated host/event identity, they cannot provide the same provenance guarantee as v2 and should be retired by an explicit compatibility policy before production use.

## `PK_HOST_RESOURCES/1`

`ElasticHost.host_snapshot()` returns `schema`, `host`, `total_mib`, `reserve_mib`, `allocated_mib`, `free_mib`, `guest_count`, and `audit_head`.

## `PK_RESOURCE_AUDIT/1`

Every successful local resource mutation is appended to a SHA-256 hash chain. `sequence` is monotonic, `prev_hash` points to the preceding event, and `event_hash` covers the canonical JSON representation of all other event fields. `verify_history()` validates the complete in-memory chain and mutating operations fail closed when chain corruption is detected.

The chain is tamper-evident, not durable or externally anchored. Durable storage, rotation, timestamping, signing/attestation, export, retention, and centralized audit ingestion remain missing production components.
