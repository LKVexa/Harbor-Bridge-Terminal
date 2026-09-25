# INV-54 Repository Audit Report

## Audit identity

- **Component:** INV-54 - Broker implementations
- **Input version:** 4.1.0
- **Updated version:** 4.2.0
- **Audit date:** 2026-09-22
- **Scope:** parse, correctness review, hardening, version consistency, dependency-free behavioural verification, repository-evidence review, and second-pass missing-component audit.

## Executive result

Version 4.2.0 fixes the concrete defects that can be corrected inside this small reference repository without pretending to supply production infrastructure that is not present. The in-memory fan-out and partitioned-log reference implementations now have strict input validation, constructor-state protection, per-operation locking, failure-atomic isolated fan-out delivery, and standalone tests that do not require `pk_core`.

The repository is **not a complete production broker implementation estate**. It contains reference brokers and a `pk_core` contract adapter, but it does not ship Kafka, RabbitMQ, or AWS SQS adapters; durable/replicated state; production configuration/security/telemetry; full integration, performance, security, and disaster testing; or release/governance evidence. Those omissions are enumerated in `MISSING_COMPONENTS.md`.

## Findings fixed in 4.2.0

1. **Fan-out aliasing:** 4.1.0 appended the exact same mutable message object to every subscriber. A subscriber could mutate another subscriber's apparent delivery. 4.2.0 deep-copies per subscriber.
2. **Partial fan-out on copy failure:** deliveries are now prepared before any inbox mutation; copy failure produces no partial fan-out.
3. **Internal-state constructor injection:** `subscribers`, `logs`, and `offsets` are now non-init dataclass fields, preventing callers from constructing a broker with spoofed internal state.
4. **Boolean-as-index ambiguity:** Python treats `bool` as `int`; 4.2.0 explicitly rejects booleans for partition counts, partition indexes, limits, and offsets.
5. **Weak numeric validation:** non-integer limits/offsets/partition indexes are rejected deterministically rather than failing later with incidental slice/comparison errors.
6. **Identity/key boundary validation:** subscriber names, consumer names, and partition keys are validated explicitly.
7. **Shared-state race exposure:** fan-out subscribe/unsubscribe/publish and log append/poll/seek/offset reads now use re-entrant locks within one process.
8. **Eager external dependency:** package import no longer eagerly imports `pk_core`; the dependency-free broker primitives can be imported and tested alone.
9. **Missing primitive observability helpers:** `committed_offset()` and `end_offset()` make reference state inspection explicit instead of requiring callers to reach into dictionaries/lists.
10. **Missing unsubscribe primitive:** the reference fan-out broker now supports explicit subscriber removal.
11. **Documentation drift:** README previously stated that `MASTER.md` was shipped, but the archive contains no such file. The README now states the shipped audit source accurately.
12. **Insufficient standalone tests:** added tests for alias isolation, atomic copy failure, constructor injection, type/range validation, replay/offset isolation, and concurrent append integrity.

## Verification performed

- `python -m compileall`: **PASS**
- AST parse of Python sources: **PASS**
- `python -m unittest discover -s tests -p 'test_*.py' -v`: **PASS** for all runnable tests
- Dependency-free broker tests: **10 passed**
- Version consistency test: **1 passed**
- `pk_core` conformance tests: **2 skipped** because `pk_core` is not present/importable in the supplied archive or audit environment

The skip is a verification limitation, not a pass. A production release should rerun the `pk_core` conformance/gate commands in the integrated estate and retain their machine-readable evidence.

## Version-bump rationale

The bump from **4.1.0 to 4.2.0** is a minor-version increment because the package gains new public helper methods (`unsubscribe`, `committed_offset`, `end_offset`) and exports the broker primitives directly, while retaining the existing reference-broker behaviour and component integration path.

## Post-update architecture assessment

The repository now cleanly separates two concerns:

- `brokers.py`: dependency-free in-memory reference semantics.
- `component.py` / `contract.py`: integration with the external `pk_core` conformance framework.

That separation makes local correctness independently testable. It does **not** turn the in-memory references into production physical messaging infrastructure. Production provider implementations and the surrounding operational/security estate remain missing and are tracked separately.

## Second-pass conclusion

No additional local syntax/runtime defects were found by the dependency-free validation pass after the 4.2.0 changes. The remaining findings are primarily **missing production components, policies, provider adapters, evidence, and test systems**, not small code defects that can be responsibly invented inside this archive.

See `MISSING_COMPONENTS.md` for the complete second-pass gap inventory.

---

## v4.3.0 — missing-component overhaul (2026-09-22)

Governing input: `docs/checklist/INV54_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (100 components: 40 P0, 54 P1, 6 P2).

**Result (computed by `tools/gen_evidence.py`):** 105 tests (103 pass, 2 skip: the `pk_core` conformance tests), also green under `python -O`, and in a clean venv with no extras (then 3 skips, adding the encryption test).
Components: 48 LOCAL_VERIFIED, 30 PARTIAL, 18 DOCUMENTED_UNAPPROVED, 4 UNVERIFIED_EXTERNAL, 0 FAIL.
P0: 21 LOCAL_VERIFIED, 17 PARTIAL, 1 documented, 1 external. **Exit gate: NO_GO.** No component is PASS, because none has an independent review record.

Defects this pass found in its own work (via tests or the evidence generator) and fixed:
1. Name grammar used `re.match` + `$`: `"orders\n"` was accepted as a topic. All grammars now use `fullmatch` (found by `test_c44`).
2. `_size()` serialised with `default=str`, so non-JSON payloads were silently accepted (found by `test_c44`).
3. `config.validate` raised `AttributeError` on a non-object section. The seeded property test found it; the validator now returns a problem instead.
4. The RabbitMQ fake redelivered unacked messages inside one fetch, which caused double delivery and a false conformance failure. The fake was corrected to broker semantics, and conformance now drives redelivery per provider (nack / visibility timeout).
5. The SQS ack-redelivery conformance check assumed immediate redelivery. It now takes a provider clock `advance` hook.
6. The evidence generator's first run flagged a missing artifact for `CODEOWNERS` and `config.HARD_LIMITS` (resolver bug) and 5 components claimed without a mapped test. The resolver was fixed and the tests were written; components were not upgraded by hand.
7. In a clean venv without `cryptography`, the encryption test errored instead of skipping. It is now an explicit skip, plus a test that encryption without the library fails closed.

Measured finding (component 66): per-subscriber `deepcopy` shares immutable leaves. A 64 KB string payload therefore costs no more than a small dict for 8-way fan-out. Isolation still holds because strings are immutable.

What cannot be closed from inside this archive: real Kafka, RabbitMQ and SQS certification; `pk_core`; INV-52, INV-53, INV-49 and INV-37 integration; edge power and thermal data; soak and fleet runs; OS sandbox evidence; a backup owner and on-call; a license; signing keys; independent review.
