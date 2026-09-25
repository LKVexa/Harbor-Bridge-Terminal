# Configuration reference — generated from `mc/ops.py::CONFIG_SCHEMA`

Configuration must be signed (`load_config(..., signature_ok=True)` after verification). Unknown keys are rejected.

| Key | Type | Default | Bounds | Runtime-mutable | Restart | Owner |
|---|---|---|---|---|---|---|
| `challenge_ttl_s` | float | 30.0 | [5.0, 300.0] | True | False | UNASSIGNED |
| `verdict_ttl_s` | float | 3600.0 | [60.0, 86400.0] | True | False | UNASSIGNED |
| `skew_budget_s` | float | 2.0 | [0.1, 30.0] | True | False | UNASSIGNED |
| `max_outstanding_challenges` | int | 100000 | [100, 10000000] | False | True | UNASSIGNED |
| `rate_per_principal` | float | 5.0 | [0.1, 1000.0] | True | False | UNASSIGNED |
| `policy_threshold` | int | 2 | [2, 9] | False | True | UNASSIGNED |
| `offline_max_age_s` | float | 86400.0 | [0.0, 604800.0] | True | False | UNASSIGNED |
| `require_revocation_info` | bool | True |  | False | True | UNASSIGNED |
