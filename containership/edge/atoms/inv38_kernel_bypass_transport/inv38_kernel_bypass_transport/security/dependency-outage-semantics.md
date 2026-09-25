# Dependency-outage safe mode (INV-38-C048)

Independent outage handling for identity, attestation, policy, key and time
(`security/fail-safe-matrix.yaml`, `failsafe.py`). Cached policy may be used
within a bounded age; expired key material is never used; the privileged fast
path does not resume until identity/policy/key/time are refreshed in the defined
order. Degraded reason + dependency age are exposed in status without leaking
secrets. Fault-injection tests in `tests/test_failsafe.py`. **Status:**
`IN_PROGRESS` — live KMS/attestation/time services required for full evidence.
