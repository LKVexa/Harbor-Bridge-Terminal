# Testing and certification (MC-071 .. MC-079)

`python inv62_edge_topology/tools/ci.py` runs every lane and writes `evidence/ci_report.json`. A lane that
cannot run reports `NOT_RUN` and the overall result is `INCOMPLETE` (exit 3) — never PASS. Skipped tests do
not satisfy any gate: the unit lane fails if any test outside the pk_core adapter is skipped.

| Lane | Command | Covers |
|---|---|---|
| compile | `python -m compileall -q` | syntax |
| lint | `ruff check .` | MC-093 |
| types | `mypy` (config in pyproject) | MC-093 |
| unit / unit-O | `python [-O] -m unittest discover -s tests` | all suites, optimised mode |
| contract | fixtures + schema sync | MC-071, MC-019 |
| security | `tests/test_security.py` | MC-040, MC-076 |
| fuzz | `INV62_FUZZ_ITERS=3000` property + byte fuzz | MC-074 |
| concurrency | `tests/test_concurrency.py` | MC-075 |
| faults | `tests/test_faults.py` | MC-050, MC-078 |
| integration | `tests/test_integration.py` | MC-020, MC-072 |
| bootstrap | `tests/test_bootstrap.py` | MC-030 |
| perf | `tools/bench.py --gate` | MC-051..060, MC-077 |
| rtm | `tools/rtm.py --check` | MC-011, MC-079 |
| docs | referenced paths/commands exist | global rule 9 |
| secrets | no inline key material in the tree | global rule 3 |
| pk-core | external 100-item gate | NOT_RUN when absent |
| license | licence selected | NOT_RUN until MC-090 closes |

Compatibility (MC-073): only CPython 3.11 / Linux x86_64 is exercised here; the matrix in COMPATIBILITY.md
lists what is declared vs tested. Soak/fleet (MC-077): the bench overload scenario and the 5-cycle
partition test are the only long-running evidence; multi-hour soak and fleet-scale runs are open.
