# Configuration — `DOC-INV52-CFG` v4.3.0 (C032-C040)

## Immutable vs mutable (C032)

| Class | Items | Where | Changed by |
|---|---|---|---|
| Immutable artifact | the Python package (all `*.py`, `schemas/`, `CHECKSUMS.sha256`) | wheel / image, digest in SBOM | release only |
| Mutable configuration | `PK_MSG_CONFIG/1` layers: limits, topics & publishers, topic states, admission, telemetry | config store, overlays | `ConfigManager.activate` |
| Mutable runtime state | subscriptions, dead letters, decisions, counters, dedup window, replay cache | process memory | application / traffic |
| Secret material | token keys, `dapr-api-token`, broker credentials | platform secret store | never in config (validation rejects) |

## Declarative model and secure defaults (C033)

Schema: `schemas/PK_MSG_CONFIG_1.schema.json`; defaults: `config.DEFAULTS` — no topic has publishers, every bound finite, dedup on (4,096), predicates see a read-only view, admission on (1000/s, burst 2000), telemetry never exports payloads.

## Validation before activation (C034)

`config.validate` returns every problem; `activate` refuses on any (unknown keys, out-of-range limits, wildcard publishers, duplicate topics, bad states, secrets, bad telemetry). The new bus is built completely before swap; a failing `health_check` keeps the previous generation.

## Site/environment layering (C035)

`layered(base, env, site)`: maps merge, lists replace. Examples: `examples/config/base.json`, `env.prod.json`, `site.edge-1.json`. Same artifact everywhere.

## Provenance (C036)

Every activation records `digest` (sha256 of canonical JSON), `version`, authenticated `author`, `declared_author`, `activated_at` (UTC), `change_ref`, `layers`.

## Atomicity and rollback (C037, C038)

Swap is a single reference assignment under the manager lock after full construction (tested with a concurrent reader). Operator rollback: `ConfigManager.rollback(author, reason)`; automatic: `health_check` refusal. Subscriptions carry over across generations.

## Secrets (C039)

`security.find_secrets` rejects secret-looking keys/values (`password`, `token`, `api_key`, private keys, AWS/GitHub keys, JWTs, `password=` in connection strings). References use `secretref:<store>/<name>`. Adapter credentials are fetched per call (`DaprHttpAdapter(api_token=callable)`).

## Bootstrap (C040)

`lifecycle.bootstrap(layers, author, dependencies)`: validate → build → probe dependencies → READY; a failed critical/security dependency leaves the component CONFIGURED (not serving). Day-0 runbook: OPERATIONS.md §1.
