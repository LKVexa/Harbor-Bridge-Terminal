# Changelog — INV-57

## 4.3.0 — 2026-09-23

Remediation pass against `INV57_v4.2.0_MISSING_COMPONENTS_ENGINEERING_CHECKLIST.md` (82 components).
Result: 16 IMPLEMENTED_LOCAL, 38 PARTIAL, 21 BLOCKED, 7 OPEN, 0 CLOSED. Gate verdict NO_GO.

### Defects found in the v4.2.0 baseline and fixed
- **Quadratic replay (performance).** `Worker.activity` re-hashed the whole chain on every step and copied the full event tuple on every step. 1000-event replay took ~3.7 s against the contract's 100 ms p99 SLO. It now takes ~3.7 ms p99 (incremental validation + indexed `event_at`), and a linear-scaling gate test guards it.
- **Malformed payload escaped integrity handling.** A history payload missing `"v"` (or with a wrong-typed value) raised a bare `KeyError`/`TypeError` instead of `HistoryCorruption`. Mutation fuzzing found it. Decoding now type-checks bool/int/str and maps every malformation to `HistoryCorruption`.

### Defects in this pass's own work, caught by its own tests
- Identity validation used `re.match` with `$`, which accepts a trailing newline (`"a\n"`): a log/key injection vector. Now `fullmatch`.
- Installed-wheel tests wrote `__pycache__` that `pip uninstall` leaves behind, so the package still resolved after uninstall. CI now runs installed tests with `-B`.
- The first gate test assumed only the mutated component would lose evidence. In fact every IMPLEMENTED_LOCAL component is demoted when the test report lacks its tests, which is the correct behaviour, so the test was corrected, not the gate.

### Defects found by the independent adversarial review (all fixed, each with a regression test in `tests/test_review_findings.py`)
- R1: `effect_mark` updated by `effect_id` alone, so a valid lease for workflow B could overwrite workflow A's effect record (including across tenants). `effect_prepare` silently ignored an effect-id collision. Both are now scoped to the lease's workflow key and refuse aliasing.
- R2: `HistoryEvent.payload` was a mutable dict reachable through `store.events`, so a recorded result could be rewritten in place and incremental validation would not notice. Payloads are now deep-frozen.
- R3: the gate accepted symlinked evidence (`normpath`, not `realpath`) and counted any caller-chosen HMAC key as a signature, and the manifest did not hash the test report. Fixes: realpath plus symlink refusal, a `TRUST_POLICY.json` key-id requirement (empty, so no key is trusted), a separate RG-06 attestation blocker, and the test report hashed and marked `attested: false`.
- R4: decoder escapes. A list-typed `kind` raised TypeError, and deep nesting raised RecursionError; passing bytes raised UnicodeDecodeError. All now raise `HistoryCorruption`.
- R5: the crash test had no kill points at effect-ledger commits, and the child's 0.5 s lease could flake. Four new effect kill points were added (prepare/mark × before/after commit), and the TTL is now 30 s.

### Added
- Persistent fenced SQLite backend, workflow identity, lifecycle machine, effect protocol, error model, config ledger, resilience, telemetry, status surface, acceptance gate, JSON Schemas, golden fixture, backup/restore.
- 64 new tests (79 total; 2 pk_core tests skip visibly). These include a real-subprocess crash test at all 12 before/after-commit boundaries, seeded property/fuzz tests, multi-connection contention, and a performance gate.
- `pyproject.toml`, reproducible wheel (identical bytes across two builds), `ci.sh`, hosted CI workflow (unpinned, never run), benchmark evidence bundle, OWNERS/WAIVERS ledgers (deliberately empty).

## 4.2.0 — 2026-09-22

Repository audit, correctness hardening, reproducibility improvement, and post-fix gap audit.

### Durable replay hardening

- Added `durable.py`, a stdlib-only replay engine so core correctness can be tested without the external `pk_core` framework.
- Added a runtime-checkable `HistoryStore` protocol so the replay engine is no longer coupled to the in-memory store and a production persistent adapter can be supplied.
- Replaced result-only history with append-only `started` / `completed` / `failed` events.
- Added conservative `ActivityInDoubt` handling: a started activity with no durable outcome is never blindly re-executed.
- Added stable optional activity IDs and replay fingerprints.
- Added deterministic tagged result encoding for supported scalar/container/bytes values.
- Added SHA-256 hash chaining and strict JSON history validation/tamper detection.
- Added a configurable history event bound and preflight capacity check before activity code executes.
- Added same-`Worker` concurrent-run refusal.
- Added explicit reconciliation of one trailing in-doubt activity without re-running user code.
- Preserved migration from the v4.1 legacy `[(activity_name, result), ...]` completed-history form.
- Stopped persisting exception messages in failure events to reduce accidental secret/tenant-data leakage.

### Test and integration hardening

- Added 12 self-contained durable-engine tests covering replay, duplicate-effect avoidance after completed steps, in-doubt crashes, divergence, shortened workflows, fingerprints, failure replay, tamper detection, capacity bounds, legacy migration, unsupported results, concurrency refusal, and optimized-mode behavior.
- Changed package imports so the stdlib replay engine remains importable when `pk_core` is absent.
- Split framework-dependent conformance tests from package metadata tests; version verification no longer skips with `pk_core` missing.
- Corrected `component.py` resilience evidence to target C057/C058 instead of incorrectly overwriting the first resilience checklist item.
- Updated evidence references after moving the replay engine to `durable.py`.

### Audit transparency

- Removed the README claim that `MASTER.md` is included; it was absent from the supplied archive and was not fabricated.
- Added `TRACEABILITY.json` with an explicit post-hardening status/evidence record for every checklist item.
- Added `AUDIT_REPORT.md` enumerating the remaining missing/partial production components.
- Version bumped consistently to 4.2.0.

### Validation in this archive

- Python compile: PASS.
- Self-contained/unit discovery: PASS.
- `pk_core`-dependent adapter tests: SKIPPED because `pk_core` is not included/importable in the supplied standalone archive.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assessment bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `tests/test_component.py`: added stdlib conformance coverage for the framework adapter.
- `VERSION` and `__version__` added.

### Defects fixed

- Replay that finished with fewer steps than the recorded history now raises `NonDeterminism`.

### Historical gate claim

The v4.1.0 changelog recorded all 100 requirements as satisfied under Python and `python -O`. The supplied v4.1.0 standalone ZIP did not include `pk_core`, so that framework-level claim was not independently reproducible during the v4.2.0 audit.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
