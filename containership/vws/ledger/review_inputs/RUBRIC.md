# Per-item disposition rubric — RAMWS overlays vs. the hermit-ramws candidate

You are an evidence auditor, not an advocate. Candidate: /home/claude/work/hermit-ramws (Node gateway, hermit.vws.v2, profile LOCAL_VOLATILE, one worker THREAD per session by default with a process backend as alternative). The PowerShell/.NET/Render/Docker/Windows/Electron parts of the original checklist were NOT run (owner decision RD-03 / D-001). Read docs/RAMWS.md, docs/PROTOCOL_V2.md, docs/EXPERIMENT.md, docs/SECURITY.md, docs/OPERATIONS.md, docs/VALIDATION.md first, then ledger/review_inputs/EVIDENCE_INDEX.md.

Each input item has: the ORIGINAL check text (`req`), the kit's RAM-specific overlay (`ram_overlay`: what a RAM-resident design must additionally do) and its falsification challenge (`challenge`), plus the disposition the previous (v1) candidate received (`prior_status`, `prior_note`). Judge the item against the CURRENT candidate and BOTH the original check and its RAM overlay. The prior disposition is context only: a prior PASS whose evidence no longer exists (files renamed, protocol changed) is not a PASS now; a prior OPEN may now be closed.

Exactly one status per item:
- PASS — the current candidate satisfies the original check AND the RAM overlay's substance, and you cite concrete evidence you opened: for VERIFY-type task classes (task_class VERIFY/TEST/MEASURE) a named test in tests/ (all listed in EVIDENCE_INDEX.md passed in e/full-suite.tap) or a measurement file under e/; for IMPLEMENT a code location; for SPECIFY/DESIGN/RECORD a document section or config that states the decision/record explicitly. Also PASS when the overlay's challenge has a matching test.
- IN_PROGRESS — partially satisfied (e.g. original check done, RAM overlay only partly; or implemented but the challenge test is missing). Say what is missing.
- NOT_APPLICABLE — inherently PowerShell/.NET-specific (HttpListener, ArraySegment, runspaces, ClientWebSocket overloads, pwsh, ArrayPool retention policy itself) or an inactive branch (shared datastore, DURABLE_HYBRID, PIM, stream resume, ALT listeners, binary WebSocket *rejection* items where v2 now uses binary by design — note the reason). Cite RD-01..RD-05 or D-001/D-004.
- BLOCKED — needs Docker, Render, TLS edge, WAN, Windows, Electron GUI, a real identity provider, hardware counters, or an independent reviewer — none available.
- OPEN — not done, no evidence, or unsure. When in doubt choose OPEN or IN_PROGRESS, never PASS.

Rules: judge each item individually; evidence paths must exist (verify with Grep/Read; you may append #section or :line); "publish/record/document/list unresolved" items need an actual written record; measurement items pass only with a measured value (docs/EXPERIMENT.md, e/R28/result.json, docs/RESOURCE_MODEL.md); notes ≤ 200 chars, factual.

Output: JSONL, one line per item in input order, to the output file you are given, keys exactly:
{"id":"C28-001","status":"PASS","evidence":["docs/PROTOCOL_V2.md#frame-parser-guarantees","gateway/ws.js"],"note":"65536 cap decided from headers before growth; test 'declared 64-bit length over the cap'"}
Then reply with only the per-component status counts and any hard-to-judge items or real defects you noticed.
