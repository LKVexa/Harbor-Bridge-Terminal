# Replication, HA, fencing and residency  (components 49, 50, 55, 60)

`ha.ReplicatedPartition` models leader/follower replication with quorum commit (`min_insync`) and a high watermark; `ha.FencingAuthority` issues leases with monotonically increasing epochs. Followers reject lower epochs (`INV54-E0501`) and truncate divergent suffixes; a deposed leader cannot write after failover. `failover()` promotes the most caught-up live replica **within `allowed_sites`** (residency). Tests cover quorum loss, stale-leader fencing, dual-leader prevention, residency-constrained failover and partition→reconnect convergence.

**Limits (UNVERIFIED):** the transport is in-process; there is no network RPC, no persistent epoch store, and lease safety assumes bounded clock drift. Production HA for Kafka/RabbitMQ/SQS is the provider's own replication (ISR, quorum queues, SQS multi-AZ) and must be certified per provider.
