# Security model — INV-42 Capability descriptors

## Trust boundary

A serialized descriptor is attacker-controlled input and is a bearer capability. A descriptor number, type, or table identifier by itself conveys no authority. `PK_DESCRIPTOR/2` authenticates the tuple `(schema, table, number, type)` with HMAC-SHA-256 under a random 256-bit per-table key that never appears on the wire.

The authentication tag **is part of the bearer capability**. Do not log, index, persist, expose in crash reports, or place complete descriptor payloads in telemetry. `Descriptor.__repr__` intentionally redacts the tag and `DescriptorTable.status()` omits table identity and key material.

## Threats handled in this repository

- descriptor-number guessing and same-table forgery;
- foreign-table descriptor confusion;
- type substitution/tampering;
- stale descriptor replay after close;
- descriptor-number reuse within a session;
- resource exhaustion through unbounded live descriptors or allocation churn;
- concurrent allocation races;
- fork-cloned tables issuing divergent authority under one table identity;
- accidental serialization of the table secret;
- post-lifecycle use after explicit table destruction.

## Security invariants

1. A descriptor resolves only in the table that minted its authentication tag.
2. Every authenticated field is bound into the HMAC.
3. Closed numbers are never reused within a table session.
4. A valid descriptor that is no longer live is treated as permanently closed.
5. Descriptor tables are process-local and reject use after fork.
6. Live and lifetime allocation are bounded.
7. Destruction clears live entries and best-effort overwrites the Python bytearray containing the table key.

## Limitations and external responsibilities

- HMAC provides authenticity and integrity, **not confidentiality**. Descriptors that cross a process boundary MUST use `transport.py` (`PK_DESCRIPTOR_TRANSPORT/1`: TLS 1.3 with mutual authentication and an optional pinned peer identity). The deployment PKI is still an open item (W-005).
- Python cannot guarantee complete cryptographic zeroization because interpreter/runtime copies may exist. `destroy()` is best-effort defense in depth, not a protected-memory facility.
- Theft of an entire live `PK_DESCRIPTOR/2` payload confers the represented bearer authority until close or table destruction. This repository does not implement leases or remote revocation. Delegation is supported only through policy-controlled re-issuance (`delegation.py`).
- 4.3.0 adds a tamper-evident audit chain (`audit.py`), supply-chain tooling (`tools/release.py`), fail-closed handling when the key provider is unavailable, and an emergency disable. The full threat-to-test mapping is in `THREAT_MODEL.md`.

## Vulnerability handling

See `VULNERABILITY_POLICY.md` and `INCIDENT_RUNBOOK.md`.

Do not certify this package for production from the standalone unit tests alone. The release gate must run with the suite's `pk_core` dependency available and must include the missing security/integration evidence listed in `POST_AUDIT.md`.
