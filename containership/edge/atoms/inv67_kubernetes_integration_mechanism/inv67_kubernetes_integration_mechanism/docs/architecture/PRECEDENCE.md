# Constraint precedence (item 08)

Implemented in `plane/policy.py::resolve`, tested in `tests/unit/test_identity_authz_artifact.py::Precedence`.

1. **security** (authn/z, artifact trust, privileged refusal)
2. **residency / tenancy** (namespace binding, watch scope)
3. **safety** (freeze, quarantine)
4. **compatibility** (GAP-15 certification, version matrix)
5. **capacity** (quota, rate, overload)
6. **SLO**
7. **cost**
8. **user preference** (placement hints)

A `deny` at any level wins over every lower level; `defer` (e.g. quota) delays but never overrides a lower-level deny; unknown constraint levels or invalid verdicts deny. The controller pipeline order (`controller._sync`) follows this list.
