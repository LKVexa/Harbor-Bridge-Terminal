# Runbook: Day-0 Bootstrap

| Field | Value |
|---|---|
| Document ID | INV63-RB-DAY0 |
| INV-63 C-IDs covered | C040, C096 |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role), Security contact (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change. |

Goal: empty node → ready INV-63 instance for one site, deterministically, gated by preflight (A-01..A-08, `docs/architecture/ASSUMPTIONS.md`).

## Prerequisites
1. Python 3.11–3.13 (`pins.json`: `>=3.11,<3.14`); `cryptography==46.0.7` installed.
2. Package integrity: verify files against `MANIFEST.sha256` (`sha256sum -c MANIFEST.sha256` from the package dir).
3. Secrets provisioned at the `secret_refs` paths in `deploy/config/base.json`: (only `env:`/`file:` refs) `/run/secrets/inv63-token-keys` = JSON `{kid: hex}`, keys >= 32 bytes; `/run/secrets/inv63-data-key` = hex of exactly 32 bytes; `/run/secrets/nats.creds`. Never put secret values in config (`INV63-E-SECRET-IN-CONFIG`).
4. Host inventory JSON file `{host: spread_label}`; >= 2 labels preferred (A-03).
5. A dedicated state directory outside the package, owned by the service user (bootstrap sets mode 0700).
6. Wadm transport: **not bundled; Wadm UNPINNED** — without it the instance runs in offline/degraded mode only.

## Steps
1. Run the test suite on the target: `python -m unittest discover -s tests` — all must pass.
2. Validate the config composition for this env/site (fails closed on errors):
   `python tools/bootstrap.py --state-dir /var/lib/inv63 --config-dir deploy/config --env prod --site <site> --hosts hosts.json [--reference-time <unix ts>]`
   It composes + validates config → resolves `token_keys`/`data_key` → creates the state dir 0700, opens a sealed `Journal`, acquires the epoch → runs `preflight` (required checks must pass) → constructs `DeploymentService` and prints `status()` JSON. Any failure prints a `PK_DEPLOY_ERROR/1` to stderr and exits **3**. Re-running replays the existing journal. Bootstrap uses an empty `ArtifactVerifier({})` and no lattice transport; production wiring of trusted keys and the Wadm transport is separate.
3. Check `status()`:
   - `ready: true`, `leader: true`, `epoch >= 1`.
   - `preflight`: A-01, A-02, A-04, A-07 ok (required). A-03/A-06/A-08 may be false (preferred) — record them. A-08 is true only if the adapter reports `wasi-p2` and `component-model`.
   - `config_digest` recorded in the change ticket.
4. Take an initial backup (see `BACKUP_RESTORE.md`).
5. Hand over to Day-1.

## Failure handling
| Symptom | Code | Action |
|---|---|---|
| Exit 3, config rejected | `INV63-E-CONFIG-INVALID` / `INV63-E-SECRET-IN-CONFIG` | fix overlay; prod requires signed artifacts + encryption at rest; far-edge requires `offline_autonomy_s >= 300` |
| A-04 fails | `INV63-E-DEPENDENCY-UNAVAILABLE` | fix state dir permissions/disk |
| A-07 fails | `INV63-E-DEPENDENCY-UNAVAILABLE` | `pip install --require-hashes -r requirements.lock` |
| Secret missing | `INV63-E-DEPENDENCY-UNAVAILABLE` | provision the `file:`/`env:` secret |
| Preflight failed | `INV63-E-PRECONDITION`, `details.checks` | fix listed required checks |
| Journal refuses to open | `INV63-E-STATE-CORRUPT` | state dir not empty/corrupt — restore or wipe (Day-0 only) |

Last exercised: NEVER — game day required
