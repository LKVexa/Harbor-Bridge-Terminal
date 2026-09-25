# RB-DAY0 — Bootstrap (MC-064-T01)

Owner: SRE on-call owner (UNASSIGNED). Escalation: `governance/owners.json`.

1. **Prerequisites.** Linux x86_64 with CPython 3.11 and `cryptography` from `constraints.txt`. A journal volume with POSIX `flock` and durable `fsync` (local ext4/xfs; NFSv4.1 only if your storage team confirms lock semantics). An IdP issuing EdDSA JWTs for audience `inv66-control-plane`. A TLS server certificate plus the CA used for workload mTLS (SPIFFE URIs).
2. **Service identity and secrets.** Create a service account that is the only one allowed write access to the journal volume. Put the anchor signing seed in the secret manager and reference it as `env:` or `file:` (`production/keys.py`). Never put it inline in config.
3. **Install.** `pip install --require-hashes -r constraints.txt && pip install .` (or the container in `deploy/Dockerfile`, which runs as non-root with a read-only root filesystem).
4. **Validate config.** `python -m inv66_enterprise_wasm_control_plane.production.cli validate-config config/examples/base.json config/examples/prod.json config/examples/site-eu-west-1.json`
   Expected: `{"valid": true, "generation": "<64 hex>", "environment": "prod"}`. Record the generation.
5. **Bootstrap the first generation** (the only activation allowed without approvers, and only on an empty store). Use `ControlPlaneService.config.stage(...)` then `activate_config(..., bootstrap=True)`. This is journaled as `bootstrap: true`.
6. **First anchor.** `cli anchor ROOT --key-ref env:INV66_ANCHOR_KEY`. Store the printed `public_key` in the trusted-keys file that auditors use. Keep it outside the journal volume.
7. **Verify.** `cli verify-journal ROOT --trusted-keys keys.json` → `"result": "INTACT"`.
8. **Evidence.** Archive the outputs of steps 4, 6 and 7 with the release evidence.
