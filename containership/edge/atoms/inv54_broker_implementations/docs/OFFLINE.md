# Intermittent / offline network semantics  (C018 · component 09)

- Clients on intermittent links SHALL use `service.OfflineBuffer` (bounded, FIFO, explicit overflow policy).
- Every buffered request carries an idempotency key; flush is at-least-once *transport*, effectively-once *effect* because the broker's `IdempotencyCache` returns the first result for a repeated key (horizon = cache capacity).
- Flush stops at the first retryable failure to preserve order; terminal failures are dropped and counted.
- While disconnected, consistency is **local-only**: no read-your-writes across sites. On reconnect, replicas catch up under the current epoch (`ha.ReplicaNode.replicate` truncates divergent suffixes from deposed leaders).
- Duplicates beyond the idempotency horizon are possible and are an INV-53 policy decision.
