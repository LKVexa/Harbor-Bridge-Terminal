# Continuous integration (MC-23)

Workflow: `.github/workflows/ci.yml`. **It has not yet run on GitHub** - the repository was supplied as an archive; the same gates were executed locally with `python -m inv36_control_transport.audit` (evidence in the work order).

| Job | Trigger | What it gates |
|---|---|---|
| test | PR, push, nightly | matrix Python 3.11/3.12/3.13 x (x86_64, arm64): compileall/import, IDL drift, unit+integration in normal and `-O` mode, traceability, checklist ledger, docs consistency, secret scan, 300-iteration property/fuzz campaign, perf smoke vs baseline |
| lint | PR, push | ruff (E, F, W, B, S) and mypy |
| security | PR, push, nightly | hash-pinned lock generation, `pip-audit --require-hashes`, runtime license check |
| build | after test/lint/security | wheel + sdist from clean checkout, manifest allow-list, clean-venv install + round-trip smoke, SBOM, provenance |
| nightly | schedule | 20,000-iteration fuzz (date seed), full benchmark + regression gate, 10-min soak + 200-guest fleet, full local gate evidence (400-day retention) |
| real-vsock | schedule, only when a certified self-hosted runner exists | `tools/vsock_smoke.py --peer-cid` end-to-end over real AF_VSOCK |
| release | `v*` tags | protected `release` environment; downloads the validated `dist` artifact (never rebuilds); `audit --certify` bound to the wheel digest; signing step fails closed until the managed signing identity is configured |

Controls: actions pinned by commit SHA; `permissions: contents: read` by default, `id-token: write` only in `release`; PR runs cancel superseded runs, release runs do not; every job has `timeout-minutes`; no dependency cache (so caches cannot bypass integrity checks); artifacts retained 90 days (evidence 400 days).

Owner actions required: enable branch protection with required checks `test`, `lint`, `security`, `build` and CODEOWNERS review; configure the `release` environment reviewers; provide the self-hosted vsock runner and signing service.
