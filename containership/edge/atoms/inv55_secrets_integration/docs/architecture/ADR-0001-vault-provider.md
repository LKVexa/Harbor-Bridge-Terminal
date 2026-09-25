# ADR-0001 — HashiCorp Vault KV v2 as the production secret provider

* **Status:** PROPOSED — not approved. Approver: UNASSIGNED (security) / UNASSIGNED (operations).
* **Date:** 2026-09-22 · **Supersedes:** none · **Review trigger:** provider, identity or deployment change; any Vault major release.

## Context
INV-55 does not own storage (`contract.py::not_owns`). It needs a provider that holds versioned secrets, supports check-and-set writes, version destroy, lease revocation, namespaces, and TLS/mTLS client authentication.

## Decision (proposed)
Use Vault **KV secrets engine v2** through the stdlib adapter `runtime/vault.py`, authenticated with **AppRole** (secret-id delivered by the platform) or a token file, over **TLS ≥ 1.2** with a pinned CA bundle and optional client certificate. All access goes through `SecretProvider`, so a different provider is an adapter, not a rewrite.

## Deployment mode
Vault cluster (integrated storage / Raft, ≥ 3 voters) per region; performance/DR replicas used only for **reads** via `FailoverProvider` (writes never fail over — split-brain rule R-RES-03). Auto-unseal via the platform KMS (outside INV-55's scope; see `docs/security/AT_REST.md`).

## Alternatives considered
| Option | Why not chosen (yet) |
|---|---|
| Cloud KMS-backed secret managers (AWS/Azure/GCP) | per-cloud adapters; kept possible via `SecretProvider` |
| Kubernetes Secrets | etcd at-rest encryption and RBAC granularity insufficient for per-secret scoping |
| In-house store | violates non-goal "storing secrets" |

## Trust boundaries
B2 (INV-55 → Vault) is authenticated both ways when mTLS is configured; the Vault token is a `_SecretValue` and never logged. Vault policy is least-privilege per tenant (`deploy/vault/policies/`).

## Version policy
See `docs/governance/COMPATIBILITY.md`. **No real Vault server version has been certified** — the adapter has been exercised only against the in-repo KV v2 wire double.

## Consequences
+ single adapter seam, testable offline; − production readiness depends on provisioning a real Vault and running `tests/` against it (W-001).
