# INV-20 Audit Report — v4.3.0

## Scope
Execution of `INV20_v4.2.0_Missing_Components_Implementation_Checklist.md` (27 components, global rules,
final production checklist) against the supplied 4.2.0 tree. Work was done in a fresh copy of the
candidate; the 4.2.0 files were read before any change. Version bumped **4.2.0 → 4.3.0** (minor: additive
modules and APIs; no public name removed; `COMPONENT` became lazily loaded with the same name).

## Outcome
| Measure | Result |
|---|---|
| Components CLOSED_LOCAL | 8 of 27 (4, 5, 8, 11, 12, 17, 24, 25) |
| Components PARTIAL (in-repo work done, external residue) | 15 |
| Components BLOCKED (external decision/dependency) | 4 (1 pk_core, 7 TLS owner, 20 ownership, 22 policy approval) |
| Dependency-independent tests | 8 suites, all pass normally and under `python -O` (≈150 test methods incl. subtests) |
| Clean-room | wheel built from a pristine copy, installed with `--no-index` into a fresh venv; suites pass against the installed artifact |
| Fuzz | 3 × 8,000 seeded inputs per VERIFY run across 8 targets; 0 crashes/oracle violations/hangs |
| Benchmark | dispatch p99 ≈ 0.3 ms (SLO < 1 ms) — sandbox hardware, not a controlled baseline |
| `VERIFY.py` | exit **2 BLOCKED**; certification 100/100 BLOCKED; local verification 6 PASS / 94 BLOCKED / 0 FAIL |

## Defects found while executing the checklist
1. **Dispatch SLO breach (new async path).** The first async implementation polled for the response head
   every 1 ms; the benchmark gate measured p99 ≈ 1.6 ms against the 1 ms contract SLO. Replaced with
   event-driven waiting (p99 ≈ 0.3 ms). Caught by `bench/run_bench.py`.
2. **Sticky DNS denial.** A denied answer stayed in the resolver cache for its TTL, so a corrected record kept
   being denied. Denials are no longer cached. Caught by `test_egress.test_answer_change_between_checks_is_revalidated`.
3. **Bytecode leaked into the wheel.** Building in place after the compile stage shipped `__pycache__/*.pyc`.
   Builds now run from a pristine copy; `inspect_wheel` rejects `.pyc`, evidence, keys and env files.
4. **Unbounded metric label.** The 4.2.0 contract labelled `egress_denials` by "attempted host" — an
   attacker-controlled, unbounded label. Now a bounded reason code; unknown values collapse to `other`.
5. **Ambiguous host forms.** `canonical_host` accepted `%` (e.g. `fe80::1%eth0` is valid to `ipaddress` on
   3.9+) and backslashes; both are now rejected.
6. **Eager pk_core import.** Importing the package failed without pk_core, so nothing — not even the
   dependency-free primitives — could be installed or tested in a clean environment. Now lazy with a precise
   `PkCoreUnavailable`.
7. **Ambient dependency resolution.** `test_component.py` injected `PK_CORE_PATH` and parent directories into
   `sys.path`, which could load an unintended pk_core. Removed; `pk_compat.probe` also flags a copy shadowed
   from the source tree.
8. **Distro build breakage.** Debian-patched setuptools fails with `install_layout`; the release tool sets
   `SETUPTOOLS_USE_DISTUTILS=stdlib`.

9. **Flaky benchmark gate.** A p99-only regression rule failed a clean run on shared-runner noise
   (stream p99 1.5× baseline, median unchanged). The gate now keys regressions on the median with 2×
   extra headroom on p99; the absolute 1 ms dispatch SLO is still checked on p99.

## Honesty constraints applied
- No owner, approver, on-call contact, license, upstream WIT digest or pk_core coordinate was invented;
  each is recorded as UNASSIGNED/UNRESOLVED and blocks the gate.
- Reference implementations (HMAC identity documents, asyncio lifecycle, injected resolver/transport) are
  labelled as such; runtime/SVID/TLS integration remains PARTIAL/BLOCKED.
- The CI workflow's pinned action SHAs were written from reference and must be verified before enabling.
- A requirement is PASS only if every component mapped to it is CLOSED_LOCAL and its mapped tests ran and
  passed in this run; a skipped mandatory suite downgrades PASS to BLOCKED; waivers can never hide FAIL.

## Global completion rules — how each is met
| Rule | Where |
|---|---|
| Work-item ID, owner, reviewer, target release, deps | `components.json` (owners UNASSIGNED → blocks) |
| Link to INV-20-Cxxx | `components.json.maps_to`, `evidence/requirements/*.json` |
| Immutable vs mutable separation | `config.py` (secret refs only), `docs/ops/STATE_AND_RECONSTRUCTION.md` |
| Fail closed | identity/PDP/audit/resolver/config paths all deny on ambiguity or dependency failure |
| Versioned public surfaces | `INV20_CONFIG/1`, `INV20_CAP/1`, `INV20_ERROR/1`, `INV20_EVIDENCE/1`, `INV20_HEALTH/1`, `INV20_AUDIT/1`, WIT `pk:inv20@4.3.0` |
| Deterministic unit + negative tests | `tests/` (injected clocks, seeded RNGs) |
| Tool versions / commands / platform / digests | `evidence/tests/testrun.json`, `evidence/release.json`, `dist/build_manifest.json` |
| CI fails on missing evidence / skips / stale files / drift / waivers | `evidence_gate.gate`, `witgen --check`, `version_check`, workflow |
| Re-run VERIFY, -O, conformance after closure | `VERIFY.py` stages 4 and 8 |
