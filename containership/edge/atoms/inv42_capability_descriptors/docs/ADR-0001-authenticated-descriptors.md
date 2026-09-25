# ADR-0001 — Authenticate serialized capability descriptors

**Status:** Accepted in 4.2.0  
**Date:** 2026-09-22

## Context

Version 1 bound a descriptor to a table id and type but did not cryptographically authenticate those fields. Because `Descriptor` objects could be constructed by callers, knowledge or guessing of a live `(table, number, type)` tuple was sufficient to manufacture an object accepted by the issuing table.

## Decision

Version 2 uses a random 256-bit per-table key and HMAC-SHA-256 over canonical JSON containing `(PK_DESCRIPTOR/2, table_id, number, resource_type)`. Wire parsing is strict, unknown fields are rejected, v1 is not accepted, and all resolution paths authenticate before returning a resource. Table identities are issuer-generated. Tables are process-local, fork use is rejected, and explicit destruction clears live entries and best-effort zeroizes the key.

## Consequences

- A guessed number/table/type is no longer authority.
- Altering any authenticated wire field invalidates the descriptor.
- v1 wire compatibility is intentionally broken and requires re-issuance.
- Theft of a complete live v2 bearer descriptor still conveys authority; confidentiality and peer authentication remain transport responsibilities.
- The Python implementation cannot promise hardware-backed key isolation or perfect memory zeroization.
