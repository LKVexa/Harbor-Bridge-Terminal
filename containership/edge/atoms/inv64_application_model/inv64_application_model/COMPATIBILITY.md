# Supported-version compatibility (MC-27, MC-30; C084, C093)

Source of truth: **`compatibility.json`**. This page explains it; `tools/governance_check.py` fails CI if `pyproject.toml` (requires-python, classifiers) or the CI matrix contradict it, and `tools/preflight.py` enforces it at install/bootstrap time.

| Dimension | Range / rows | State | Evidence in 4.3.0 |
|---|---|---|---|
| CPython | 3.10 – 3.13 | required (all four in the CI matrix) | 3.11.15 executed locally; others defined in CI, not yet run |
| linux-x86_64 | — | required | executed |
| linux-aarch64, windows-amd64, darwin-arm64 | — | supported | CI rows defined, not run |
| darwin-x86_64 | — | experimental (excluded from production certification) | none |
| schema `app/v1` | 4.0.0 → | required | tests |
| protocol `PK_APP_SUBMIT/2` | 4.3.0 → | required | tests |
| protocol `PK_APP_SUBMIT/1` | 4.3.0 → 5.0.0 | deprecated (REG-001) | tests |
| contract families `PK_APP_*/1` | 4.3.0 → | required | schemas + tests |
| pk_core | **unknown** | required-for-conformance, **BLOCKED** (no pin) | preflight reports BLOCKED |
| OAM baseline | oam-dev/spec v0.3.0 @ 3104d27a | schema/conceptual profile | OAM_PROFILE.md fixtures |
| INV-10 `PK_COMPOSE_RESOLVE` | v1 – v2 | emulator only | integration (min + current) |
| INV-63 `PK_DEPLOY_HANDOFF` | v1 | emulator only | integration |
| INV-65 `PK_PROVIDER_BIND` | v1 | emulator only | integration |
| INV-66 `PK_GUARDRAIL` | v1 – v2 | emulator only | integration |
| cryptography (optional) | ≥ 42 (tested 46.0.7) | supported | tests |

Canonical digests are platform-independent: canonical bytes are UTF-8 JSON text with sorted keys (no binary integers, no endianness); floats are printed by CPython's shortest-repr algorithm, identical on all supported platforms.

## Support lines and EOL

| Line | State | Security fixes |
|---|---|---|
| 4.3.x | supported | until 6 months after 5.0.0 |
| 4.2.x | deprecated | until 2026-12-31 (no authn/authz/audit — upgrade) |
| 4.1.x, 4.0.x | unsupported | none |

## Upgrades, downgrades, migration

- 4.2.0 → 4.3.0: manifests carrying inline secrets are now **rejected** (`secret.inline`) — migrate them to `secretref://`. Deeply nested (> 64) manifests are rejected. Everything else is additive. No persisted state existed in 4.2.0.
- Downgrade 4.3.0 → 4.2.0: supported for the pure API; ConfigStore/audit state is ignored by 4.2.0 (it has none).
- Removing a matrix row: announce in CHANGELOG one minor release ahead, mark `deprecated` with a date, then `unsupported` (SECURITY_RESPONSE.md EOL notice period: 90 days).

History of this matrix is kept in `compatibility.json` `history` and in git.
