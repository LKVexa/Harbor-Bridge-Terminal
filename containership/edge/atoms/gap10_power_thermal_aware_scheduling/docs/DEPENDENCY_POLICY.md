# GAP-10 Dependency, Pinning and Vulnerability Policy (component 35)

- **Runtime dependencies:** CPython standard library only (see `SBOM.cdx.json`). `pk_core` is optional and only imported by `component.py` / `contract.py` for estate conformance.
- **Pinning:** the supported interpreter range is `>=3.10,<3.14`; CI must pin an exact patch version and record it in the release provenance (`builder.python`).
- **Enforcement:** `tests/test_prod_p3.py::test_c35_sbom_lists_no_undeclared_imports` fails the build if any module imports a non-stdlib package not declared in the SBOM.
- **Adding a dependency:** requires an ADR, SBOM entry with exact version and hash, licence review, and security-owner approval.
- **CVE response SLA (CPython or any future dependency):** Critical: 72 h to patched release or documented mitigation; High: 7 days; Medium: 30 days; Low: next scheduled release.
- **End of life:** a Python minor version is dropped no later than its upstream EOL; the compatibility matrix is updated in the same release.
- **Scanning:** each release runs a vulnerability scan against the SBOM (tooling is deployment-specific; result attached to release evidence).
