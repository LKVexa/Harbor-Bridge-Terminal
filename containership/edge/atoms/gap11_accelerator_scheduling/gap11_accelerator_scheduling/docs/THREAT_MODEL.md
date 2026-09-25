# GAP-11 v4.3.0 — Threat Model (GAP11-P2-44)

**Status:** DRAFT — not reviewed. **Owner:** UNASSIGNED. **Approver:** UNASSIGNED.
**Review cadence (proposed):** every minor release and on any change to `security.py`, `store.py`, `election.py`, `controller.py` scrub paths, or the wire schemas.
**Out-of-cycle triggers:** a STALE_FENCE or REPLAY_DETECTED alert in production; any audit-verify failure; a new accelerator vendor; any scrub finding.

## Scope and non-goals

In scope: the GAP-11 control plane in `gap11_control/` (store, election/fencing, controller, service boundary, adapters) and the audited v4.2.0 allocator it reuses.
Not in scope (owned elsewhere, relied upon): device drivers/firmware, hardware root of trust (GAP-06), capability discovery (GAP-02), power/thermal (GAP-10), telemetry backends (GAP-09), the workload runtime.

## Trust boundaries

| ID | Boundary | Crossing | Control |
|---|---|---|---|
| TB-1 | workload → service | credential + JSON request | `Authenticator` (MAC, aud, exp, skew, nonce), `wire.decode` limits, `Policy` deny-by-default |
| TB-2 | operator → service | operator credential | operator-only scopes (`OPERATOR_ONLY`), audit |
| TB-3 | controller → store | CAS commit | fence token (leader epoch), revision preconditions, checksummed WAL |
| TB-4 | node agent → controller | inventory + quote | `AttestationVerifier` binds stable_id, capability digest, driver/firmware, node |
| TB-5 | controller → scrub backend | privileged reset/zeroize | deadline, bounded retry, independent verify, quarantine on doubt |
| TB-6 | controller → audit ledger | events | redaction, hash chain, HMAC, external head witness |

## Attacker classes

A1 malicious tenant workload · A2 compromised/confused operator tooling · A3 stale or partitioned controller (not malicious, but dangerous) · A4 malicious or faulty node agent / device metadata · A5 network attacker between workload and service · A6 insider with filesystem access to the store/ledger.

## Threats and mitigations (stable IDs)

| ID | Threat | Mitigation | Test evidence |
|---|---|---|---|
| THR-01 | Cross-tenant data remanence in HBM/VRAM | security_tenant epoch; scrub required; failed/partial/timeout scrub → QUARANTINED | `test_hardware.ScrubTests`, `test_scheduler.AdversarialTests` |
| THR-02 | Split-brain double allocation | store-side fencing by leader epoch | `test_state.FencingElectionTests`, `test_verification.SplitBrainTests` |
| THR-03 | Replay of allocate/release | tenant-scoped idempotency keys + nonce window | `test_state.IdempotencyTests`, `test_security.AuthnTests` |
| THR-04 | Tenant spoofing in request body | tenant taken from principal; body mismatch refused | `test_security.AuthzTests` |
| THR-05 | Cross-tenant release / existence oracle | release of another tenant's lease returns LEASE_NOT_FOUND / POLICY_DENIED | `test_security.AuthzTests` |
| THR-06 | Privilege escalation to scrub/quarantine | operator-only scopes | `test_security.AuthzTests` |
| THR-07 | Inflated device capability | attestation capability digest | `test_security.AttestationTests` |
| THR-08 | Audit tampering / truncation | chain + HMAC + external witness head | `test_observability.AuditLedgerTests` |
| THR-09 | Parser DoS / malformed input | size, depth, duplicate-key, NaN refusal before logic; fuzzing | `test_wire.SchemaTests` |
| THR-10 | Resource exhaustion | bounded in-flight, bounded queue, quotas with deny default | `test_wire.TransportTests`, `test_scheduler` |
| THR-11 | Secret leakage via logs/metrics | redaction, label budget, secret refs only | `test_observability`, `test_security` |
| THR-12 | Wall-clock manipulation | monotonic TTLs; wall time provenance only | `test_state.FencingElectionTests` |
| THR-13 | Returning/replaced device trusted | stable identity; reappearance → QUARANTINED | `test_state.LifecycleAndHotplugTests`, `test_hardware.InventoryTests` |
| THR-14 | Insider edits WAL | per-record SHA-256 + refuse-to-open | `test_state.StoreTests` |

## Residual risks (not mitigated in this build)

- **RR-01** Plaintext loopback HTTP; no mTLS (BLK-PKI). Bearer-style HMAC credentials are replayable only inside the nonce window of a single controller instance; the nonce cache is in memory.
- **RR-02** SHA-256 WAL checksums detect accidental corruption, not a filesystem insider who recomputes them. The WAL is not MAC'd (proposed: key the WAL with the audit key; EXC-004).
- **RR-03** Side channels between partitions of one physical device (MIG/SR-IOV) are **assumed** mitigated by same-tenant co-residency only; cross-tenant partition sharing is refused by design.
- **RR-04** Scrub completeness is only as good as the vendor's zeroize primitive; simulated here (BLK-HW).
- **RR-05** Single-store design: the store is a single point of failure until a replicated backend exists (BLK-ENV).
