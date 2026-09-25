# Security model and residual risk

Security contacts, escalation and vulnerability ownership: [`ops/OWNERS.md`](../ops/OWNERS.md)
(`inv69-security-owner`); incident procedures: [`ops/RUNBOOK.md`](../ops/RUNBOOK.md).

## Trust boundary

INV-69 treats the model/agent planner and all tool arguments as untrusted.
The deterministic runtime kernel is the policy enforcement point for tool
selection, budgets, approval consumption, sandbox-tier routing and local audit
recording. Tool implementations, identity providers, sandboxes, persistence
systems and external approval workflows are dependencies, not trusted by
default merely because they are adjacent.

## Implemented controls

- Immutable built-in tool metadata (`ToolSpec` plus read-only registry).
- Construction-time rejection of unknown allowlist entries.
- Positive step, cost and audit-capacity bounds.
- One-use approval tokens bound to exact canonicalized arguments via HMAC.
- Self-approval, approval of disallowed tools and approval of non-side-effect
  tools are rejected.
- Side-effectful tools remain pending until an approval exists.
- High-risk tools route to the heavy sandbox tier.
- Raw tool arguments are not persisted in the transcript.
- Each audit event contains a sequence number, previous hash and event hash.
- A lock serializes policy decisions for one agent instance.
- Audit-capacity exhaustion seals execution and causes subsequent operations to
  fail closed rather than run without an audit trail.

## Threats covered by local tests

The standalone suite covers allowlist bypass, approval replay, approval binding
to different arguments, self-approval, unhashable payload handling, step/cost
budget exhaustion, transcript secret exposure, transcript mutation detection,
high-risk routing, concurrent budget races and audit-capacity exhaustion.

## Residual risks / required external controls

The local reference implementation does **not** provide identity authentication,
cryptographic artifact provenance, tenant process/memory isolation, network
policy, durable execution, distributed replay prevention, key management,
encryption at rest/in transit, signed/remote transcript anchoring, centralized
telemetry, sandbox implementation, or business approval workflow. Those controls
must be supplied by adjacent layers and integration-tested before production.

The argument binding key is process-local. Approvals are intentionally not
portable across process restart. A production durable approval service needs a
versioned, authenticated, replay-resistant record format and explicit expiry.

The hash chain detects local mutations relative to the live head; it is not a
substitute for an externally sealed audit log.

## v4.3.0 additions

- The error taxonomy never exports exception messages or tracebacks. Unknown exceptions map to
  AGT-INTERNAL-001 (`errors.translate`).
- Redaction now covers secret-looking field **names** as well as values. Fuzzing found that v4.2.0's
  `_arg_shape` echoed a secret used as a dict key into the transcript.
- Input bounds (depth 32, 4096 items, 1 MiB strings) are enforced by an iterative guard **before**
  recursive canonicalization. v4.2.0 raised RecursionError on deeply nested arguments.
- Every trust dependency has a fail-closed matrix (`trust.DEPENDENCY_MATRIX`). Losing keys or trusted
  time blocks approvals.
- The artifact verifier checks the digest, source, version, revocation list and signer, and binds
  generated code to its provenance. Generated code is never run in the fast tier.
- Configuration secrets are `secretref://` references only. Locked fields cannot be overridden below
  their scope. Emergency overrides may only tighten a setting.
- Failover is fenced before any side effect. Approvals never cross a failover or a restore.

## Vulnerability response, patching and end of life (C094)

**Intake.** Report privately to `inv69-security-owner` (see OWNERS.md). The report is acknowledged
within 2 business days. Embargoed reports are handled on a private branch that only the owners and the
security owner can see.

**Severity (CVSS v3.1 base score plus exploitability) and remediation SLA**, measured from confirmation
until a fixed release is available:

| Severity | SLA |
|---|---|
| Critical, or actively exploited | 72 h, emergency path |
| High | 14 days |
| Medium | 45 days |
| Low | next routine release |

**Routine cadence.**
- A dependency and toolchain review runs every month (R-DEPS in `ops/REVIEWS.json`).
- A patch release is cut every month if anything changed.
- The runtime is stdlib-only, so a "dependency update" means a CPython patch level.

**Emergency release.** The mandatory safety profile is never skipped. `tests/run_all.py` runs in both
normal and `-O` mode, and the release gate lanes still apply. Only the performance baseline comparison
may be waived, and that needs a WAIVERS.json entry.

**Support and end of life.** See `ops/EOL.json`. A release line becomes security-fix-only when the
second-next minor ships, and reaches EOL 180 days later. Unsupported versions are refused by
`compat.handshake`, which reads the compatibility matrix.

**Known gaps.** Not yet in place:
- automated advisory-database scanning (the build runs offline)
- an SLA-clock tracker (this needs an issue tracker)

Both appear as partial for C094 in `ops/RTM.md`.
