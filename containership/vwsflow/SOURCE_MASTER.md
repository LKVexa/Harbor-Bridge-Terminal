# Virtual WebSocket terminal — master prompt and workflow

**Series version:** 2.0.0. **Source basis:** PSWS checklist v1.0.0 (6300 actions) plus supplied HERMIT/SPIRAL terminal v1.0.0. **Additional series:** 60 integration work packs in 12 phases. **All engineering work statuses:** OPEN. This is a complete planning/prompt package, not a completed service implementation.

## Master prompt

Act as a senior distributed-systems engineer, PowerShell/.NET networking specialist, Node runtime engineer, terminal-protocol engineer and security reviewer. Implement the selected work pack against an isolated candidate derived from the supplied source; do not replace the source with an unrelated terminal or claim that absent components exist. Preserve all original checklist IDs, requirement text, applicability and source provenance. The authored architecture extends the source; classify SOURCE, DOCUMENTED, OBSERVED, PROPOSED and UNVERIFIED information explicitly.

Build toward a standards-based authenticated virtual terminal over WebSockets. Preserve HERMIT's internal VT parser, Screen and CanvasRenderer and SPIRAL's registry, VFS, pipeline and line editor where they meet the contract. Introduce a transport-neutral adapter; retain local IPC as a compatibility profile, add a browser WebSocket adapter, and run SPIRAL headlessly behind a PowerShell gateway. The default remote execution surface is the virtual command registry, not arbitrary PowerShell or an operating-system shell. Treat all remote messages, terminal escapes and worker output as untrusted data.

Read the selected task, its exact source item, the applicable phase, `docs/ARCHITECTURE.md`, `docs/RESEARCH.md`, `docs/SOURCE_AUDIT.md` and the named source seams before editing. Proposed target paths are future candidate paths, not verified existing files. Establish candidate/runtime/provider identities and dependencies. Keep Linux HttpListener feasibility, signal handling, close ownership and hosted deployment claims blocked until empirically demonstrated on the selected image. An explicitly approved fallback can change architecture, but must preserve protocol parity and attach dispositions to affected source tasks.

For the chosen task, formulate a precise requirement interpretation, invariant and failure oracle. Perform task-appropriate design, implementation or verification; do not turn a documentation-only requirement into unnecessary runtime functionality. Use bounded allocation, one send/one receive ownership, tenant/session authorization, secret isolation, validated dimensions, safe URL/capability boundaries and deterministic cleanup. Do not use completion of generated prose as evidence that code, tests or a deployment passed.

Return actual changed files or justified no-code disposition, tests with commands and raw observations, measurements with units/environment, evidence hashes, residual risks, rollback instructions and a reviewed RESULT record. Missing credentials, tools, image compatibility or user authorization produces BLOCKED—not invented settings, successful logs or a Production GO claim. Never expose a public service until the selected profile's applicable gates pass and deployment is authorized.

## Master workflow

1. Freeze original archives, hash files and parse exactly 6300 source task IDs with immutable requirement text.
2. Reproduce the baseline terminal behavior and classify observed faults independently from code-inspection concerns.
3. Verify the claim ledger using primary references and design an exact-runtime/hosted experiment for unresolved claims.
4. Select profile, topology, identity seam, protocol, resource limits and optional branch applicability through recorded decisions.
5. Execute integration work packs in phase order, completing prerequisites and using a scoped candidate copy.
6. Execute each phase's mapped source checklist work packs; parallelize only when file ownership and dependencies permit.
7. Add a requirement-specific regression or decision oracle, implement the smallest correct change and run positive/boundary/negative tests.
8. Preserve byte and session semantics across client, gateway, pipe and worker; enforce resource and authorization boundaries end to end.
9. Run cross-runtime conformance, adversarial isolation, load, lifecycle, recovery and client/accessibility experiments.
10. Rehearse authorized staging deployment, drain, reconnect, restart, secret rotation and rollback using actual runtime evidence.
11. Review every applicable source/integration task and record PASS, FAIL, BLOCKED or justified NOT_APPLICABLE with immutable evidence.
12. Version and package only what was actually implemented and validated; preserve source licensing and identify every unsupported or untested profile.

## Navigation

Read [INDEX](INDEX.md) for all components and phases, [integration master](INTEGRATION.md) for the full integration series, and [execution rules](docs/EXECUTION.md) for evidence/dependency semantics. Individual checklist prompts are under `tasks/<component>/<number>.md`; each contains a fully populated prompt and workflow for exactly one original item.
