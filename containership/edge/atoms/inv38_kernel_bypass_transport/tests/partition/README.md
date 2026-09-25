# Disaster/partition/reconnect tests (INV-38-C089)
`test_model_faults.py` injects crash/stale-key/fencing/partition faults into the
model and asserts no duplicate/lost completion outside documented semantics. Real
device-reset/partition on hardware is IN_PROGRESS.
