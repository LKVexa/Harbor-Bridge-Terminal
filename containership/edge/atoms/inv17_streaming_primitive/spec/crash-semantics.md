# INV-17 Crash, Restart, Resume and Replay Semantics

**Controls:** C057 (checklist §29); related C055/C058 (§28), C095 (§57).

## 1. Statement

INV-17 streams are **ephemeral, in-process, instance-local** objects. `control::StreamRegistry` keeps streams in a memory dict (`_streams`); `explain()` reports topology `instance-local`. Nothing is persisted.

## 2. On process crash or restart

| Item | After restart |
|------|---------------|
| Open streams, buffered elements, credit | Lost |
| Idempotency windows (`_seen_keys`) | Lost |
| Capability replay cache (`CapabilityAuthority._replay`) | Lost; a new `KeyRing` (default random key) invalidates old tokens unless keys are supplied externally |
| Freeze / disable flags, frozen scopes | Lost — re-apply controls after restart if the incident is ongoing |
| Audit ledger (`AuditLedger`) | Lost unless exported (`export_jsonl`) before exit |
| Active config | Rebuilt from config layers; `ConfigManager` history lost |

## 3. Resume / replay

- **No resume, no replay.** A holder of a pre-restart id receives `StreamNotFound` ("streams do not survive restart") and must reopen with a fresh capability.
- Elements in flight at crash time are **not delivered**; producers needing at-least-once must re-send from their own source of truth after reopen, using idempotency keys (dedup only applies within the new stream).
- Consumers cannot distinguish crash loss from a slow writer except through `StreamNotFound` on the next registry call; wrap waits with timeouts.

## 4. Failover

No replication or distributed failover exists (`spec` decision; see checklist §28). Failover = client reconnect to another instance and reopen.
