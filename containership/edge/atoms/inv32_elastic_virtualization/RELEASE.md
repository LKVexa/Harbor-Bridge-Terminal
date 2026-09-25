# Release process (INV-32)

1. Bump `inv32_elastic_virtualization/VERSION` (single source; `__init__.__version__` must match — import guard).
2. Update `CHANGELOG.md` with a compatibility statement.
3. Clean build: `python -m pip wheel --no-deps -w dist .` and `python setup-free sdist` via `pip` / `build` on the runner.
4. Fresh venv install of the wheel, then run the full suite against the installed package.
5. `release digests`, `release sbom`, `release sast`, `release rtm-check`, `bench run` + `bench gate`.
6. `release evidence --tests … --bench … --artifact dist/*.whl` with `INV32_RELEASE_KEY` (reference HMAC;
   production requires SLSA/Sigstore provenance — BLOCKED).
7. `release gate --manifest …` must return PASS; promotion requires a protected approval recorded in the manifest.
