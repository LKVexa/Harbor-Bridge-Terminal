# INV-07 operations guide

## Install
`pip install .` (from the package root, see `pyproject.toml`) or run from source with Python ≥ 3.10 and `git` ≥ 2.31 on PATH. Container/Kubernetes assets: `components/deploy/`.

## Configure
1. Write `config.json` (`PK_GITOPS_CONFIG/1`, reference in `API_REFERENCE.md`); validate offline: `python -m inv07_gitops_transition_layer.components.cli config-validate config.json` (exit 64 on rejection).
2. Write `trust_roots.json` (`PK_GITOPS_TRUST/1`): commit keys (`purposes: ["commit"]`, identity = committer e-mail, scopes), builder keys (`provenance`), policy keys (`policy`).
3. Sign and install a policy bundle (`policy.sign_bundle`).
4. Put the Git credential in the tenant-scoped secret (`env:INV07_<TENANT>_...` or `file:/run/secrets/inv07/<tenant>/...`, mode 0600).

## Normal operation
`sync` runs one reconcile; the HTTP server (`server.serve`) exposes `/healthz`, `/readyz`, `/metrics`, `/v1/status`, `/v1/explain/<id>`, `/v1/sync`, `/v1/freeze`.

## Troubleshooting
Every failure has a stable code (`API_REFERENCE.md`). `retry=retryable` → the controller retries within budget; `terminal` → fix input/trust/policy; `operator` → human action (freeze, partial apply, corrupted state).

## Emergency controls
Freeze scopes: global (kill switch), tenant, ref, target. Freezes are durable and audited; global release needs `freeze.override` with a second approver.

## Recovery / upgrade / rollback
State is versioned (`STATE_VERSION`). Upgrade: stop → backup (`cli backup`) → install → start (recovery replays the journal). Rollback: stop → restore backup into an empty directory → start previous version. An unsupported state version refuses to start (`PKG-STATE-002`).

## Capacity limits (defaults)
`max_resources` 5,000 per instance; manifest ≤ 1 MiB each, depth ≤ 32; journal 64 MiB before checkpoint; admission queue 1,000. Measured local baseline in `evidence/perf_baseline.json`.

## Known failure modes
Git unavailable (retry → breaker → offline policy); target unavailable (compensate or PartialApply → freeze); clock untrusted (no mutation); lease lost (FencedOff, stop writing).
