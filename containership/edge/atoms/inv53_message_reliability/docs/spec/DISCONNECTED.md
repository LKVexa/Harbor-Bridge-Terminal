# Disconnected / intermittent-network semantics (C018)

1. **Consumer partitioned while holding a lease:** the lease expires at `deadline`; the message is
   redelivered to the next receiver under a new token. When the partitioned consumer returns, its ack is
   refused (`E_LEASE_STALE`); it must treat its work as possibly duplicated — hence consumer dedupe.
2. **Consumer needs longer than the lease:** heartbeat with `extend` before the deadline; an extend after the
   deadline is refused, never silently granted.
3. **Producer partitioned mid-put:** the producer cannot know whether the put landed. It retries the *same*
   message: `OK_DUPLICATE` if it landed, `OK` if not. A different payload under the same id is refused.
4. **Broker partitioned from its key provider:** authentication fails closed (`E_SECURITY_DEPENDENCY`). Far-edge
   sites therefore use locally provisioned keys (EnvKeyProvider) with rotation on reconnect.
5. **Broker partitioned from the audit/telemetry shipper:** the local audit log keeps appending; its head is
   anchored externally on reconnect so truncation during the partition is detectable.
6. **Clock drift:** leases use the broker's clock (clients cannot move it); authentication tolerates `skew_seconds` of client drift.
7. **Reconnect storm:** tenant token buckets and the shed watermark bound the burst; refusals carry
   `retry_after` from full-jitter backoff so clients de-synchronise.
