# PLN-05 release, versioning and lifecycle policy

- **Versioning:** SemVer on the package. MAJOR = a wire schema major (`/2`) or an outcome change for identical input; MINOR = new capability, new optional field, new error code; PATCH = fixes. One canonical version: `VERSION` (checked against `__init__`, `pyproject.toml`, `security/approved-versions.json`, README, CHANGELOG by `tools/check_repo.py`).
- **Changelog:** every release has a `CHANGELOG.md` section listing defects fixed, behaviour changes and evidence summary; claims must match machine evidence.
- **Channels:** dev → staging → canary → production rings (ring 1 = 1 site, ring 2 = 10 % of sites, ring 3 = all). Promotion only with a PASS exit gate for the release tier.
- **Canary:** 24 h on one site; abort automatically if any of: readiness loss > 1 min, any `E_INTERNAL`, any `E_FENCED`, decision p99 > 2 × baseline, SLO burn alert. Manual abort by any on-call.
- **Rollback:** triggers as canary abort; procedure: redeploy previous wheel (state format is backward-readable one minor back), keep `state_dir`; verify `status()` version and checksum. Rehearsed by `tools/ci.py` (install previous wheel → current → previous in a clean venv).
- **Compatibility window:** schemas `/1` supported for ≥ 2 minor releases after `/2` ships; state readable one major back; config one major back.
- **Supported versions:** `compatibility/supported-versions.json`.
- **Patch policy:** functional defects fixed in the current minor; security fixes back-ported to the previous minor.
- **Vulnerability SLA:** critical 7 days, high 30 days, medium 90 days, low next release (from triage).
- **EOL:** 6 months notice in CHANGELOG and `compatibility/supported-versions.json`; unsupported versions are removed from `security/approved-versions.json`, so `verify_artifact` refuses them.
- **Waivers:** `governance/waivers.json`; the gate blocks on any expired waiver.
- **Offline / edge installs:** the wheel has no runtime dependencies; mirror the wheel and `SHA256SUMS` only.
