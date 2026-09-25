# Identity and trust boundaries (M06)

- Trusted identity = the five-tuple (tenant, environment, site, workload, component) **as signed by the trust root**, never caller-supplied names.
- Link key = identity five-tuple + link name. Same names in any other tuple element are a different link (`tests/security/test_identity_binding.py`).
- Link records persist the identity; a scope mismatch between record and caller increments `pk_isolation_violation` and is refused.
- Decisions (M08) and secret references (M09) are both bound to the same five-tuple.
- Trust boundaries: identity plane (issuer keys), policy plane (decision keys), INV-55 (secret values), backend (receives resolved secret only at call time).
