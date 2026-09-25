# Day 2 — operations (MC-25..MC-32, MC-68)

| Task | Procedure |
|---|---|
| Key rotation | `KeyStore.rotate(old_kid)`; old key moves to retiring (verifies, no signing). After max grant TTL: `revoke_key(old_kid)`. |
| Revocation horizon breach | `RevocationRegistry.horizon_breached(sites, now)` lists sites; `quarantine.freeze("sites", site)` until they acknowledge, then thaw. |
| Stale controller | A write with a lower epoch gets `revocation.stale_epoch`. Fence the old controller, bump `controller_epoch` on the new one. |
| Crash recovery | Restart. The log replays, a torn last line is cut off, anything else raises `revocation.corrupt` → restore from replica, compare `head` hashes. |
| Compaction | Daily `compact(now, epoch=)`; tombstones older than `not_after + retention` are removed, and the compaction itself is logged. |
| Degraded | `/healthz` names stalled loops. Issuance refusals are expected while dependencies are down. Verify keeps serving. |
| Partition drill (quarterly) | Stop acks from one site, confirm the breach is detected, freeze it, restore it, thaw. |
