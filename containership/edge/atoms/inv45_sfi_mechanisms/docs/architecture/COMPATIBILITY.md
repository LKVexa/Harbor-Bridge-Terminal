# Compatibility, dependencies and supported versions (C016, C027, C093, A2)

Machine-readable matrix: `release/compatibility.json` (checked by `CompatibilityPolicyTest`).

## Policy

* **Explicit match, no negotiation.** Every boundary object carries a schema/profile id. A consumer accepts
  exactly the ids listed in `compatibility.json`; anything else is `SFI_UNSUPPORTED_VERSION`. There is no
  version negotiation, so there is nothing to downgrade: an attacker cannot force an older schema.
* **Supported window.** Current major only for schemas (`/1`). When `/2` of any schema ships, `/1` stays
  accepted for one minor release (deprecation window) and the acceptance is listed explicitly in
  `compatibility.json`; removal is a major component version.
* **Upgrade order.** Verifier/service first (it must understand what it seals), loader second (same process
  today), engine last. Mixed service versions MUST NOT share a config generation directory or state root
  (single owner, fenced — C058).
* **Older loader / newer report.** Refused (`SFI_UNSUPPORTED_VERSION`).
  **Newer loader / older signed artifact.** Artifact statements are version-independent Ed25519 over
  canonical JSON; accepted if the trust root is valid and the workload's anti-rollback floor allows it.
* **Enum expansion.** New error codes may be added; consumers handle unknown codes by `category`/`retryable`.
  New lifecycle states or result classes are breaking.
* **Downgrade prevention.** Descriptors bind `profile_sha256`, `config_sha256` and `verifier_version`; a
  config change invalidates outstanding descriptors (`T08`). Anti-rollback floors refuse older artifacts
  (`T07`).

## Supported version matrix (this release)

| Component | Supported | Evidence in this release |
|---|---|---|
| CPython | 3.10 – 3.13 | 3.11.15 (linux-x86_64) — only this row has passing evidence |
| Node.js / V8 | majors 20, 22, 24 (pinned 22) | v22.22.2 |
| cryptography | ≥ 41, < 47 | 46.0.7 |
| jsonschema (test lane) | ≥ 4.18, < 5 | 4.26.0 |
| `pk_core` | **UNRESOLVED** — no version/digest has been published to this repository | NOT RUN |
| Wasm binary | version 1 | fixtures |
| Profiles | `PK-SFI-WASM32-MVP-1` | fixtures |

Rows without passing evidence are **declared, not certified**. The CI matrix (`.github/workflows/ci.yml`)
runs 3.10–3.13 × Node 20/22 so the matrix fills in when CI runs on the target runners.

## `pk_core` dependency (A2)

`pk_core` is the external checklist framework used by `component.py` / `contract.py` for the 100-item gate.
Its source, license, public API version and digest are not available to this repository, so it cannot be
pinned here. 4.3.0 therefore:

1. makes the package importable without it (`PK_CORE_ERROR` explains the absence);
2. keeps `tests/test_component.py` skipping with an explicit reason, and `tools/ci.py` reports the
   `pk-core-gate` lane **NOT RUN** (never PASS);
3. records the absence in release evidence (`release/evidence.json` → `pk_core: absent`).

To close A2 the owner must publish `pk_core` with a version and digest, add it to `constraints.txt` with
`--hash`, and flip the lane to required.
