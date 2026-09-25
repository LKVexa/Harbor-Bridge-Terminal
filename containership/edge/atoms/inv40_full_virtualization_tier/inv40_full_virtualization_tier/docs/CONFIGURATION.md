# Configuration (INV-40-C032..C040)

**Immutable:** the package (`runtime.py`, `fvt/`, `schemas/`), digested in `MANIFEST.sha256`.
**Mutable config:** `PK_FULL_VM_CONFIG/1` documents, layered `SECURE_DEFAULTS → site → environment` (`fvt/config.py::layer`) — no rebuild needed to change a site.
**Mutable state:** `state_dir/` — `journal.wal`, `audit.jsonl`, `config/active.json`, `config/history.jsonl`.

Secure defaults: primitive required (const true), emulation forbidden (const false), nested virt / GPU passthrough / live migration off, telemetry on, `offline_mode=fail_closed`. Prod additionally requires an approved image allow-list and telemetry export, and refuses non-production providers.

Validation is fail-closed: schema (`additionalProperties:false`), secret scan (keys and values), cross-field rules. An invalid document never replaces the active one (`test_invalid_never_partially_applied`).

Provenance per generation: digest, generation, config_version, author, reason, activated_at, previous_digest. Tampering with `active.json` is detected by digest.

Activation is atomic (temp file → fsync → `os.replace`). Rollback: operator (`ConfigStore.rollback`) or automatic when the post-activation health check fails.

Secrets never live in config; keys come from a `KeyProvider` (KMS binding — blocker SEC-KMS).

## Deterministic bootstrap (C040)
```
python -m pip install .                    # stdlib only; no dependencies
python tools/bootstrap.py --state-dir /var/lib/inv40 --site dc1 --env staging
```
`tools/bootstrap.py` creates the state dir, activates the layered config, probes the host, and prints the health document; exit 0 only when `ready=true`. On a host without KVM it exits 3 with the probe reasons (it never starts in emulation).
