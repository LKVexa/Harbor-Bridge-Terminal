# Support and End-of-Life Policy

| Version line | Status | Security fixes until | End of life |
|---|---|---|---|
| 5.0.x | Current | 12 months after 5.1.0 ships | 18 months after 5.1.0 ships |
| 4.2.x | Maintenance (reference model only, no endpoint) | 2027-03-31 | 2027-03-31 |
| ≤ 4.1.x | Unsupported | — | ended |

Patching: security fixes are released as patch versions on every supported line. Deprecated behaviors are announced one minor release before removal and tracked in `EXCEPTIONS.md`/`CHANGELOG.md`.

## Evidence retention
Each release keeps `evidence/*.json`, `RELEASE_MANIFEST.json`, `sbom.cdx.json` and `CHECKSUMS.sha256` for the support life of its version line plus one year, so any shipped build can be reconstructed and audited.
