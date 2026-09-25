# INV-54 normative requirements  (controls C011, C012, C013; components 03, 04)

Key words MUST/SHALL/SHOULD per RFC 2119. Each requirement has a stable ID used by
`evidence/traceability.json`. Scope: the INV-54 package; non-goals per `contract.py`.

## Invariants (all profiles)
- **REQ-INV-001** Fan-out SHALL deliver every accepted message to every subscriber registered at publish time, or to none (`reject` policy); `drop_oldest` SHALL report `Outcome.DEGRADED` and count drops. — `service._fanout`, `test_c68_*`
- **REQ-INV-002** The log SHALL preserve publish order per key within a partition. — `brokers.PartitionedLog`, `test_c13_*`, `test_c86_*`
- **REQ-INV-003** Consumer offsets SHALL be independent per (tenant, stream, consumer, partition). — `test_c39_*`
- **REQ-INV-004** Consumers SHALL be able to replay from any retained offset; offsets below the low watermark SHALL fail with `INV54-E0401`. — `test_c48_*`
- **REQ-INV-005** Every boundary input SHALL be validated; invalid input SHALL fail with `INV54-E0001` and no side effect. — `test_c44_*`

## Deployment contexts
| ID | Context | SHALL |
|---|---|---|
| REQ-CTX-CLOUD | managed cloud | provider ∈ {kafka, sqs}; TLS 1.2+ with hostname verification; auth≠none; secrets by reference — `test_c03_deployment_contexts_validate` |
| REQ-CTX-DC | datacenter | provider ∈ {kafka, rabbitmq, durable}; same security floor as cloud — `test_c03_deployment_contexts_validate` |
| REQ-CTX-NEAR-EDGE | near-edge | provider=durable with replication `min_insync ≥ 2` where ≥3 nodes exist; fsync=always — `test_c03_deployment_contexts_validate`, `test_c49_quorum_replication_and_hw` |
| REQ-CTX-FAR-EDGE | far-edge / intermittent | provider=durable single node; `OfflineBuffer` on clients; bounded storage via retention; at-rest encryption on — `test_c03_deployment_contexts_validate`, `test_c09_store_and_forward_ordered_idempotent` |

A context not listed is **unsupported**; `config.validate` enforces the production floor for all.

## Non-functional (component 04) — targets are PROPOSED until owner approval
| ID | Attribute | Target | Evidence |
|---|---|---|---|
| NFR-LAT-1 | append latency (reference, in-process) | p99 < 2 ms | `evidence/benchmark.json`, `test_c62_c71_benchmark_harness_and_gate` |
| NFR-LAT-2 | durable append fsync=always | p99 < 50 ms on SSD | build-host only via `test_c62_c71_benchmark_harness_and_gate`; UNVERIFIED on target hardware |
| NFR-AVL-1 | availability (replicated durable) | survive loss of `n - min_insync` replicas without losing committed data | `test_c49_*`, `test_c50_*` |
| NFR-DUR-1 | durability | acknowledged write with fsync=always survives process crash | `test_c57_*` |
| NFR-CON-1 | consistency | reads expose only records below the high watermark | `test_c49_*` |
| NFR-ISO-1 | isolation | zero cross-tenant reads/writes | `test_c39_*` |
| NFR-STA-1 | startup | CREATED→READY in < 1 s for an empty durable store | `test_c04_startup_under_one_second` (build host) |
| NFR-THR-1 | throughput | ≥ 10k appends/s/partition (durable, fsync=batch) | not yet measured on target |
| NFR-STO-1 | storage | bounded by `retention.max_records`/`max_age_s` and hard ceilings | `test_c48_*` |
| NFR-REC-1 | recovery | torn tail truncated automatically; mid-file corruption refused | `test_c57_*` |
| NFR-EDGE-1 | edge power/thermal | characterised per device class | **UNVERIFIED** — no device available |
