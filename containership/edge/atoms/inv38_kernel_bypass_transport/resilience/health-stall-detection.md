# Health & stall detection (INV-38-C052)

Stall indicators use oldest-in-flight age and completion progress, not queue
depth alone (`health_stall.py`, `resilience/thresholds.yaml`). Warning/degraded/
failed thresholds derive from baselines/SLOs with hysteresis to prevent flapping.
Remediation escalates alert → shed load → kernel fallback → drain → operator.
Zero-budget safety signals page immediately. Synthetic stall tests in
`tests/test_health_stall.py`. **Status:** `IN_PROGRESS` — real device-reset
detection latency needs hardware.
