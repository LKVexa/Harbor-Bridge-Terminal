# INV-17 Cost Model

**Controls:** C069 (capacity/cost), C064 (per-tenant overhead), C065-C066 (copy/serialisation cost)
**Owner:** UNASSIGNED — owner to fill
**Numbers:** none here. Unit costs are produced by `tools/bench.py` -> `benchmarks/results/latest.json` and `tools/capacity.py`.

## Cost drivers (from code)

| Operation | Work performed | Code |
|---|---|---|
| `Stream.write` | lock, state checks, `isinstance`, deque append, optional idempotency set/deque insert | `stream::Stream.write` |
| `Stream.read` | lock, deque popleft, notify | `stream::Stream.read` |
| `Stream.grant` | lock, bounds check, notify | `stream::Stream.grant` |
| Registry write | `get` (tenant check + token verify: base64, JSON, HMAC-SHA256, replay-cache expiry scan; nonce insert only for single-use tokens) + 2 × `buffered_total` O(N) + `Stream.write` | `control::StreamRegistry.write` |
| Token verify | `_expire` scans the whole replay cache (single-use nonces only) each call (O(cache size)) | `security::CapabilityAuthority._expire` |
| Audit record | canonical JSON + HMAC-SHA256 per event | `security::AuditLedger.record` |
| Metrics scrape | `stats()` on every stream | `observability::MetricsExporter.samples` |
| Codec | encode + copy to `bytes` | `adapters::CanonicalCodec` |

## Per-tenant attribution (PROPOSED method)

cost_tenant = (streams_t × c_stream) + (writes_t × c_registry_write) + (buffered_t × c_mem_per_elem)
+ (tokens_verified_t × c_verify). Coefficients measured by `tools/bench.py` per-tenant scenarios.
INV-17 exports no per-tenant metrics, so attribution needs the integrator's own counters or
pseudonymised audit/log records.

## Optimisation levers

Use direct `Stream` operations inside trusted code (skips token/quota cost); batch credit grants
(optional feature "credit batching"); keep replay cache sized to need; scrape at a moderate interval.
