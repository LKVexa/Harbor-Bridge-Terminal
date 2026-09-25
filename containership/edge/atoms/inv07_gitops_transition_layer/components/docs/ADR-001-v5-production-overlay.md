# ADR-001 — INV-07 v5.0.0 production overlay

**Status:** PROPOSED — needs a named engineering owner and an independent reviewer to become ACCEPTED (see `OWNERS.md`).
**Date:** 2026-09-22 · **Supersedes:** nothing · **Scope:** `components/` overlay on INV-07 v4.2.0

## Context

v4.2.0 was an in-memory reference model: HMAC "signatures", a Python dict as the live state, memory-only history, no transport, no authz. `MISSING_COMPONENTS.md` listed 54 gaps. The 54-component checklist (38 controls each, 2,052 total) asks for production closure.

## Decision

Build a stdlib-only production controller beside the untouched reference model:

| Concern | Decision | Rejected alternative (why) |
|---|---|---|
| Transport | system `git` ≥ 2.31 via argv subprocess against a pinned bare mirror | libgit2/pygit2 (native dep, no wheel on every target); GitPython (shells out anyway) |
| Commit trust | Ed25519 signature in the standard `gpgsig` header (PKED25519/1) verified in pure Python; OpenPGP lane via `git verify-commit --raw` | HMAC (symmetric: controller would hold the signing secret); SSH signatures (need `ssh-keygen` at runtime) |
| Provenance | DSSE/in-toto v1 statement in `refs/notes/provenance`, bound to commit **and** tree OID | provenance file inside the tree (a commit cannot contain its own digest) |
| Apply | plan → preflight dry-run → journalled intent → ordered effects → compensation; `PartialApply` freezes the target | fire-and-forget apply (no rollback boundary) |
| Concurrency | file lease with epoch = fencing token; target rejects lower epochs | leader flag only (split brain overwrites) |
| State | CRC-framed WAL + atomic checkpoint; ambiguous intents read back on start | SQLite (not allowed on the yard mount; more moving parts) |
| Target | `DirectoryTarget` (real, durable) + `KubernetesTarget` (server-side apply adapter) + Argo CD/Flux delegate adapters pinned to OIDs | cluster client libraries (not stdlib; need a cluster to test) |
| Policy | built-in bounded evaluator over signed, versioned bundles; OPA/CEL adapter slot | embedding OPA (binary dependency) |

## Control flow and trust boundaries

```
signer (dev key) ──signed commit──▶ Git remote ──fetch (pinned URL, fsck)──▶ controller mirror
builder key ──DSSE note──────────▶ refs/notes/provenance
                                       │
controller: time ▸ freeze ▸ lease ▸ fetch ▸ resolve ▸ signature ▸ ref policy ▸ freshness ▸ provenance
            ▸ parse ▸ tenancy ▸ policy ▸ live read ▸ drift ▸ plan ▸ preflight ▸ intent ▸ apply ▸ commit
                                       │ epoch-fenced writes
                                   target (INV-05 live control store / Kubernetes / directory)
```

Trust boundaries: (1) Git remote → controller (untrusted bytes until signature + provenance verify); (2) operator HTTP → controller (PKT1 tokens, RBAC, two-person rule); (3) controller → target (fencing + ownership + preconditions). The controller holds **no private signing keys**.

## Concurrency model

One reconcile at a time per instance (`Controller._run_lock`); one leader per tenant×site partition (lease); the target is the final arbiter via fencing. Lease TTL must exceed max inter-node clock skew (config `controller.lease_ttl_seconds` ≥ 5 s; `TimeAuthority` refuses skewed clocks).

## Deployment topology

One controller instance per tenant × site (the contract forbids a global singleton), two replicas for availability sharing one lease directory/Lease object. See `deploy/`.

## Consequences

* Pure-Python Ed25519 is correct (RFC 8032 vectors) but not constant-time → used for **verification of public data only** (W-002).
* Kubernetes/Argo/Flux adapters are unit-verified against recorded requests only; live-cluster acceptance is BLOCKED until a cluster is provided.
