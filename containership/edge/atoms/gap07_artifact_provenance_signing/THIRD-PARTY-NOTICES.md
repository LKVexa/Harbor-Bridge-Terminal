# Third-party notices - GAP-07 v6.0.0

No source code was copied into this package from donor repositories (the chop-shop yard office was not
installed, so no yard parts were pulled; see the work order `00-WORK-ORDER.md`). All v6 modules are new code.

Runtime dependency (installed separately, not vendored):

| package | licence | use |
|---|---|---|
| `cryptography` (Python Cryptographic Authority) | Apache-2.0 OR BSD-3-Clause | all signature, key and X.509 primitives |
| `cffi`, `pycparser` (transitive) | MIT / BSD-3-Clause | bindings for `cryptography` |

Published test vectors pinned in the tests: RFC 8032 Ed25519 test 1 (IETF Trust) and the RFC 6962 eight-leaf
Merkle root used by certificate-transparency implementations. These are cited as data only.
