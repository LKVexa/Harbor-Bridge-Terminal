# Day-0 / Day-1 / Day-2 runbook (C040, C096)

**Day 0 — bootstrap:** `pip install .[crypto]` from the lock; create key files (authn, policy, state); write `host.json`; pin the implementation digest in `supply_chain/provider_catalog.json` (`python -m inv65_capability_providers.tools.release_gate --print-digest`); start `python -m inv65_capability_providers.host.server --config host.json`; check `/readyz` = 200; archive `evidence/` as baseline.
**Day 1 — deploy:** run `tools/release_gate.py`; verdict must not be NO_GO; roll out via `rollout/canary-policy.json` stages; watch `ProviderErrorBudgetBurn`.
**Day 2 — operate:** backups hourly (`tools/backup_state.py backup`); key rotation quarterly (docs/key-management.md); re-run gate on every change; review calendar in governance/.
