# Dependency and vulnerability management (#39)

| dependency | why | pin | licence | advisory feed |
|---|---|---|---|---|
| `cryptography` (PyCA) + bundled OpenSSL | all signature primitives, X.509 path validation | `>=45,<48` in `requirements.txt`; the exact resolved version is recorded in `SBOM.cdx.json` | Apache-2.0 OR BSD-3-Clause | GHSA `pyca/cryptography`, OpenSSL security advisories |
| `cffi`, `pycparser` (transitive) | cryptography bindings | resolved in SBOM | MIT / BSD-3-Clause | GHSA |
| Python stdlib ≥ 3.10 | everything else | runtime image | PSF | python.org security |
| `hypothesis` (test-only, optional) | property tests | CI only | MPL-2.0 (test tooling, not shipped) | — |

The runtime depends on exactly one third-party package, `cryptography`. Provider SDKs (boto3, azure-keyvault-keys,
google-cloud-kms, hvac, python-pkcs11) are **not** imported by GAP-07. Callers inject clients that the estate
image supplies and pins.

**Remediation SLAs** (from advisory publication to a released fix): critical or known-exploited, 72 h; high, 7 d;
medium, 30 d; low, next release. Crypto-library advisories are always triaged the same day, because they can
invalidate trust fleet-wide.

**Emergency path:** bump the pin → `tools/release.py evidence --bench` (every gate must pass) → sign (`release.py sign`)
→ distribute. There is no path that skips evidence or signing.

**EOL policy:** a Python minor version past upstream EOL, or a `cryptography` major version with no security support,
blocks release unless a signed time-bounded waiver exists (`PK_WAIVER/1` style record, owner + expiry +
compensating control).

**Integrity:** production builds install with `pip install --require-hashes -r requirements.lock`, where the lockfile is
generated in CI from `requirements.txt` with `pip-compile --generate-hashes`, from a private index or allowlist. CI runs
`pip-audit --strict`, and a stale feed fails the job.
