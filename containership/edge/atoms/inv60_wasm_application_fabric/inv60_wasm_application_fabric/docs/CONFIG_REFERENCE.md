# Configuration reference (M27) — generated from fabric/config.py

Schema `inv60.config/1.0.0`. Unknown fields are rejected. Secrets are references `secret://<backend>/<path>#v<n>` only.

Overlay trust order: {"base": 3, "production": 3, "staging": 2, "edge": 2, "disconnected": 2, "test": 1, "development": 1}.

| field | type | default | constraint | overlay protection |
|---|---|---|---|---|
| `transport.require_tls` | bool | `true` |  | true_only |
| `transport.nats_url` | str | `"tls://127.0.0.1:4222"` | ^tls:// | pattern |
| `auth.allow_anonymous` | bool | `false` |  | false_only |
| `auth.token_ttl_s` | float | `300.0` | (10.0, 900.0) |  |
| `auth.max_clock_skew_s` | float | `30.0` | (0.0, 120.0) |  |
| `membership.suspect_after_s` | float | `3.0` | (0.5, 60.0) |  |
| `membership.lost_after_s` | float | `8.0` | (1.0, 600.0) |  |
| `membership.isolated_serving_s` | float | `300.0` | (0.0, 3600.0) |  |
| `placement.allowed_regions` | list | `[]` |  | residency |
| `signing.min_slsa_level` | int | `2` | (1, 4) | min_only |
| `signing.require_signature` | bool | `true` |  | true_only |
| `resilience.max_attempts` | int | `4` | (1, 10) |  |
| `resilience.default_deadline_s` | float | `5.0` | (0.01, 300.0) |  |
| `resilience.breaker_threshold` | int | `5` | (1, 100) |  |
| `telemetry.trace_sample_ratio` | float | `0.1` | (0.0, 1.0) |  |
| `telemetry.export_endpoint` | str | `""` |  |  |
| `telemetry.retention_days` | int | `30` | (1, 400) |  |
| `storage.state_dir` | str | `"./state"` |  |  |
| `features.batching` | bool | `false` |  |  |
| `secrets.nats_credentials` | dict | `{"ref": "secret://vault/inv60/nats-creds#v1"}` | secretref |  |
| `limits.max_payload_bytes` | int | `1048576` | (1, 16777216) |  |
| `limits.max_artifact_bytes` | int | `33554432` | (1, 268435456) |  |
| `limits.max_components_per_tenant` | int | `256` | (1, 10000) |  |
| `limits.max_links_per_component` | int | `16` | (1, 256) |  |
| `limits.max_inflight_per_tenant` | int | `64` | (1, 10000) |  |
| `limits.max_inflight_global` | int | `1024` | (1, 100000) |  |
| `limits.rate_per_tenant` | float | `500.0` | (0.1, 100000.0) |  |
| `limits.burst_per_tenant` | int | `100` | (1, 100000) |  |
| `limits.max_registry_entries` | int | `4096` | (1, 1000000) |  |
| `limits.max_hosts` | int | `512` | (1, 10000) |  |
| `limits.max_decisions_retained` | int | `10000` | (100, 1000000) |  |
