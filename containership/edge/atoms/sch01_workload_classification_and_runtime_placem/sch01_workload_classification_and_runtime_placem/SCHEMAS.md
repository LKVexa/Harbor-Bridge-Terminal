# SCH-01 Interface Schemas (implementation reference)

This file documents the concrete in-process payloads emitted by version 4.2.0. It is not a substitute for a separately governed JSON Schema/Protobuf/WIT contract; formal schema artifacts remain a post-audit gap.

## PK_WORKLOAD_CLASS/1

Produced by `classify()`:

- `schema`: literal `PK_WORKLOAD_CLASS/1`
- `workload`: workload name
- `trust_class`: `trusted | first-party | third-party | untrusted | hostile`
- `required_tier`: `process | wasm | unikernel | microvm | vm`
- `latency_class`: `interactive | batch`
- `hardware`: sorted list of required capability names

Canonical provenance mapping in 4.2.0:

- `internal` -> `trusted` -> `process`
- `first-party` -> `first-party` -> `wasm`
- `partner` -> `third-party` -> `unikernel`
- `public` -> `untrusted` -> `microvm`
- `quarantined` -> `hostile` -> `vm`

## PK_PLACEMENT/1

Produced by `place()`:

- `schema`: literal `PK_PLACEMENT/1`
- `workload`, `tenant`, `node`, `site`
- `tier`, `trust_class`
- `lease_issued_at`, `lease_expires`
- `candidates_total`, `candidates_considered`
- `decision.strategy`: `weakest-sufficient-tier/most-free-slots/name`
- `decision.score`: deterministic score tuple serialized as a list

## PK_SCHEDULER_ERROR/1

Produced by `Unplaceable.as_dict()`:

- `schema`: literal `PK_SCHEDULER_ERROR/1`
- `code`: stable refusal code
- `message`: human-readable summary
- `details`: aggregate safe-to-surface diagnostic fields

Current refusal codes:

- `UNKNOWN_PROVENANCE`
- `DUPLICATE_LEASE`
- `NO_CANDIDATE`

Candidate rejection codes used in `NO_CANDIDATE.details.rejection_counts`:

- `THERMALLY_EXCLUDED`
- `NO_FREE_SLOTS`
- `REPORT_FROM_FUTURE`
- `STALE_REPORT`
- `SITE_MISMATCH`
- `MISSING_CAPABILITY`
- `INSUFFICIENT_TIER`
- `TENANT_ISOLATION`

`ValueError`/`TypeError` are still used for programmer/configuration errors. A single governed error envelope for all public boundaries remains missing.
