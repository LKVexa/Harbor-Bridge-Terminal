# ADR-PLN02-001 — Application plane architecture

| Field | Value |
|---|---|
| **State** | **Proposed** (not Accepted: no approval evidence exists yet) |
| Created | 2026-09-23 (v4.3.0 build) |
| Governs | MC-02, C009, C010; all `AP-REQ-*` in `docs/spec/REQUIREMENTS.md` |
| Required approvers (quorum 2 of 3) | Plane owner · Security lead · Schema governance lead |
| Next mandatory review | 2027-03-23, or earlier on a trigger below |
| Supersedes / superseded by | — / — |

## Problem and scope

PLN-02 turns a declared composition of components into an immutable, content-addressed application revision
bound to concrete providers, or refuses. Scope: modelling, resolution, selection policy, publication and the
controls around them. Non-goals: placement, execution, provider implementation, transport, estate desired state.

## Decision

1. **Pure deterministic core.** `resolver.py` stays side-effect free and stdlib-only; identity is SHA-256 over
   canonical normalized semantics (v4.2 invariant, unchanged).
2. **Controls wrap the core, never modify it.** `service.py` orders: bound → authn → admission → idempotency →
   version → entitlement → signed catalogue → policy merge → selection → resolve → fenced publish → audit.
3. **Catalogue is signed, scoped, monotonic data** (`PK_SIGNED_CATALOGUE/1`), cached for autonomy only under a
   GAP-04 lease; signatures are verified offline too.
4. **Fixed constraint precedence** with hard filters and soft rankers; contradictions refused.
5. **File-backed fenced store** as the reference source of truth; a production deployment MAY substitute a
   replicated store that preserves the same atomicity/fencing contract.
6. **Hash-chained, MAC'd audit ledger**; HMAC-SHA256 by default, Ed25519 when `cryptography` is present.
7. **Subset adapters** for OAM and WIT that refuse unsupported features.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Kubernetes CRDs + controllers as the model | Couples the plane to a runtime it explicitly does not own. |
| Full OAM/KubeVela runtime | Imports trait/workflow semantics the plane cannot enforce. |
| External WIT toolchain (wasm-tools) as the checker | Adds a non-Python dependency to the resolution path; retained as a future conformance oracle (MC-10 residual). |
| Database-backed store (SQLite/Postgres) | Viable for production; file store chosen as a dependency-free reference with the same contract. |
| Unsigned catalogue over mTLS only | Loses offline verifiability and poisoning resistance. |

## Consequences

- New invariants: fenced single-writer publication; no inline secrets; audit before success is returned.
- Operational obligations: key custody and rotation (catalogue/token/audit/artifact), lease issuance, store backups.
- Failure modes: stale catalogue → refusal (or degraded under lease); audit write failure → request fails.
- Migration: v4.2 callers of `resolve`/`resolve_document` are unaffected.

## Review triggers

New schema major; new trust boundary or key purpose; change to precedence order; replacement of the store;
any Critical/High security finding.

## Approval record

_None yet._ Approval requires signed entries (role, name, date, commit) appended here and mirrored in
`docs/governance/APPROVALS.json`. Until then the gate reports MC-02 as **BLOCKED_OWNER**.
