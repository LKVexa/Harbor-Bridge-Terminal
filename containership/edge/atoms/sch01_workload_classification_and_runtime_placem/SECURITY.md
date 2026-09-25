# SCH-01 Security Notes - 4.2.0

## Implemented defensive behavior

- Canonical classification is re-derived before candidate evaluation; a caller cannot weaken trust by editing a classification dictionary.
- Unknown provenance, malformed identifiers, unsupported tiers, invalid capacity, invalid clocks, duplicate node names, and invalid lease durations fail closed.
- Future-dated and stale reports are excluded.
- Cross-tenant co-location is denied because current occupancy metadata cannot prove same-tier/same-trust isolation safety.
- Refusal diagnostics aggregate rejection counts and do not expose the candidate node names.
- The core engine performs no filesystem or network access.

## Required external controls not present in this archive

- Authenticated and integrity-protected node reports
- Artifact/policy signature and digest verification
- Authorization/capability checks on callers
- Managed encryption and key rotation at transport/storage boundaries
- Tamper-evident security audit event emission
- Distributed fencing/lease ownership
- Execution-tier enforcement and post-expiry reclamation
- Security fuzzing and adversarial test suites covering spoofing, replay, injection, resource exhaustion, and side channels

These are reported as missing components rather than silently treated as satisfied by the local algorithm.
