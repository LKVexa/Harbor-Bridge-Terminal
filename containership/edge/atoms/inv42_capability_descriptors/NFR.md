# Requirements, deployment context and applicability — INV-42 4.3.0

Covers MC-011 (deployment context), MC-012 (quantitative NFRs), MC-013 (configuration applicability), MC-034 (edge power/thermal). Where this file uses SHALL, the requirement is traced in `TRACEABILITY.json`.

## SHALL requirements

The original `MASTER.md` is missing (waiver W-002). Until it's recovered, these statements, derived from `contract.py`, are the source of truth.

- R1. The component SHALL accept a descriptor only in the table that minted its authentication tag.
- R2. The component SHALL authenticate schema, table, number and type together.
- R3. The component SHALL never reuse a descriptor number within a table session.
- R4. The component SHALL reject closed, foreign, forged, tampered, legacy-v1 and type-confused descriptors with a typed, stable error code.
- R5. The component SHALL bound live descriptors (1024) and lifetime allocations (1,048,576) per table.
- R6. The component SHALL reject use of a table after fork, destroy, or emergency disable.
- R7. The component SHALL NOT emit auth tags, table ids, keys or resources in telemetry, audit or errors.
- R8. Descriptors crossing a process boundary SHALL use `PK_DESCRIPTOR_TRANSPORT/1` (TLS 1.3 mTLS).

## Deployment contexts

| Context | Applicability | Notes |
|---|---|---|
| Cloud / datacenter | Supported | Standard profile. |
| Near-edge | Supported | Same code; thresholds in `PERF_THRESHOLDS.json` need re-baselining on the target CPU. |
| Far-edge / disconnected | Supported | No network dependency at all. See "Disconnected" below. |

### Disconnected

The runtime makes no network calls. With intermittent or absent connectivity, local open, resolve and close keep working. Only cross-host transfer (`transport.py`) fails, and it fails closed. An injected `key_provider` is called only at table creation. If it's unreachable, table creation fails with `key_unavailable`, and existing tables are unaffected.

### Precedence

When requirements conflict, they take priority in this order: **security > isolation > residency > correctness (non-reuse) > availability SLO > latency SLO > cost.** For example, saturation never triggers number reuse. Emergency disable outranks availability.

### Unsupported

The following aren't supported:

- cross-site number portability;
- persisting descriptors across restart;
- sharing keys between tables;
- serializing a table;
- running on interpreters without `hmac.compare_digest`.

## Quantitative

| NFR | Target | Evidence |
|---|---|---|
| Security SLOs (binding, non-reuse, type fidelity) | 0 violations, no budget | contract.py, test suites |
| Latency p50/p95/p99 per op | see `PERF_THRESHOLDS.json` (e.g. resolve ≤ 35/45/170 µs) | `tools/bench.py` |
| Availability of local ops | 99.99% monthly of calls not failing with an internal error | SLO.md |
| Determinism | Same inputs produce the same outcome codes; numbering is strictly monotonic from 3 | test_descriptors |
| Throughput | ≥ 20k open+close/s per table on the reference host | bench soak (measured ~50k/s) |
| Memory | ≤ 400 KiB peak per 1k live descriptors | bench fleet |
| Durability | None by design. Restart revokes everything. | OPERATIONS.md |

### Failover

N/A. Tables are process-local and deliberately non-replicable. Failover means clients re-acquire descriptors from the new process. Replicating a table would violate R1 and R3.

### Efficiency

The HMAC is computed once per operation. There are no copies beyond one small dict, and no I/O. Kernel-bypass and zero-copy optimisations are N/A because the component does no I/O.

## Configuration

The runtime has **no mutable configuration**:

- limits are code constants;
- the key is generated per table;
- the only runtime switch is `INV42_EMERGENCY_DISABLE` / `emergency_disable()`, which is a safety control, not configuration.

Configuration validation, site overrides, provenance and atomic update (C034–C037) are therefore **N/A**. If configuration is ever introduced, it MUST follow these rules:

- ship as a signed, versioned document validated against a schema before activation;
- fail closed on errors;
- be recorded with author and activation time in the audit chain;
- be applied atomically by swapping a whole immutable config object.

## Edge power

N/A as a separate measurement. The component is pure CPU (about 10 µs per operation) with no polling, timers or background threads, so its energy cost is proportional to operation count. That is already captured by the benchmark. If a far-edge SKU with a hard power envelope is adopted, run `tools/bench.py --soak 600` under the vendor's power meter and add the result here.

## External services

The runtime depends on none. If identity, attestation or policy services are introduced, they come in via `key_provider` or a `delegation` policy. Both treat failure or timeout as a **denial**. Wall-clock time is used only in telemetry timestamps and never in a security decision.
