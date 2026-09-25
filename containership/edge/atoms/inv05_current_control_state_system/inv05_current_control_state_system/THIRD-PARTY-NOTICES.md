# Third-party notices

No third-party source code is copied into this package. The following runtime dependencies are
installed separately (see `requirements.lock` and `evidence/sbom.cdx.json`):

| Component | Version | Licence | Use |
|---|---|---|---|
| cryptography | 46.0.7 | Apache-2.0 OR BSD-3-Clause (dual) | AES-256-GCM at-rest encryption; test PKI generation |
| cffi | 2.0.0 | MIT | transitive dependency of cryptography |
| pycparser | 3.0 | BSD-3-Clause | transitive dependency of cffi |
| Python | 3.10–3.13 | PSF-2.0 | runtime |

Redistributors must include the licence texts shipped in each dependency's distribution
(`*.dist-info/licenses/`). `pk_core` is not bundled; its licence must be recorded in
`deploy/pk_core_pin.json` when pinned (MC-001-07).
