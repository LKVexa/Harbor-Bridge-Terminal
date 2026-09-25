# Source baseline, reproduced defects, claim ledger

## Frozen inputs (I001)

`ledger/source.json` records SHA-256, size and entry count of the seven supplied archives, the SHA-256 of all 35 files of the candidate baseline, and the task inventory check: **6300 source task IDs, 6300 unique, 0 requirement-hash mismatches, 60 integration packs**. The four DF node zips match the digests pinned in `DF_Fabric/DF_INDEX.md` (`d64085ac…`, `7c57c6ce…`, `7acac542…`, `c0432c14…`). `python3 tools/verify.py` of the VWS200 package passed unmodified.

Note: the series audited `hermit-spiral-terminal` v1.0.0 (29 files). The archive supplied for this run is a **newer 35-file revision** that adds the DF fabric and VEC1 Photon commands and a restyled renderer. The series' source line locators therefore drift; findings were re-derived against the supplied revision (next section) rather than assumed.

## Baseline probes, before and after (I003)

The series' seven offline probes were run unchanged against the supplied archive, then against the candidate (`e/I003/*.json`).

| Probe | Supplied archive | Candidate | Note |
|---|---|---|---|
| 01 same-kernel sessions share a VFS | true | true (by design) | LOCAL is single-user. Remote isolation is one kernel **per worker process**; OBSERVED cross-tenant file test. |
| 02 output before the consumer knows the id | 4 early events | 4 in legacy mode; **0 with `deferStart`** | Both adapters always use the barrier; OBSERVED in kernel, IPC-adapter and gateway tests. |
| 03 invalid geometry stored | -3 x 0 | refused, 80 x 24 kept | |
| 04 close leaves the reader unsettled | unsettled | settled, one `exit` | |
| 05 unterminated OSC retention | 8194 units | 4096 cap, never dispatched | |
| 06 scrollback after resize churn | 5037 > 5000 | 5000 | plus a 2 000 000-cell budget |
| 07 Buffer append | `efbfbd00` | `ff00` | |

Additional defects found while integrating (not in the series audit): CSI counts were unbounded (`CSI 999999999 @` loops a billion times in the renderer — a remote tab freeze); text pasted with newlines lost every line after the first; `seq` could allocate without limit; `LineReader` escape accumulation was unbounded; `vfs.move` could move a directory into itself and ignored quota effects. All fixed with tests.

A pre-existing behaviour left unchanged: `$?` and variables are expanded when the whole line is parsed, so `false; echo $?` prints the previous line's status. It is a shell-semantics quirk, not a safety issue.

## Claim ledger delta (I004)

The series register Q01–Q12 stands. This run adds observations:

| Claim | Status after this run |
|---|---|
| Q01 WebSocket upgrades are not CORS-preflighted; Origin must be checked server-side | OBSERVED in Chromium: the upgrade carried `Origin`, no preflight; the ticket API answers CORS separately. |
| Q02 browsers cannot set WebSocket headers | Designed around (ticket cookie); OBSERVED: no credential in URL. |
| Q03/Q09 .NET keep-alive and Linux HttpListener feasibility | **UNVERIFIED — not runnable here** (no `pwsh`/`dotnet`; registries blocked). Inactive under D-001. |
| Q04 stop listener before draining sockets | Candidate order: admission off -> notify -> close sessions -> reap workers -> close listener. OBSERVED on a real process with SIGTERM. |
| Q05/Q06 Render shutdown window and health semantics | DOCUMENTED only. No Render service exists; UNVERIFIED. |
| Q07 receive buffer vs frame vs message boundaries | OBSERVED: fragment, interleaved-control and split-UTF-8 fixtures. |
| Q10 VB-JA21 bundle | Still absent from the supplied archive. |
| Q11 BrowserView deprecation | Evaluated in `docs/DESKTOP.md`; migration not performed (Electron not runnable here). |
| Q12 snapshots are not live resumption | Implemented as quiescent-only; a running command refuses the snapshot. |
