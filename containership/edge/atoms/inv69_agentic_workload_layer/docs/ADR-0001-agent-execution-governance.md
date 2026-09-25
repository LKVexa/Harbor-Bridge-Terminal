# ADR-0001: Agent execution governance boundary

- **Status:** Accepted for the reference component
- **Date:** 2026-09-22
- **Decision scope:** INV-69 Agentic workload layer

## Context

Model-driven agents may iterate, call tools, encounter hostile input, and request
operations with side effects. Treating the model's own plan or narration as an
authority would collapse the trust boundary. INV-69 therefore needs a small,
deterministic enforcement kernel that can be exercised without the model or the
external conformance framework.

## Decision

The agentic workload layer owns policy enforcement around a tool invocation:
a per-agent allowlist, bounded invocation and cost budgets, one-use approval for
side-effectful tools, risk-class-to-sandbox routing, and an append-only-style
local transcript hash chain. Raw tool arguments are not persisted in the
transcript; approval binding uses a process-local keyed digest of canonicalized
arguments.

The model, tool implementation, sandbox internals, identity issuance, durable
execution, and business approval workflow remain outside this component.

## Consequences

- Safety-kernel tests can run with only the Python standard library.
- Side-effect approval is exact-argument-bound and one-use.
- Unknown tools cannot be admitted into an agent allowlist.
- Mutable raw arguments no longer need to be hashable to receive approval.
- Transcript tampering is detectable within the live process state.
- Durable/signed audit anchoring is still required externally; the in-memory
  hash chain is not sufficient against a process owner who can rewrite both the
  history and current head.
- Authentication, distributed authorization, sandbox enforcement and durable
  execution remain integration responsibilities and must be proven separately.
