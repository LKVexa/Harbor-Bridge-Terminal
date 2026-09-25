# Disaster recovery and site failover

Traceability: C055, C089, C095; MC-039-02, MC-040.

## Objectives
| Scenario | RPO | RTO | Mechanism |
|---|---|---|---|
| Process crash | 0 (fsync) | < 30 s | restart + WAL recovery |
| Disk loss (single member) | last verified backup (target ≤ 15 min, backup every 15 min) | < 30 min | `restore_backup` into a new data dir |
| Site loss with GAP-05 follower | replication lag at failure (alert > 100 revisions) | < 15 min | promote follower with epoch+1 |
| Corruption detected | last verified backup | < 30 min | quarantine, preserve evidence, restore |
| Provider loss | as site loss | as site loss | follower in second provider/region permitted by residency |

## Authority and triggers
Failover is declared by the incident commander (SEV1) with the service owner; triggers: primary unreachable > 5 min with quorum loss, or confirmed data corruption. Automation may *prepare* (fence, snapshot) but promotion is a human decision.

## Safety during partition/loss
Only the site holding the highest epoch may accept writes. Promotion: (1) fence old primary (`role=replica`, epoch refused), (2) promote follower with `epoch+1`, (3) update service discovery (DNS/Service endpoint to the new site VIP), (4) clients reconnect and relist/resume. Stale batches/snapshots from lower epochs are refused (`CSTATE_FENCED`).

## Residency
Followers are only placed in regions allowed for the tenant set; backups inherit the source region's residency tag.

## Failback
Old primary rejoins as a follower, discards divergent tail (detected by revision/digest comparison), resyncs from the new primary snapshot; failback is a planned second failover.

## Backup verification
Every backup is re-read, decrypted, checksum/HMAC verified and invariant-checked before being marked `verified`; a weekly automated restore into an isolated directory runs `tools/restore_drill.py`.
