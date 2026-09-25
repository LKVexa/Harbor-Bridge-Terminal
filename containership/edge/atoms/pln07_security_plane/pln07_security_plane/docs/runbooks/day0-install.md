# Day 0 — install and bootstrap (MC-21, MC-68)

1. Verify the archive: `sha256sum -c MANIFEST.sha256` from the package folder. Stop on any mismatch.
2. Create a venv; `pip install -r lock/requirements.lock` (on the release builder first run `pip-compile --generate-hashes` and install with `--require-hashes`).
3. Run the gate: `python -m pln07_security_plane.ci.gate`. Expect `CONDITIONAL_GO` until external blockers close. `NO_GO` → stop.
4. Create service user `pln07`, state dir `/var/lib/pln07` (0700), config `/etc/pln07/config.json` via `ConfigStore.activate(..., author=, change_id=)`.
5. Provision `PLN07_AUTH_SECRET` from the secret store (≥ 32 bytes). Never put it in config.json.
6. Generate/import signing keys (GAP-07/HSM in production). Record key ids.
7. Start: `systemctl enable --now pln07` (or apply `deploy/kubernetes.yaml`).
8. Check `/readyz` = 200 and `/healthz` shows `revocation_chain_ok` and `audit_chain_ok` true.
