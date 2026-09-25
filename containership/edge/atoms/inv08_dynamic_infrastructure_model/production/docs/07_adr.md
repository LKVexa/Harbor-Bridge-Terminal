# ADR-0001: INV-08 dynamic infrastructure architecture

- **ID:** ADR-0001
- **Status:** PROPOSED (not accepted; approver UNASSIGNED)
- **Deciders:** service_owner UNASSIGNED, security_owner UNASSIGNED
- **Controls:** INV-08-C010 (ADR), C004 (source of truth), C011 (function)
- **Review triggers:** see "Consequences and review triggers"

## Template
Every ADR under `production/docs/` uses these sections, in order: ID, Status
(PROPOSED | ACCEPTED | SUPERSEDED by ADR-NNNN | REJECTED), Context, Decision,
Alternatives, State representation, Dependency inference and simulation,
Consequences and review triggers.  IDs are `ADR-NNNN`, never reused.

## Context
INV-08 must deliver "continuous infrastructure intent/control" for elastic
capacity.  The only executable artefact is `model.Pool`: a single-writer,
deterministic lease pool whose `tick(now, demand)` is a pure-transactional
reconciliation step (validate -> compute on copy -> commit).  The contract
declares PK_DYN_LEASE/1, PK_DYN_SCALE/1 and PK_DYN_COST/1 but no store, graph
engine or provider.

## Decision (proposed)
Adopt a **level-triggered reconciliation loop over an authoritative lease
table** (Kubernetes-controller style), with `Pool.tick` as the pure decision
function and the lease table as the only source of truth.  A live
infrastructure graph is an optional read model derived from the lease table,
never an authority.

## Alternatives
| Option | For | Against | Verdict |
|---|---|---|---|
| A. Reconciler + lease table (proposed) | matches existing `Pool.tick`; deterministic; easy to fence (component 58) | graph queries need a derived view | proposed |
| B. System Initiative style live graph as source of truth | rich dependency modelling, interactive change sets | external product dependency; graph mutation semantics not modelled by `Pool`; hard to fence per lease | rejected for v1, revisit |
| C. Static IaC plan/apply (INV-06) | mature tooling | not elastic; plan drift between runs; replaced by INV-08 for pools | rejected |
| D. Event-sourced digital twin as authority | full history, replay | projection lag; needs consensus log (component 10 BLOCKED) | deferred |

## State representation (digital-twin boundary)
- Authoritative: lease records `{node_id, expires, busy, revision, fence}` per tenant (LeaseTable in `production/concurrency.py`; tech BLOCKED, see 10).
- Derived (twin): pool snapshot (`Pool.snapshot()`), cost counters, optional graph view.  Twins may be stale; they MUST NOT drive reclaim.
- Out of twin: provider-side reality; reconciled by `backup.reconstruct` (leaked/lost classification).

## Dependency inference and simulation assumptions
- Dependencies are declared (topology.json), not inferred at runtime; inference is out of scope for v1.
- Simulation (`soak.py`, `rollout.py` SimFleet) assumes deterministic ticks, integer lease TTL, no clock skew beyond `now` monotonicity enforced by `Pool`.
- Demand signal (PLN-05) is trusted for magnitude only; bounds cap its effect.

## Consequences and review triggers
- Reversible: the decision function is isolated; swapping the authority (B/D) requires a new ADR and migration via `backup.migrate`.
- Irreversible-ish: lease schema fields become a compatibility surface (PK_DYN_LEASE/1).
- Review when: lease store technology is selected (10); a provider adapter lands; any SLO in contract.py is breached twice in a quarter; annually (governance.py `architecture_adr`, 365 days).
