# Key and secret inventory (MC-14.01/14.02)

| Key class | Purpose | Algorithm | Backend in v5.0.0 | Rotation | Owner |
|---|---|---|---|---|---|
| `audit/vN` | sign audit ledger events | Ed25519 | SoftwareKeyStore (memory) | `rotate()`; publish new pubkey first | UNASSIGNED |
| `wl/vN` | sign workload identity tokens | Ed25519 | SoftwareKeyStore | ≤ verdict TTL overlap | UNASSIGNED |
| policy approver keys | sign measurement policy bundles | Ed25519 | held by approvers (outside service) | approver-set change = new pinned set | UNASSIGNED |
| service TLS key | mTLS server identity | ECDSA P-256 | PEM file (`transport.py`) | not automated | UNASSIGNED |
| node AK | quote signing | ECDSA/RSA (TPM-resident on real HW) | node | `Enrollment.rotate` (old-AK signed) | node owner |
| trust anchors | EK chain roots | X.509 | operator-supplied | overlap rotation (runbook) | UNASSIGNED |
| state encryption key | at-rest encryption of store | — | **not implemented** | — | — |
