# Ownership fencing (INV-38-C058)

INV-38 enforces a single writer per node/device/queue. Remotely managed ownership
uses lease/epoch fencing (`fencing.py`, `resilience/lease-epoch.schema.json`): a
stale controller cannot mutate device/config state after leadership changes, and
registrations/queue pairs/operation IDs are bound to the current epoch. Network
partitions never let both sides assume authority. Split-brain model tests in
`tests/test_fencing.py`. **Status:** `IN_PROGRESS` — true partition/fencing needs a
multi-node cluster.
