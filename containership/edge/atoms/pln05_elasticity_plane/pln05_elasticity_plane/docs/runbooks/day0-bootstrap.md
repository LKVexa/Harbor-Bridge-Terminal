# Day 0 — bootstrap (empty host → healthy plane)

Prerequisites: CPython 3.10–3.13; a key ring from the platform KMS (≥ 32-byte HMAC keys with windows); writable `state_dir`, `config_dir`, `audit_path` on an encrypted volume; a coordination service adapter implementing `LeaseService` (acquire/renew/release); a target consumer implementing the `FencedSink.apply` contract.

1. Verify the artifact: `python -c "from pln05_elasticity_plane.supplychain import verify_artifact; ..."` against `SHA256SUMS` and `security/approved-versions.json` (or `sha256sum -c SHA256SUMS` + version check). Refuse anything unapproved.
2. Install offline: `python -m pip install --no-index pln05_elasticity_plane-4.2.0-py3-none-any.whl` (no runtime dependencies; see `docs/release-policy.md` for mirrors).
3. Validate the site overlay: `python -m pln05_elasticity_plane validate-config site.json --layer site` — must print `"valid": true`.
4. Start the embedding service constructing `ElasticityPlane(instance_id=..., ring=..., state_dir=..., config_dir=..., audit_path=..., lease_service=..., sink=...)`; activate the overlay with a `platform_operator` credential.
5. Verify: `plane.health()` → `ready: true`, `state: healthy`; `plane.status()` shows the expected config checksum and schemas.
6. Declare envelopes from PLN-01 (`submit_limits`) for each workload; confirm `status(admin)` lists the scopes.
7. Archive the evidence baseline: copy `evidence/` from the release and the audit anchor.

Failure handling: config invalid → fix overlay (nothing activated); `R_NO_ACTIVE_KEY` → load keys; `E_STATE_CORRUPT` at start → restore state from backup (`backup-restore.md`), never delete silently.

Windows: identical commands with `py -3` in place of `python`; paths in the overlay use forward slashes.
