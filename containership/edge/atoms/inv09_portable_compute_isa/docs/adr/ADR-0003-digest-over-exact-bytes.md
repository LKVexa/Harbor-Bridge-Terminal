# ADR-0003: Module identity is SHA-256 over the exact bytes
Status: accepted. Alternatives: digest excluding custom sections (lets a name/debug section change
without re-validation). Rejected: custom sections could then be swapped under an attestation and
toolchains that read them would see unattested content. Consequence: any byte change → new identity.
