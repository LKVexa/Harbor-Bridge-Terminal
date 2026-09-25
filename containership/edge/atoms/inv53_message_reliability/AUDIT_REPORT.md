# INV-53 Message Reliability - Audit and Hardening Report

**Input version:** 4.1.0  
**Updated version:** 5.0.0  
**Audit date:** 2026-09-22

## Executive result

The repository was parsed, statically validated, hardened, version-bumped, and re-audited. The original reference queue implemented basic visibility-timeout redelivery and DLQ behavior, but it contained a critical settlement weakness: an ACK was identified only by message ID. After a visibility timeout and redelivery, a stale consumer could therefore acknowledge the newer lease. The original mutable-message references, unprotected shared state, duplicate-ID state collisions, unbounded dedupe set, weak local test coverage, and inaccurate README artifact claim also reduced reliability and auditability.

Version 5.0.0 replaces message-ID-only settlement with lease fencing tokens and explicit ACK time, isolates broker-owned state from caller mutation, adds thread-safe transitions and fail-closed capacity bounds, adds NACK and lease-extension semantics, makes DLQ records explicit, hardens dedupe behavior, and adds framework-independent executable tests.

## Defects fixed

1. **Stale ACK vulnerability:** each delivery now receives an opaque lease token; ACK must match the currently active token.
2. **Late ACK vulnerability:** `ack(..., now=...)` processes visibility expiration before settlement, so an expired delivery cannot settle merely because no receive call happened first.
3. **Mutable aliasing:** accepted and delivered messages are deep-copied; publisher/consumer mutation cannot alter the broker-owned redelivery record.
4. **Duplicate active IDs:** a second active logical message with the same ID is rejected instead of corrupting attempt/in-flight state.
5. **Thread safety:** queue and dedupe state transitions are protected with re-entrant locks.
6. **Unbounded reference dedupe:** the reference consumer is hard-bounded and fails closed before admitting an effect it cannot track.
7. **Cross-scope dedupe collision:** dedupe keys now include an explicit scope in addition to message ID.
8. **O(n) ready-queue head removal:** replaced list `pop(0)` with `deque.popleft()`.
9. **Incomplete failure disposition:** NACK supports explicit requeue or terminal DLQ disposition with a reason.
10. **No lease heartbeat operation:** `extend_visibility()` now refreshes only the currently valid lease.
11. **Deferred poison-message parking:** visibility expiration now dead-letters immediately when the attempt cap is exhausted.
12. **Weak DLQ record:** dead letters now preserve message copy, attempt count, reason, and last lease token.
13. **Capacity transition loss risk:** target capacity is checked before removing the source state, preserving the in-flight record on refusal.
14. **Weak input validation:** numeric settings/time must be finite, counts must be valid integers, and message IDs must be non-empty bounded strings.
15. **Mutable public internals:** core state is now private and exposed through defensive snapshots/count properties.
16. **No local executable coverage without `pk_core`:** a standalone unit suite now tests reliability primitives independently.
17. **Framework import coupling:** package primitives now import without `pk_core`; component/contract bindings load lazily.
18. **Documentation inaccuracy:** README no longer claims a bundled `MASTER.md` file that does not exist.
19. **Version semantics:** major bump to 5.0.0 records the intentionally breaking secure-ACK contract.

## Validation performed

- Python 3.13 byte-compilation of the updated repository.
- Standalone `unittest` execution for the reliability state machine.
- Optimizer-mode execution (`python -O`) of standalone tests.
- Source scan for stale 4.1.0 runtime version references and optimizer-sensitive assertions in production code.
- Archive structure and duplicate-path validation before packaging.
- Re-audit against the bundled 100-item checklist and repository delivery artifacts.

The `pk_core` conformance suite is retained but cannot be counted as executed in this environment because `pk_core` is neither bundled in the archive nor installed. Its tests correctly skip under that condition. This limitation is recorded as an unresolved verification dependency in `MISSING_COMPONENTS.md`.

## Remaining gaps

See `MISSING_COMPONENTS.md` for the complete post-hardening list. The remaining gaps are primarily production infrastructure and evidence: durable/distributed broker adapters, typed wire schemas, authentication/authorization, configuration and secrets, full security controls, integration/fault/scale testing, production telemetry, operational runbooks, release governance, packaging/CI, and machine-readable acceptance evidence.
