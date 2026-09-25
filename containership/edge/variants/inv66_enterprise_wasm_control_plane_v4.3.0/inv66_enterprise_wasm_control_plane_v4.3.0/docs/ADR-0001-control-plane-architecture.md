# ADR-0001 — INV-66 enterprise control plane above wasmCloud lattices

| Field | Value |
|---|---|
| ID | ADR-0001 (INV-66) |
| Status | **Proposed** — awaiting architecture-board approval (see sign-off table) |
| Version | 1.0.0 (2026-09-22) |
| Supersedes | none |
| Related controls | C010, C001–C008; MC-002 |

## Context

INV-66 governs many wasmCloud lattices for many teams: who may deploy where, which registries and signers are acceptable, and an append-only record of every change. A single lattice's own controls (host labels, link policies) are per-lattice and do not give an organisation-wide admission point or a unified audit trail. The Post-Kubernetes series contract (`contract.py`) fixes the responsibilities; this ADR records *how*.

## Decision

1. **Admission-gate architecture.** INV-66 is a stateless-API / single-writer-journal service placed *in front of* every INV-63 deployment manager. INV-63 accepts manifests only from INV-66 (mTLS identity), so the guardrail cannot be bypassed.
2. **Technology.** Python ≥ 3.11 standard library for the service, `cryptography` for Ed25519; no web framework (smaller attack surface, reviewable). The wasmCloud/Cosmonic Control runtime is *not* embedded: INV-66 speaks to INV-63 over HTTPS JSON (`adapters.HttpDeploymentManager`), keeping lattice runtime, reconciliation and signing keys out of scope (contract "does not own").
3. **Source of truth = hash-chained journal** (`store.py`). State is a pure reduction of journal entries; every mutation is fsync-journalled before it takes effect; chain heads are HMAC-anchored to an external WORM sink.
4. **Identity is federated, never local.** Bearer tokens from configured issuers (EdDSA/HS256, audience/issuer/lifetime/jti checks, optional mTLS binding). OIDC/SAML is terminated at the IdP.
5. **Policy is layered.** Local RBAC capability model (deny-wins) + provenance verification + external GAP-13 policy engine, evaluated in the fixed order in `CONSTRAINT_PRECEDENCE.md`, failing closed.
6. **HA model: single leader per site-store, fenced by lease epochs.** Warm standbys take over after lease expiry; replication of the store directory is delegated to the storage layer (synchronous replicated volume) — see TOPOLOGY.md. Multi-leader consensus (Raft) was deferred; see alternatives.

## Alternatives considered

| Option | Why not chosen now |
|---|---|
| Cosmonic Control / wasmCloud policy service as the control plane | Per-lattice scope; no cross-lattice RBAC/audit; ties governance to runtime vendor. May be adopted as an INV-63-side enforcement point later. |
| Kubernetes admission webhooks (OPA Gatekeeper/Kyverno) | Series premise is post-Kubernetes; would reintroduce a cluster dependency. |
| Embedded Raft (e.g. etcd) for state | Strong fit for HA, but adds an operational dependency and cannot be verified inside this archive; revisit when MC-039 multi-site is funded (waiver W-006). |
| Relational DB (PostgreSQL) as store | Good durability/query; rejected for v4.3 to keep the audit chain self-verifying and dependency-free. The `JournalStore` interface allows a DB-backed implementation later. |
| Trusting signer *names* in manifests (v4.2 behaviour) | Spoofable; replaced by Ed25519 verification over the pinned digest. |

## Constraints and consequences

* Throughput is bounded by a single writer (~400–500 fsync'd admissions/s on the reference host; see `CAPACITY.md`). Scale-out is per site/environment, not per request.
* Loss of the policy engine, store or identity issuer blocks admissions (fail closed) — an explicit availability-for-safety trade (`OFFLINE_SEMANTICS.md`).
* Operators must run an external WORM anchor sink; without it, an attacker with write access to the store could recompute the chain undetected.

## Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Accountable service owner | *pending — see OWNERSHIP.md* | | |
| Security architecture | *pending* | | |
| Platform architecture board | *pending* | | |

Review cadence: on every major version and at least annually (REVIEWS.md).
