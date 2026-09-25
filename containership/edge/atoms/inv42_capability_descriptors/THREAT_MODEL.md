# Threat model — INV-42 4.3.0 (MC-029 source)

Each threat below is traced to its tests. Adversaries considered: malicious tenant or workload, compromised peer process, hostile network, a malicious log reader, a supply-chain attacker, and an insider with host access.

| # | Threat | Mitigation | Tests |
|---|---|---|---|
| T1 | Number guessing / forgery | HMAC-SHA-256 per-table key | test_guessing_or_forgery_is_not_authority, FuzzTest |
| T2 | Confused deputy (foreign table) | table id bound and checked | test_tampering…, test_process_transfer_confers_no_authority |
| T3 | Replay after close | permanent close; valid-tag-but-absent means closed | test_close_is_permanent… |
| T4 | Type confusion across ABI | type is authenticated; `expect=` enforced | test_expected_type…, AdjacentLayerTest |
| T5 | Hostile Mapping/str/int subclasses | exact `type()` checks in `from_wire` | test_hostile_subclasses_rejected |
| T6 | Log/terminal injection via error text | attacker text truncated, `redact()` escapes control chars | test_error_messages_are_log_safe, test_redaction… |
| T7 | Timing side channel on tag compare | `hmac.compare_digest` | test_constant_time_comparisons_used |
| T8 | Key compromise | contained to one table; `destroy()` revokes; no cross-table effect | test_key_compromise_contained_by_destroy |
| T9 | Resource exhaustion | live and session ceilings; cheap rejections (p99 ≤ 60 µs) | test_sustained_exhaustion_bounded, bench overload |
| T10 | Fork clone | pid check | test_fork_clone_is_rejected |
| T11 | Races (close/resolve/destroy) | single RLock; atomic ops | ConcurrencyTest |
| T12 | Bearer theft in transit | TLS 1.3 mTLS profile | TransportTest |
| T13 | Audit tampering | hash chain + MAC + anchored head | AuditTest |
| T14 | Supply chain | SBOM, provenance, signed manifest, reproducible archive | tools/release.py verify |
| T15 | Delegation abuse | default deny, no key sharing, idempotent txn, atomic move | DelegationTest |

## Least privilege

The runtime needs no file, network, device, or environment access. The one exception is reading the `INV42_EMERGENCY_DISABLE` environment variable. Audit and transport receive their paths and sockets explicitly from the caller.

## Ambient authority

Nothing is discovered implicitly. Authority comes only from possessing an authenticated descriptor. The `resource` object is supplied by the caller (INV-41).

## Failure enumeration

- **Component:** typed errors.
- **Process crash:** authority is revoked (FaultInjectionTest).
- **Fork:** rejected.
- **Node or site loss:** equivalent to a crash.
- **Network:** transport fails closed.
- **Provider/KMS:** `key_unavailable`.
- **Control plane:** not required at runtime.
- **Dependency (`pk_core`):** certification-only, so a failure blocks release but not runtime.

## Residual risks

- A stolen, complete live descriptor is bearer authority until it's closed or the table is destroyed.
- CPython can't guarantee zeroization of key copies (W-007).
- The hash-only audit chain can be re-forged by anyone with write access unless a MAC key is used (tested).
