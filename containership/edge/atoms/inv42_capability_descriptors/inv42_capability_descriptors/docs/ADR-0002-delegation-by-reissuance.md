# ADR-0002: Descriptor delegation by re-issuance (MC-042)

**Status:** Accepted, 4.3.0

**Context:** The contract lists "descriptor transfer between tables under policy" as optional. Sharing issuer keys would make any table able to mint for any other table, which would break R1.

**Decision:** Delegation re-issues the descriptor. The destination table mints a fresh descriptor under its own key, and a `PK_DESCRIPTOR_DELEGATION/1` record links the source and destination through non-secret fingerprints.

- There are two modes. In `move`, the source is closed atomically and closed only after the destination has issued. In `share`, both descriptors stay valid.
- The default policy is deny-all. A policy that throws an exception counts as a denial.
- The type must be preserved, so no amplification is possible. The descriptor model has no rights beyond type.
- `txn_id` makes the operation idempotent. Reusing a `txn_id` with different parameters is refused.
- Every decision, including denials, is sent to the audit sink.
- Delegation across processes or hosts sends the new descriptor over `PK_DESCRIPTOR_TRANSPORT/1`.

**Consequences:**

- Revoking the source does not cascade to shared delegates. Holders must close each one.
- Delegation versioning is separate from `PK_DESCRIPTOR/2`.
