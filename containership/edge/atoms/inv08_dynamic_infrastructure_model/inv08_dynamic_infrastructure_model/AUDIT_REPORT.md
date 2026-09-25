# INV-08 Dynamic Infrastructure Model - Audit Report

**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Audit date:** 2026-09-22  
**Method:** static archive inspection, syntax validation, dependency-independent
unit testing, adversarial input tests, documentation/evidence consistency review.
No untrusted project code was executed before inspection.

## Executive result

The 4.1.0 archive contained a useful bounded elastic-pool reference model, but it
had three material assurance problems:

1. The main conformance test class was skipped when `pk_core` was unavailable,
   including the version test, so a local test run could show only skips while
   providing little package-local assurance.
2. The package claimed/strongly implied all 100 production requirements were
   satisfied even though the ZIP did not contain the majority of artifacts and
   integrations required by its own checklist.
3. The pool accepted several malformed or pathological state/input conditions
   that could produce exceptions, ambiguous accounting, or unsafe state mutation
   in a real control loop.

Version 4.2.0 fixes the package-local defects and makes missing production
components explicit. It should be treated as a hardened reference component, not
as a complete production dynamic-infrastructure control plane.

## Findings fixed in 4.2.0

### A-01 - Conformance dependency could hide lack of executable evidence - HIGH

**Problem:** `@unittest.skipIf(pk_core is None, ...)` wrapped the entire original
`ConformanceTest`, including basic version checks. With no `pk_core` present, the
suite could skip every meaningful test.

**Fix:** model/version tests now always run. Only the actual `pk_core` integration
class is skipped. `preflight.py` is strict by default and fails when `pk_core`
cannot be imported; standalone-only verification must be explicitly requested.

### A-02 - README referenced a nonexistent `MASTER.md` - MEDIUM

**Problem:** the 4.1.0 README stated that `MASTER.md` was carried in the package,
but the archive contained no such file.

**Fix:** removed the inaccurate statement and recorded the corpus as an external/
missing component if it is still expected as part of the deliverable.

### A-03 - Production-readiness evidence was overstated - HIGH

**Problem:** comments/changelog language said all 100 requirements were satisfied,
while the archive itself lacked wire schemas, authn/authz, durable state,
provider integrations, telemetry, deployment automation, certification evidence,
and many other artifacts explicitly required by `CHECKLIST.json`.

**Fix:** documentation now distinguishes contract declarations from implemented
and executable evidence. Added `MISSING_COMPONENTS.md` with 66 explicit gaps.

### A-04 - Non-finite time/demand values were insufficiently guarded - HIGH

**Problem:** 4.1.0 rejected negative/NaN demand but still permitted positive
infinity to reach `math.ceil()`, and `now` had no validation.

**Fix:** reject NaN/Inf/boolean time and demand; reject negative demand; detect
non-finite arithmetic.

### A-05 - Python booleans could pass integer configuration validation - MEDIUM

**Problem:** `isinstance(True, int)` is true, so boolean values could be accepted
as `min_nodes`, `max_nodes`, `per_node`, or `lease_ttl`.

**Fix:** integer validators explicitly reject bool.

### A-06 - Restored/public node state was not validated - HIGH

**Problem:** callers could mutate the public `nodes` mapping into malformed state,
leading to type errors or invalid lease decisions during `tick()`.

**Fix:** every tick validates node IDs, lease expiry, busy flags, pool cardinality,
and required state keys before mutation.

### A-07 - Decision mutation was not transactional - HIGH

**Problem:** the original implementation directly renewed/reclaimed nodes while a
decision was executing. A later exception could theoretically leave a partially
modified pool.

**Fix:** decisions are calculated against a detached copy and committed only when
all validation, lease arithmetic, scaling, and accounting succeeds.

### A-08 - Restored node IDs could force collision/scan behavior - MEDIUM

**Problem:** `_n` was independent of restored `node-N` IDs. Allocation could
revisit already-used IDs until it eventually found a free suffix.

**Fix:** initialization and allocation synchronize against the highest observed
generated suffix and explicitly skip collisions.

### A-09 - Time regression semantics were undefined - HIGH

**Problem:** a controller clock moving backward could silently alter lease-expiry
behavior.

**Fix:** a pool remembers the last accepted `now` and fails closed on regression.
A production implementation should still use a defined monotonic/distributed time
strategy; that remains a missing component.

### A-10 - `node_hours` assumed one hour per tick without an explicit interval - MEDIUM

**Problem:** accounting incremented by current node count per decision, even though
there was no statement that a tick represented an hour.

**Fix:** `tick(..., elapsed_hours=1.0)` makes the interval explicit while preserving
4.1.0 behavior by default.

### A-11 - Core state machine was unnecessarily coupled to `pk_core` - MEDIUM

**Problem:** importing the package eagerly imported `component.py`/`contract.py`,
preventing reference-model use or testing when `pk_core` was absent.

**Fix:** moved pool logic to dependency-free `model.py`, moved constants to
`metadata.py`, and lazy-loads the conformance adapter/contract.

## Verification performed

The 4.2.0 verification run checks:

- all Python files parse/compile;
- package version and `VERSION` agree;
- checklist declares and contains 100 unique checks;
- standalone pool unit tests pass without `pk_core`;
- extreme integer demand remains bounded without huge-number ceiling work;
- NaN/Inf/boolean/negative input rejection;
- hard bounds and busy-node safe reclaim;
- expired pool recovery to `min_nodes`;
- malformed restored state fails closed;
- time regression is rejected without mutation;
- restored generated IDs do not collide;
- explicit node-hour interval accounting;
- strict preflight detects missing `pk_core` rather than treating it as success.

## Residual risk

The archive still does not implement the distributed, authenticated, durable,
observable, provider-integrated control plane described by many of its checklist
requirements. Those are not cosmetic gaps: they are prerequisites for production
operation and are enumerated in `MISSING_COMPONENTS.md`.
