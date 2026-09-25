# Third-party notices

No third-party source code is bundled in this archive. No parts were pulled from the GitHub Junkyard yard for v4.3.0.

| Dependency | Use | Bundled? | Licence (upstream declared) | Obligation if distributed |
|---|---|---|---|---|
| CPython stdlib | runtime | no | PSF-2.0 | none for use |
| jsonschema | optional test | no | MIT | include notice if vendored |
| cryptography | optional Ed25519 | no | Apache-2.0 OR BSD-3-Clause | include notice if vendored |
| pk_core | optional estate conformance | no | unknown (not supplied) | **review before distribution** |

Specifications referenced (not copied): OAM (`core.oam.dev/v1beta1`), WebAssembly Component Model WIT,
W3C Trace Context, JSON Schema 2020-12.

Upstream licence labels above are recorded from the projects' own declarations and must be re-verified by the
release licence scan (`tools/gate.py --tier release`) before a distribution.
