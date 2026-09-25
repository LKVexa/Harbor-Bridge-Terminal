# INV-61 Mutable State Inventory (M20 / C057, C095)

INV-61 holds no application data. Protocol-layer state:

| State | Location | Durability | Restart semantics | Loss impact |
|---|---|---|---|---|
| Idempotency results (done only) | memory + `state.json` | checkpoint after each keyed success (fsync + atomic rename) | restored; TTL restarts from restore time | duplicate execution possible for keys in TTL window |
| Fencing epoch / lease epoch | memory + `state.json` | on checkpoint | restored as max(local, checkpoint) — never decreases | stale-owner protection weakened until a new lease is issued |
| Audit chain head + seq | `audit.jsonl` + anchor in `state.json` | fsync per record | log re-verified on open; shorter-than-anchor log refused | tamper evidence lost → Sev-2 |
| Emergency-disable flag | `state.json` | checkpoint on change | restored (node stays disabled) | node could re-enable silently → prevented |
| Replay cache | memory only | none (by design) | empty after restart; frames issued before process boot are refused (`issued-before-boot`) | none: pre-restart frames cannot be replayed; calls in flight at restart are refused and must be re-issued |
| Counters/metrics | memory | none | reset (monotonic counters restart, scrapers handle resets) | none |
| Registered exports | code | n/a | re-registered at start | none |

Checkpoint format: `inv61-state/1` = `{format, sha256, state}`; a digest mismatch aborts startup.
