# Crash-consistency & restart (INV-38-C057)

Mutable state is classified ephemeral/reconstructible/durable. A restart bumps a
generation/epoch (`recovery.py`); descriptors/keys from a prior incarnation are
rejected. MR keys and queue handles never survive a device reset and are
recreated and rebound. In-flight ops are classified completed / unknown-replayable
/ rejected / caller-reconcile. Recovery revalidates identity/policy before
recreating privileged resources. Checkpoint schema:
`schemas/recovery-checkpoint-v1.schema.json`. Tests: `tests/test_recovery.py`.
**Status:** `IN_PROGRESS` — real crash/device-reset recovery needs hardware.
