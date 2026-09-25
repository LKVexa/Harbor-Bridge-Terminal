# Day-0: installation and bootstrap (MC-051-01, MC-029)

Prerequisites: Linux x86_64/aarch64, Python 3.10–3.13, `cryptography` from `requirements.lock`, a data volume (ext4/xfs, honest fsync), PKI issuing SPIFFE client certs for trust domain `inv05.local` (or configured), secret files mounted 0600 at `/run/inv05/secrets`: `data-key`, `audit-key`, `token-key`.

1. Verify artefact digests: `sha256sum -c MANIFEST.sha256`.
2. Install pinned deps: `pip install --require-hashes -r requirements.lock`.
3. Runtime self-test: `python -c "from inv05_current_control_state_system.backend import runtime_self_test as t; print(t())"` → `ok: true`.
4. Validate config (no side effects): `python -m inv05_current_control_state_system.bootstrap --config deploy/config/base.json --env deploy/config/prod.json --site deploy/config/site-a.json --secret-dir /run/inv05/secrets --dry-run`.
5. Preflight: `python tools/preflight.py --config deploy/config/base.json --env deploy/config/prod.json --site deploy/config/site-a.json --secret-dir /run/inv05/secrets`.
6. Bootstrap: same as step 4 without `--dry-run`. Idempotent; writes `<data_dir>/bootstrap.json` (versions, digests, identities, checks, audit anchor).
7. Store `bootstrap.json` and the audit anchor in the release evidence bucket.
