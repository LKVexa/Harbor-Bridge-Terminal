# VWS master-prompt/workflow reapplication

## What was applied

The supplied archive contains 6,300 exact source checklist tasks and 60 terminal integration packs in 12 phases. UC-2.4.0 preserves the archive byte-for-byte, processes every original task record, verifies all 6,300 requirement hashes, preserves original task IDs/dependencies/source text, assigns a current execution home and candidate seam, and records the difference between source, inherited RAMWS and current evidence status.

The engineering pass implements and exercises the local containership integration: startup/configuration, scoped authentication, typed control transport, command authorization, gateway-owned Python jobs, output bounds, cancellation, runtime inspection and actual native workload execution. The original 96,000-task containership series remains independent and is not merged, renumbered or marked complete by the VWS pass.

## Architecture difference must remain visible

The VWS 2.0.0 source proposes a PowerShell/.NET public-service host with `hermit.vws.v1`. The later terminal attached by the user already implements Node `LOCAL_VOLATILE` / `hermit.vws.v2`. This integration retains that supplied architecture and terminal rather than replacing it. That is not evidence that the PowerShell, .NET, Render, distributed or durable branches ran. Original wording is unchanged inside `series.zip` and `SOURCE_MASTER.md`; current dispositions explicitly flag the mismatch and any missing owner-approved amendment/native evidence.

## Current source-task status

| Status | Work packs | Meaning |
|---|---:|---|
| OPEN | 3,900 | The source task is preserved; its individual acceptance and prerequisite evidence are not closed. |
| IN_PROGRESS | 55 | Related integration actions were applied, but exact source wording and full gates are not certified. |
| BLOCKED | 2,405 | Required alternate/native/hosted branch, approval or deployment evidence is unavailable. |
| PASS | 0 | No original work pack is bulk-promoted from adjacent tests or inherited claims. |

All 12 phase gates remain blocked for full-source promotion. This table is an honest engineering disposition, **not a claim of executing and completing all 6,360 full work packs**. Reapplication here is a source-complete traceability pass plus the concrete local integration and experiments described below. The outstanding individual source tasks are still outstanding.

## Phase application map

| Phase | Current pass actions and evidence boundary |
|---|---|
| P00 | Freeze three input identities; retain source archives; safe initial extraction; verify complete task inventory and source-record/requirement hashes; retain unsuccessful baseline evidence. |
| P01 | Keep supplied Node profile; add Python discovery and local launcher; fail on unavailable interpreter or contradictory profile; PowerShell/runtime alternative unqualified. |
| P02 | Exact credential revocation, `ship.read`/`ship.control`, fixed Origin and loopback policy, no host-shell passthrough; authorization regressions. |
| P03 | Typed request/cancel/chunk/result messages; bounded argv-array schema; uint48/binary terminal path retained; bridge/codec regression suite. |
| P04 | Reuse actual HTTP/WS gateway, health and handshake; local bind only; RFC frame conformance suite; no hosted TLS deployment. |
| P05 | Gateway-owned isolated Python process, one job globally, owner-bound cancellation, bounded capture/deadlines, worker-backend parity. |
| P06 | Register `ship` in the existing virtual command registry and retain VT/transport adapters; actual browser navigation blocked by environment policy. |
| P07 | Reservation bucket, classified output/timeout/cancel behavior, volatile sessions and explicit persistent ship state, disconnect cleanup. |
| P08 | Negative policy, authorization, malformed schema, stale generation and lifecycle tests; actual engines exercised through the WebSocket. |
| P09 | Windows-style/Unix local launchers and runbooks; native Windows, Docker, PowerShell and Render staging remain unobserved/blocked. |
| P10 | Bounded per-file test runner; raw logs and named runtime observations; no invented performance, capacity, cost or SLO qualification. |
| P11 | Updated source/readmes, preserved licenses, checksums, change/provenance ledger, residual-risk disclosure; no public Production GO. |

## Working with the remaining series

`APPLICATION.json` describes scope and phase gates. `ledger.jsonl.gz` has one disposition for every original task. The original archive contains each complete prompt, ordered workflow, acceptance oracle and phase/master context. `python -B tools/vws-pack.py TASK_ID` emits that context plus the current disposition without writing to the release or claiming execution. `uc.py vws-workflow show TASK_ID` returns the exact original source record and current mapping.

The checker refuses lost/duplicate IDs, altered source-record or requirement hashes, changed dependencies, inconsistent phase counts, corrupted input/ledger bytes and unsubstantiated per-item PASS. Source gate dependencies G00–G11 are recognized separately from work-pack IDs. Updating a disposition requires real task evidence and an intentional checker/review amendment; checksum success alone cannot promote a task.

Reviews in this pass are self-review. No independent reviewer, deployment authorization or owner approval has been invented. Historical PASS/NOT_APPLICABLE entries inside the supplied RAMWS are recorded separately and never silently carried forward as current successes.
