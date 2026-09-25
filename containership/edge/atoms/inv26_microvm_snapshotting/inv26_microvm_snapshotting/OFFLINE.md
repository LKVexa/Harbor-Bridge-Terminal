# Intermittent or absent connectivity (C018, C048, C056)

| Dependency down | Capture | Restore | Readiness | Notes |
|---|---|---|---|---|
| control plane | allowed (local callers) | allowed with already-issued, unexpired grants | ready | no new grants can be issued offline |
| identity / trust distribution | allowed while local trust store valid | same | ready | revocations published during the outage are not seen: bounded by credential lifetime ≤ 1 h |
| KMS | refused (`SNAP_KMS_UNAVAILABLE`) | refused | **not ready** | no DEK caching, by design (fail closed) |
| storage | refused (`SNAP_STORAGE_UNAVAILABLE`) | refused | not ready | |
| time source | tokens outside ±30 s refused | same | ready | clock discontinuity > skew fails closed |
| audit sink | allowed, events buffered (bounded) | same | degraded | privileged ops refused (`SNAP_AUDIT_UNAVAILABLE`); losses recorded as `audit.loss` |
| telemetry | allowed | allowed | degraded | exporter failures counted, never block |

**Reconnect reconciliation:** `reconcile()` (run at start-up and after an outage) resolves transient records,
removes orphan blobs and fails interrupted restores; duplicate operations are impossible because idempotency
keys and grant nonces are in the durable metastore; stale controllers are fenced by lease tokens.
**Not implemented:** a local KMS replica for edge tiers, offline grant issuance, partially-uploaded
object-store multipart cleanup (no object-store adapter). Partition/reconnect tests beyond the single-node
fault matrix need a multi-node environment (C089 PARTIAL).
