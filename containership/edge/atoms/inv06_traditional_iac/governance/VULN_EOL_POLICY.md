# Vulnerability, Patch and EOL Policy (MC-065)

Status: **Draft.**
- Runtime dependencies: none (stdlib only). Build-only pins: setuptools, wheel (`pyproject.toml`).
- CVE triage: Python runtime, pinned engine and providers are watched; Critical fix ≤ 7 days, High ≤ 30, Medium ≤ 90.
- Emergency fix path: PATCH release, evidence regenerated, canary rollout with shortened stages.
- Supported life: each MINOR supported 12 months after the next MINOR ships; Python versions follow CPython EOL.
- EOL: announce 90 days ahead in CHANGELOG; gate refuses EOL runtimes via `SUPPORT_MATRIX` update.
