# Authentication (INV-38-C023)

Trust boundaries: workload→INV-38, control-plane→INV-38, peer↔peer,
provider→INV-38, artifact-loader→runtime. Principals, credentials, trust roots,
rotation and clock-skew are in `security/trust-roots.yaml`; model enforcement in
`authz.py`. Mutual authentication is required for remote peers; unauthenticated
downgrade/fallback paths are prohibited (C023-T05). Authentication failures yield
non-secret reason codes and allocate no privileged resource (C023-T08). Negative
tests in `tests/test_authz.py`. **Status:** `IN_PROGRESS` — real credential/trust
root integration needs an identity service.
