# Configuration and secrets (INV30-GAP-023, GAP-025 · INV-30-C032–C040, C047)

* **Immutable vs mutable (C032):** code, schemas and `config/default.json` ship in the signed artifact; only the
  selected overlay + an optional operator patch are mutable. Runtime state (handles) is volatile.
* **Secure defaults (C033):** development mode, rollout `off`, `require_hardware=false`, model-for-hardware forbidden.
* **Validation (C034):** schema + limit checks + production rules (minting key ref required, no debug logs,
  forbidden knobs). Any error → `CONFIG_INVALID`, nothing activated.
* **Overlays (C035):** `cloud`, `datacenter`, `near-edge`, `far-edge`.
* **Provenance (C036):** `ConfigStore.activate` records version, sha256 digest, author, reason, time.
* **Atomicity (C037):** write-temp + fsync + `os.replace`; failed validation leaves the active config untouched.
* **Rollback (C038):** `ConfigStore.rollback` (operator) and automatic rollback when `ops promote` health gates fail.
* **Secrets (C039, C047):** config holds only `env:NAME` / `file:/path` references; inline values ≥16 chars are
  refused; secret files must be 0600; logs/decisions are redacted. INV-30 stores no sensitive data at rest; the
  audit ledger is integrity-protected (HMAC) — confidentiality at rest and TLS in transit are provided by the host
  platform (documented dependency; key rotation = rotate the referenced secret and restart, which invalidates all
  handles by design).
* **Bootstrap (C040):** see RUNBOOKS.md day-0.
