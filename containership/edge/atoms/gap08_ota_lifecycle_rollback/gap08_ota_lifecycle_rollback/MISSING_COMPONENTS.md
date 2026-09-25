# GAP-08 v4.3.0 — Missing Components (after build-out)

The v4.2.0 register listed 40 missing components. v4.3.0 implements all 40 in-package as reference implementations, contracts, tooling or governance templates. What is still missing is what code in this package cannot supply. Full item-level status: `docs/CHECKLIST_STATUS.md`.

## Still required before production

1. **Named owners** for service, architecture, on-call, security, release, vulnerability response and waivers (`docs/OWNERS.md`), and approval of `docs/ADR-0001-control-plane.md`.
2. **Production crypto:** per-trust-domain asymmetric keys (HSM/KMS) replacing the HMAC `KeyRing` stand-in; mTLS/workload identity on every RPC; encryption at rest for the state store.
3. **Production backends** meeting the executable contracts: GAP-05 `StateStore` (linearizable CAS + fence floor), a distributed lease service, a real WORM/transparency-log audit service, durable replay caches.
4. **Real sibling services verified end-to-end in staging:** GAP-01 supervisor (dedup, fence floor, tombstones, signed acks), GAP-06 attestation, GAP-07 verification, GAP-09 evidence, GAP-15 per-node certification, topology discovery.
5. **Config wiring:** controller gate/blast-radius/lease thresholds read from signed `ConfigStore` revisions instead of constructor arguments.
6. **Hardware power-loss certification** per supported board/storage/bootloader (simulation passes).
7. **Long runs:** days/weeks wall-clock soak; fleet-scale benchmarks on production-class hardware with regression detection.
8. **Human drills and reviews:** independent security review of `docs/THREAT_MODEL.md`; operator drills of `docs/RUNBOOKS.md` (freeze propagation, DR, quarantine recovery, explain-view reconstruction); vulnerability tabletop.
9. **Hosted CI** running `tools/ci.sh` plus secret and runtime-image scanning; signed evidence bundle.
10. **pk_core conformance** rerun (`tests/test_component.py`) in the full framework.

## Deliberately outside GAP-08

Building/signing bundles, measuring health, node lifecycle mechanics, runtime certification decisions and topology discovery remain owned by GAP-07, GAP-09, GAP-01, GAP-15 and the discovery services. GAP-08 defines and tests what it consumes from each (`docs/INTEGRATION_CONTRACTS.md`).
