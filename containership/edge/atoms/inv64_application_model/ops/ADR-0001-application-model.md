# ADR-0001 — Declarative application model aligned to OAM v0.3.0

- **Status:** PROPOSED (not approved — production certification is blocked until approved)
- **Date:** 2026-09-22
- **Deciders (required):** architecture-review-board, inv64-component-owner — *unassigned*
- **Supersedes:** none · **Superseded by:** none
- **Related:** SPECIFICATION.md, OAM_PROFILE.md, provenance/oam-baseline.json, MC-04, MC-11

## Context

Deployments in the Post-Kubernetes series need a single, validated description
of an application (components, providers, links, traits) that is refused
*before* anything runs when it is inconsistent, and that has one identity for
diffing, signing and audit. Adjacent layers own composition (INV-10),
deployment (INV-63), providers (INV-65) and guardrails (INV-66).

## Decision

1. INV-64 owns a declarative manifest (`app/v1`) and nothing that runs.
2. Topology is declarative (desired state), not imperative steps, so it can be validated statically, diffed and canonically hashed.
3. Concepts align to the **Open Application Model v0.3.0** (commit `3104d27a…`) at schema level for components/traits and conceptually for providers/links; INV-64 is not an OAM runtime and does not track later OAM/KubeVela features (policies, workflow).
4. Validation is fail-closed and aggregate; canonical identity exists only for valid manifests.
5. Security controls (authn, authz, secrets, audit, trust) are part of the INV-64 integration boundary (`service.py`), not deferred to callers — reversing the 4.2.0 position.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Adopt full OAM/KubeVela `Application` CRD as the native format | pulls in Kubernetes-specific semantics (namespaces, CRD lifecycle) the series is replacing; policies/workflow are execution concerns INV-64 must not own |
| Imperative deployment scripts | cannot be validated before running; no canonical identity |
| Helm/Kustomize-style templating | templating hides the effective topology; identity only after rendering |
| Leave security at the calling control plane (4.2.0) | every caller re-implements it; audit and tenancy gaps (4.2.0 audit) |

## Consequences

- + Pre-run refusal of dangling links/orphan traits; stable identity; OAM-literate users recognise the model; export/import to OAM Application.
- − Deviations from OAM (flattened traits, providers/links as annotations) need maintenance; each OAM baseline upgrade needs a new ADR.
- − Security at the boundary costs latency (REG-004), accepted per SPECIFICATION §10 precedence.

## Approval record

| Role | Name | Date | Decision |
|---|---|---|---|
| architecture-review-board | | | |
| inv64-component-owner | | | |

When approved: set `status` to `approved` and fill `approvers` in `ops/decisions.json`.
