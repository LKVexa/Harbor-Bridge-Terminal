# INV-08 SHALL-level requirements (DRAFT)

Authoritative data: `production/requirements.json` (schema PK_DYN_REQUIREMENTS/1,
set version 1.0.0, approver UNASSIGNED).  Derived from `model.py` behaviour and
CHECKLIST.json C011-C015.  Every requirement has inputs, pre/postconditions,
code link and a behavioural test in `production/tests/test_govops.py::RequirementBehaviourTest`.

## State invariants (continuous intent/control)
- I1 `len(nodes) <= max_nodes` at all times after construction.
- I2 after a successful tick, `len(nodes) == max(target, busy_count)` with `busy_count <= max_nodes`.
- I3 no busy node is ever absent after a tick.
- I4 time watermark `now` is non-decreasing; failed ticks change nothing.

## Node lifecycle (C015)
ABSENT -> LEASED_IDLE (admission, lease = now+ttl) <-> LEASED_BUSY (set_busy);
LEASED_IDLE -> ABSENT (expiry or surplus).  LEASED_BUSY -> ABSENT is illegal.

## Result semantics (C014)
SUCCESS | PARTIAL | DEGRADED | RETRYABLE_FAILURE | TERMINAL_FAILURE |
OPERATOR_REQUIRED | BLOCKED (core.Outcome); `Pool.tick` itself is all-or-nothing:
success, or ValueError/PoolInvariantError/OverflowError with no mutation (terminal
for the same input).

## Requirement index
REQ-INV08-001..012 functional/semantic pool behaviour, 013 lifecycle, 014-016
nonfunctional (determinism, bounded work, multi-context), 017 outcome semantics,
018 single-writer concurrency.  See requirements.json for the full SHALL text.

## Change control
Ids are never reused.  Any change of an existing requirement's normative fields
bumps its integer `version` and the set `version` (minor: additions; major:
removal or semantic change).  `rtm.check_change_control(new, baseline)` rejects
violations; `baseline_digest` records the approved set digest.
