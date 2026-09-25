# Operations — INV-42 Capability descriptors

## Lifecycle

A table is process-local. Bootstrap creates a fresh table identity and 256-bit secret. `open()` mints monotonically increasing authenticated descriptors; `close()` permanently invalidates one descriptor; `destroy()` revokes all live descriptors and best-effort zeroizes the key. Restart creates a new table/session: descriptor numbers and wire payloads from the prior process are not recoverable authority and must not be restored.

## Capacity

- Live descriptors per table: 1024 (`TABLE_LIMIT`).
- Total allocations per table session: 1,048,576 (`SESSION_ALLOCATION_LIMIT`).
- Numbers 0–2 are reserved; first issued number is 3.
- Capacity rejection is fail-closed and counted in `status()`.

## Health signals

`DescriptorTable.status()` exposes live/issued/closed counts and counters for foreign resolution, closed replay, type mismatch, invalid descriptor, capacity rejection, and fork rejection. It intentionally excludes the table id, owner, key, resources, and authentication tags.

## Emergency action

There are three levels of emergency action:

- **Table:** call `destroy()`.
- **Process:** call `descriptors.emergency_disable()`.
- **Host:** set `INV42_EMERGENCY_DISABLE=1`.

`ROLLOUT.md` covers canary, rollback and fleet disable. `INCIDENT_RUNBOOK.md` covers severity and containment.

## Required external controls

4.3.0 ships the adapters for this: `transport.py`, `audit.py` and `telemetry.py`. It also ships `alerts/`, `dashboards/`, `SLO.md` and `TELEMETRY_POLICY.md`. Wire them up with `DescriptorTable(observer=telemetry.fanout(...))`.

The platform still has to provide the following:

- the deployment PKI (W-005);
- the release signing key in a KMS (W-004);
- on-call staffing (W-003).
