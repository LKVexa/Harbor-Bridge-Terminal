# ADR-001 — Serial-bound plan/apply engine with file-backed CAS state (MC-003)

- **Status:** Proposed (needs approval by accountable owner + security reviewer; see `OWNERS.yaml`)
- **Date:** 2026-09-22
- **Deciders:** _owner to record_

## Context
INV-06 must refuse stale plans, protect resources, detect drift, and survive crash/concurrency. v4.2.0 had an in-memory engine only.

## Decision
1. Keep `IacState` as the semantic core (serial-bound plans, SHA-256 plan digest, protected set advances serial).
2. Persist state as immutable digest-sealed revisions with a `HEAD` pointer moved by `fsync`+`os.replace`, guarded by a WAL intent/commit journal; publish by compare-and-swap on serial (`durable.FileStateBackend`).
3. Mutual exclusion by lease + monotonic fencing token (`locking`); backend refuses stale tokens.
4. Configuration: a pinned, deliberately small HCL subset compiled locally; full Terraform HCL executes only through a digest-pinned external binary with `-json` output parsing (`execution.TerraformRunner`).
5. Policy (GAP-13), identity, keys, audit sinks and providers are bound by protocol and fail closed.
6. Standard library only; zero runtime dependencies.

## Alternatives considered
| Option | Why not (now) |
|---|---|
| Terraform remote backends (S3+DynamoDB, Consul, Terraform Cloud) as the only state | Couples reference semantics to one vendor; remains the recommended estate backend behind `FileStateBackend`'s interface. |
| SQLite / embedded DB | Adds locking semantics that break on network/OneDrive filesystems; heavier to audit. |
| Pulumi/CDK | Different programming model; out of scope of "traditional IaC". |
| Full HCL parser (python-hcl2) | Third-party dependency and larger attack surface; subset refuses rather than half-interprets. |

## Consequences
+ Deterministic, auditable, testable without cloud access. − Single-host durability only; multi-site needs an estate backend implementing the same CAS + fencing contract. − HCL subset is not Terraform-compatible by design.

## Approval history
| Date | Approver | Role | Decision |
|---|---|---|---|
| | | | |
