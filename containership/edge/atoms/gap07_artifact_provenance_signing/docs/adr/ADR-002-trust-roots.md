# ADR-002: Trust roots and identity
Status: accepted
Decision: an offline root (Ed25519) → a name-constrained intermediate per tenant → `PK_CERT/1` leaves whose subject is a SPIFFE-style URI. X.509 code-signing chains are accepted through `validate_x509` (EKU codeSigning, one URI SAN). Trust is pinned per namespace generation.
Consequences: identity is never a display name. Rotating anchors means adding the new anchor, overlapping, then running `retire_anchor` in a delta.
