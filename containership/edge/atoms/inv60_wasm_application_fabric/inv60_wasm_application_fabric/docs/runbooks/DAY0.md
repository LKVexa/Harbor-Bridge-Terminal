# Day 0 — bootstrap (M33/M82)

**Prerequisites:** Python ≥ 3.10, Node ≥ 18 (for the WebAssembly reference tier and cross-language fixture check). No network access is needed for the reference fabric. Production additionally requires the pinned wasmCloud/NATS/wadm set in `SUPPORT_MATRIX.json` (not yet available — W-M25).

1. Verify the release: `python3 -B tools/verify_release.py` — every file matches `SHA256SUMS`.
2. Bootstrap: `python3 -B tools/bootstrap.py --dir ./site-a --env production`.
   - Validates and renders `config/base.json` + the environment overlay; refuses insecure values.
   - Creates the trust domain, issuer key, one-time enrolment codes (printed once, never written), empty state store and audit ledger.
   - Runs post-bootstrap health checks; writes `site-a/bootstrap-evidence.json` (versions, hashes, config digest, health).
   - Re-running converges: existing keys/state are reused, nothing is duplicated.
3. Archive `bootstrap-evidence.json` and the ledger head `(seq, hash)` outside the site (external anchor).

**Failure path:** any failed check exits non-zero and leaves `bootstrap-evidence.json` with `"ok": false` and the failing check; remove the directory and re-run after fixing — forensic logs are kept in `site-a/bootstrap.log`.
