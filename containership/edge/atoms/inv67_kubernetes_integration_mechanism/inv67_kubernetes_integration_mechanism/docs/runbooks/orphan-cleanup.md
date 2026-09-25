# Runbook — orphan detection and cleanup
Orphans arise only from force-deleted objects (finalizer removed by hand). Compare runtime placements (SCH-01 list) with live `WasmWorkload` `status.appId`s; any appId without a live object is an orphan. Cancel through SCH-01 with the *current* leader's fencing token (read the Lease `transitions`). Record each cancel in the audit trail.
