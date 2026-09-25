# ADR-0001 — Fail-closed Wasm hardening boundary with evidence-bound admission (C010)

- **Status:** PROPOSED (not approved — approver UNASSIGNED)
- **Date:** 2026-09-22
- **Deciders:** UNASSIGNED

## Context
INV-44 declares Swivel (compiler-based Spectre mitigation) as its technology.
v4.2.0 modelled the boundary in Python and trusted a caller-supplied Boolean
for "compiled output verified". The master source (MASTER.md) is absent.

## Decision
1. Admission goes through `TenantGateway`: authenticate → authorize → tenant
   match → admission control → receipt verification bound to module bytes,
   toolchain identity and full hardening profile → ambient-import check →
   hardened engine → audit, in that order, every step fail-closed.
2. A verification receipt is the only accepted proof of verified output; the
   Boolean `Engine.instantiate(output_valid=)` path is legacy, kept only for
   the pk_core component model, and slated for removal in 5.0.0.
3. The production compiler is Swivel (or an approved successor) pinned by
   digest in `approved_toolchains`; no receipt from any other toolchain admits.
4. Everything stays stdlib-only so the security core has no supply-chain surface.

## Consequences
- Production is impossible until component 8 (Swivel integration) exists; that is intended.
- HMAC receipts mean verifier and issuer share a key; moving to asymmetric keys
  in a KMS is required before multi-party deployment.
- Host-level tenant isolation must come from the runtime, not this package.

## Alternatives considered
- Keep the Boolean verdict: rejected — it is an honour system.
- Interpreter-only execution for unverifiable modules (contract "optional"): deferred.
