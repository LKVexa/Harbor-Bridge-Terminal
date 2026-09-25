# Independent security / cryptographic review packet (#37)

**Status: NOT YET PERFORMED.** This pass cannot supply an independent review. It prepares the packet a
reviewer needs. Admission to production remains blocked until reviewer sign-off is recorded below.

## Scope for the reviewer
1. Envelope semantics and domain separation: `canonical.ld_encode`, `signing.signed_message`, all `ld_encode` domains.
2. Algorithm registry, downgrade logic and key-type pinning: `algorithms.py`.
3. KMS boundary: `keys.ResilientCustody` post-sign pin check, error classification and retry safety.
4. Trust semantics: `trust.TrustGeneration._validate_path` (constraints, path length, revocation, deterministic path choice) and `validate_x509` policy.
5. DSSE/in-toto/SLSA handling: `dsse.verify_envelope` (PAE, subject matching, predicate gating).
6. Merkle proof verification: `tlog.verify_inclusion` and `verify_consistency` (RFC 9162).
7. Policy semantics: `policy.evaluate` conflict resolution, the waiver scope, the non-waivable set.
8. Persistence and rollback: `store`, `distribution`, `timesrc` floors.

## Evidence provided
Tests (normal and `-O`), fuzz and property suites, interop vectors pinned to RFC 8032 and RFC 6962 values,
THREAT_MODEL.md, ADRs, benchmark output, and the release evidence bundle.

## Sign-off record
| reviewer | organisation | scope items | date | findings | disposition |
|---|---|---|---|---|---|
| _unassigned_ | | | | | |
