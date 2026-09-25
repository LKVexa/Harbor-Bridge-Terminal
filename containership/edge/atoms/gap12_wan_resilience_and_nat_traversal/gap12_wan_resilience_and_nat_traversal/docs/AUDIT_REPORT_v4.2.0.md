# GAP-12 v4.2.0 Audit Report

**Audit date:** 2026-09-22  
**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Scope:** source parsing, correctness, failure semantics, security hardening, checklist/evidence alignment, tests, documentation, and missing-component analysis.

## Executive result

The uploaded package was a useful reference state machine, but it overstated its production completeness. The audit found concrete state-machine defects and evidence-mapping problems in addition to major production networking capabilities that are not present in the ZIP. The code has been hardened to make its implemented behavior internally consistent and testable without `pk_core`; production completeness is now explicitly qualified.

## Fixed findings

| Severity | Finding | Resolution |
|---|---|---|
| High | First failure used a 2-second delay even though the declared base is 1 second. | Corrected exponent to `failures - 1`. |
| High | Checklist requires retry jitter; implementation had deterministic synchronized retries. | Added bounded per-path equal jitter. |
| High | Freshness check accepted a future `last_success` because negative age was `<= freshness`. | Requires `0 <= age <= freshness`. |
| High | Every non-healthy path was reported as `partitioned`, including a brand-new untested path. | Added explicit partition state and `unknown`/`stale` statuses. |
| High | Probe backend exception aborted fallback, so a broken direct adapter could prevent relay recovery. | Sanitized `Exception` handling records an `error` attempt and continues escalation. |
| High | Custom evidence was written into semantically unrelated checklist indexes (for example resilience evidence in implementation/configuration slots). | Re-aligned custom evidence to C047/C048 and C052/C053/C055/C056. |
| Medium | Contract claimed traversal attempt outcomes, but history stored only strategy/time. | Added outcome plus sanitized `error_type`. |
| Medium | Contract claimed relay cost accounting, but no relay byte counter existed. | Added `record_relay_bytes()` and state output. |
| Medium | Retry state was difficult to operate because `retry_at`/remaining delay were not exposed. | Added `retry_at` and `retry_in`. |
| Medium | Probe exception text could be copied into diagnostics if future code logged it directly. | Records exception class only; message is discarded by this layer. |
| Medium | Peer and time inputs were essentially unchecked. | Added peer/control-character and finite non-negative time validation. |
| Medium | README asserted `MASTER.md` was present although it was absent from the ZIP. | Removed the false claim and documented actual package contents. |
| Low | Path logic could not be tested without importing `pk_core`. | Extracted dependency-free `path.py`. |

## Validation performed

1. Parsed and compiled all Python sources with `compileall` — **PASS**.
2. Ran `tests/test_path.py` — **10 tests PASS**.
3. Checked initial/healthy/stale/backing-off/partitioned state transitions.
4. Checked direct success and last-resort relay ordering.
5. Checked probe exception fall-through.
6. Checked first retry delay and exponential ceiling.
7. Checked retry-window refusal without invoking the prober.
8. Checked future/stale timestamps.
9. Checked bounded attempt history.
10. Checked relay accounting and invalid inputs.
11. Ran `tests/test_component.py` — tests were **SKIPPED** because `pk_core` is not included in the uploaded ZIP or audit environment.

## Important limitations

- No real sockets or network namespaces are used by this package.
- No STUN/TURN/ICE implementation is present.
- No relay service is provisioned or contacted.
- No identity/attestation or end-to-end encryption implementation is bundled.
- No concurrency, daemon lifecycle, persistent state, metrics exporter, network emulation, or fleet integration is bundled.
- `connect()` relies on the supplied `prober` to enforce per-attempt timeouts/cancellation; a blocking prober can still block the caller.
- In-memory `Path` objects are not thread-safe and are not crash-persistent.

These are not hidden by the version bump; they are enumerated in `MISSING_COMPONENTS.md`.

## Version-bump rationale

The bump from **4.1.0 -> 4.2.0** is a minor release because the package gains observable path-state fields, retry jitter, relay accounting, a standalone module, and new test/documentation artifacts while preserving the primary `connect()` and `state()` usage model.
