# Limited-host rehearsal -- UC-2.1.3 assembly, limited-host rehearsal

The ship's own BUILD and VERIFY, run on a copy of this tree in an environment shaped like a Windows workstation
without a C toolchain: PATH = python3 + java only (no cc, no make, no `sh`), Python without the `fork` start method,
a non-UTF-8 console encoding (`uc.py` re-executes itself in UTF-8 mode). It shows what such a host sees:
no traceback, no silent PASS -- the QUORUM engine alone (its LCTL column verifier through java directly), the
hull compile-only, and every gate that needs the rest SKIPPED with the reason.

* BUILD: `BUILT_HOST_LIMITED` (exit 0, 3.2s)
* VERIFY: `PASS` -- 14 passed, 0 failed, 5 skipped of 19 ship gates in 91.068s

| ship gate | status |
|---|---|
| U0.1 | SKIPPED |
| U0.2 | SKIPPED |
| U0.3 | PASS |
| U0.4 | PASS |
| U0.5 | PASS |
| U0.6 | SKIPPED |
| U1 | PASS |
| U2 | SKIPPED |
| U3 | PASS |
| U4 | PASS |
| U8 | PASS |
| U5 | PASS |
| U7 | SKIPPED |
| U6.* (berths) | PASS 6 |

| berth gate | statuses over every berth |
|---|---|
| B0 | PASS 6 |
| B1 | PASS 6 |
| B2 | PASS 6 |
| B3 | PASS 6 |
| B4 | PASS 6 |
| B5 | PASS 6 |
| B6 | PASS 6 |
| B7 | SKIPPED 6 |
| B8 | PASS 1, SKIPPED 5 |
| B9 | PASS 6 |
| B10 | SKIPPED 6 |
| B11 | SKIPPED 6 |

Records: `UC_BUILD_LIMITED_HOST.json`, `UC_GATE_RESULTS_LIMITED_HOST.json`, `LIMITED_HOST_BUILD.log`, `LIMITED_HOST_VERIFY.log`.
