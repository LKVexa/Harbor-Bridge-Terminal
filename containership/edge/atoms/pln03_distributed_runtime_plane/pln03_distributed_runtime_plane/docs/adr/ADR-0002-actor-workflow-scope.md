# ADR-0002 — Actor and workflow services are out of PLN-03 scope

- **Status:** Proposed — awaiting Architecture Board approval
- **Date:** 2026-09-23
- **Resolves (on approval):** MC-052 as an approved Not-Applicable decision

## Context
`CHECKLIST.json` names Dapr-style actor and workflow services in the source function, while `contract.py` lists "Durable workflow semantics" under *not owns* and "Durable multi-step workflow execution" under *non-goals*. The archive therefore contradicted itself.

## Decision (proposed)
PLN-03 provides no actor runtime and no durable workflow engine. Stateful single-writer patterns are expressible with `PK_STATE/1` transactions plus the fencing epochs in `durability.py`. Durable workflows belong to a separate element (to be named by the Architecture Board) that *consumes* PLN-03.

## Required follow-through on approval
- Amend the CHECKLIST source-function text (or record an approved exception) so the repository no longer claims actor/workflow services.
- Add the owning element to `OWNERS.yaml > boundaries`.

## Approval record
_Empty._
