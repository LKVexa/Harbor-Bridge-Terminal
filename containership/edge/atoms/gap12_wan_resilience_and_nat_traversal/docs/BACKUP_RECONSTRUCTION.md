# GAP-12 backup / reconstruction guidance

- **Durable** (back up): `PathStore.save()` snapshot (peers, failures, remaining retry window, relay bytes),
  audit log (hash chain), configuration activation history, waiver register.
- **Reconstructable** (do not back up): candidate cache, quality windows, NAT classifications, DNS cache.
- **Discarded**: in-flight attempts, TURN allocations (re-allocated), punch tickets.
- **Revalidated after restore**: every path starts `unknown` and must be re-probed; nothing restored is "healthy".
- Integrity: snapshots carry a SHA-256 digest; a mismatch or a future schema version is refused.
