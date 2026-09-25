# INV-17 State Backup / Restore Applicability

**Controls:** C095 (checklist §57); related C057 (§29).

## Decision: backup/restore of stream state is **Not Applicable**

### Rationale (from code)

- Stream state (`stream::Stream` buffer, credit, flags, idempotency window) lives only in process memory; `control::StreamRegistry._streams` is a plain dict. No persistence API exists.
- Elements are in-flight transport data; the source of truth is the producer. Persisting them would create a second copy with no consumer contract for replay.
- `StreamRegistry.get` explicitly raises `StreamNotFound` "streams do not survive restart".

### Reconstruction = reopen

1. Client receives `StreamNotFound` (or connection loss).
2. Obtain a fresh capability (`CapabilityAuthority.issue`).
3. `StreamRegistry.open(...)` with a new or same id.
4. Reader grants credit; producer re-sends from its own checkpoint using idempotency keys.

## State that *does* need preserving

| Item | Mechanism | Owner action |
|------|-----------|--------------|
| Signing keys (`KeyRing`) | supplied by host key service | back up in the key service, not here |
| Configuration | `config/*.json` in source control + `ConfigManager` provenance | versioned in VCS |
| Audit ledger | `AuditLedger.export_jsonl()` + `anchor()` | ship to durable storage periodically (not implemented in package) |
| Emergency control state | in memory | re-apply after restart |

No restore drill has been run; tests/test_disaster.py covers reopen-after-loss behaviour.
