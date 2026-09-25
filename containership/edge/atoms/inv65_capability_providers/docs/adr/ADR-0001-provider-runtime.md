# ADR-0001: INV-65 provider runtime composition

Status: **PROPOSED** (approval is a human act; not approved by this pass)
Date: 2026-09-22

Context: 4.2.0 shipped an in-memory reference model; the audit listed 40 missing production components.
Decision: keep the reference model as the invariant oracle, and compose a production `ProviderService` from separable layers (authn, authz, identity, secrets, durable WAL store, config history, lifecycle, admission, call control, health, fencing, residency, audit, telemetry) behind an HTTP/JSON transport, stdlib-only with an optional `cryptography` extra.
Consequences: every layer is independently testable; INV-60/61/55/64 integrate through narrow seams; WIT/RPC transport remains INV-61's job; single-writer state requires lease fencing.
Alternatives rejected: embedding policy (violates non-ownership), a database dependency for state (unneeded for single-writer WAL), gRPC (extra dependency, INV-61 owns RPC).
