# Production acceptance policy and exit gate (work item 26 — C090, C100)

Mandatory evidence categories: architecture, requirements, interfaces, implementation, security,
resilience, performance, observability, testing, rollback, ownership, supply chain — one or more RTM
rows each (`governance/RTM.json`).

Acceptable states for each of the 100 checks:
- `PASS` — linked artifact(s) exist and every linked test passed in this gate run.
- `EXTERNAL` — peer-owned; accepted only with an unexpired waiver referencing the peer's evidence.
- `NOT_APPLICABLE` — accepted only with written justification **and** an approved, unexpired waiver.
- `BLOCKED` / `FAIL` — never acceptable for GO.
Conditional approval (`CONDITIONAL_GO`) is allowed only when every non-PASS row is covered by an
approved, unexpired waiver; the gate lists the conditions and expiries.

Gate artifact (`conformance/PK_GATE_RESULTS.json`, produced by `tools/gate.py run`) contains: schema,
package version, source-tree digest, git commit if available, release archive digest if built, python
and platform, per-check outcomes with evidence digests, evidence-chain head, waivers applied, approver
identities (from `governance/approvals.json`), previous gate digest, and an HMAC signature when
`INV25_GATE_KEY` is present (organisational signing PENDING W-0005).

Enforcement: CI release job fails unless verdict is GO; `tools/gate.py verify` recomputes the source
digest so a gate cannot be reused after code/config/dependency changes; any surface-widening activation
or security-policy change requires a new gate.

Required approvers: component owner, security reviewer, release approver — none may be the author of
the change.
