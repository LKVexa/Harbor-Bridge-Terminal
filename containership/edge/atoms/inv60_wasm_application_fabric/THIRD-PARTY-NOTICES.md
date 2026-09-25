# Third-party notices

| Item | Origin | Licence | Notes |
|---|---|---|---|
| `fabric/ed25519.py` | written for this release from RFC 8032 §5.1 (algorithm specification, test vectors) | owner's (pending) | no code copied; RFC text is the algorithm reference |
| `pk_core/` (sibling folder) | owner's estate — `PK_Master_Applied_All_Batches/UC270/pk_core` | owner's material | vendored unchanged to make the 100-item conformance suite runnable (M76) |
| `MASTER.md` | owner's series — `UC32/pk_components/inv60_wasm_application_fabric/MASTER.md` | owner's material | restored verbatim (sha256 in docs/MASTER_INDEX.md) |
| in-toto Statement v1 / SLSA provenance v1 field names | public specifications | spec usage only | no code copied |
| W3C Trace Context `traceparent` format | public specification | spec usage only | |

Runtime third-party dependencies: **none** (stdlib only). Optional test cross-check: `cryptography` (Apache-2.0 OR BSD-3-Clause) if installed. Node.js is an external tool, not redistributed.
