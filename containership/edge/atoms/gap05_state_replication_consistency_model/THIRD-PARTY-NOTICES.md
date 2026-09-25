# Third-party notices - GAP-05 v4.3.0

| Component | Use | License | Pulled code? |
|---|---|---|---|
| `cryptography` (PyCA) 46.0.7 | Ed25519 signatures, AES-256-GCM | Apache-2.0 OR BSD-3-Clause | No - runtime dependency, not vendored |

No code was copied into this package from any other repository.  Design patterns were
informed by public, well-known techniques (SPIFFE workload identity, hash-chained audit
logs, version vectors, Merkle-style anti-entropy, state-based CRDTs); no third-party
source text is reproduced.

The package's own license is **not declared** in the supplied archive; `pyproject.toml`
records it as UNSPECIFIED so the owner must decide it before distribution.
