# UC-2.4.0 validation and delivery scope

This is an integrated local candidate, not a public Production GO or complete execution of every VWS work pack. Evidence was generated on Linux x86-64 with Node v22.16.0 and Python 3.13.5 on September 22, 2026. No Windows, macOS or deployed-service run is implied.

## Final observed checks

| Check | Observed result | Evidence under `evidence/uc240/` |
|---|---|---|
| Complete portable terminal test run | **144 passed, 0 failed, 7 explicitly skipped**, 21 files / 151 tests. | `suite-qualified/results.json` and per-file TAP logs |
| Full containership Python regression run, including new VWS tests | **272 passed**. Earlier 266-test and separate six-test runs are historical supporting observations, not additional independent tests. | `uc-self-test-final.log` |
| Native build | **BUILT:** four engines, executable hull, six successful berth faces; no reported build problems. | `uc-build.log`, `BUILD_20260922T092124567171Z.json` |
| Actual WebSocket control execution | Stale generation refused; sealed witnesses agreed and matched the pinned reference; one TIFF tick returned `TICK_OK`. | `ship-execution.log`, `ship-execution-observation.json`, two `RUN_*.json` records |
| Real loopback launcher | Issued only a hashed stored credential, browser-style single-use cookie authentication succeeded, read-only ship request succeeded, busy-port `--new-token` left the original credential unchanged. | `ship-launcher-corrected.tap`, final suite launcher TAP |
| VWS source/ledger integrity | **6,360** exact source records and **6,300** requirement hashes verified; **12** phases accounted for; **0** phase gates closed. | `vws-workflow-check-final.json` |
| Original hull and hold | **38** original files unchanged during this pass. | `payload-preservation.json` |

The default Node run intentionally skips six legacy DF integration cases because their separate sibling container layout is absent, and skips the destructive/native ship-control case unless explicitly enabled. The ship-control case was separately enabled and observed to pass against the built candidate. Default test-file discovery excludes both browser test files; this exclusion is not counted as either a pass or an executed skip. No load/latency/SLO, capacity or cost result is fabricated.

## Important unsuccessful or blocked attempts

The initial monolithic baseline run exceeded its time budget. Early bridge tests exposed missing bounded-array schema support and a legacy hello-packet compatibility mismatch; both were fixed and the final complete portable run passed. An intermediate integration test overlapped the native verification process and was correctly refused by the existing UC lock; that failed attempt is retained rather than rewritten.

The inherited allocation stress test requested four million sequence items, but the sequence command rejects more than one million before capture/heap enforcement is reached. Its old predicate therefore waited for an error that could not occur. The corrected test requests one million items, observes the explicit one-MiB capture-limit refusal, and confirms another tenant remains responsive on both worker backends. This is a capture-budget test, **not an observed native-child or V8 out-of-memory qualification**. The launcher test also originally used bearer authentication directly on an Origin-present WebSocket, which this profile refuses by design; the corrected test performs the required HTTP ticket/cookie exchange.

**All-berth `uc.py verify --quick` did not complete within 180 seconds.** It is recorded as an incomplete timeout, never a pass. The candidate's pending managed verification transaction was subsequently rolled back; `recovery-final.json` reports `ROLLED_BACK`. The large `recovery-rollback.json` retains the detailed observation. `recovery-before-rollback.json` is explicitly historical and shows the earlier pending state. A workflow check attempted while the old process still owned the lock was refused; the later `vws-workflow-check-final.json` completed successfully. There is no full all-berth qualification for this release. The web command now requires `ship verify BERTH`; all-berth verification stays on the local CLI.

The actual Chromium UI test could not navigate to the local gateway because the environment returned **`ERR_BLOCKED_BY_ADMINISTRATOR`**. No browser policy was bypassed and no rendered-UI acceptance is claimed. The HTTP ticket, WebSocket, worker and terminal-command paths were tested using the independent Node client. Native Windows CMD launch/ACL behavior, Windows child-tree termination, macOS, Electron, Docker, Render and public TLS deployment remain unobserved.

## Limits and source-task status

Native Python/engine child memory and CPU limits are **not enforced by this integration**. Cancellation/output/deadline policies and worker budgets do not turn the containership into an OS sandbox. An abrupt parent death or interrupted native write can still require local recovery. Only managed files are covered by recovery; external effects cannot be assumed reversible.

The terminal retains `LOCAL_VOLATILE` sessions, but the ship persists TIFF/lifecycle files and runtime evidence. This is not an entirely RAM-only application, bootable guest or hypervisor. Review `SECURITY.md` and `OPERATIONS.md` in this directory.

All **6,360** original VWS work packs were retained and dispositioned: **3,900 OPEN; 55 IN_PROGRESS; 2,405 BLOCKED; 0 PASS**. All **12** full-source phase gates remain blocked. The source's PowerShell/.NET/v1 alternatives are not certified by this Node/v2 integration. The 96,000-task containership workflow remains separate. See `REAPPLICATION.md` for the phase-by-phase application map.

## Evidence handling and release integrity

`RESULT.json` and `metrics.json` describe the integration rather than promoting any original work pack. `changes.json` records differences from the two input source trees. The `suite`, `suite-final` and `suite-release` subdirectories retain unsuccessful/intermediate runs; **`suite-qualified` is the final portable run**. Earlier raw logs are not current pass claims. Reviews are self-review only.

The delivered archive excludes qualification-machine `_runs`, `_engines`, `_studio`, live `_fabric` state, tokens and generated caches. It includes selected historical logs under this evidence directory. Fresh extraction uses local installed runtimes and rebuilds its own native outputs. Root `SHA256SUMS.txt` and `MANIFEST.json` bind delivered bytes; the terminal has its own exact inventory in `vws/release/manifest.json`. Final package checks are reported separately in the companion integration report to avoid self-referential checksum edits.
