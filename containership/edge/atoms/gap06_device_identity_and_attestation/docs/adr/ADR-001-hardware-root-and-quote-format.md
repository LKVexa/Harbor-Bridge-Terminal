# ADR-001: TPM 2.0 quote as the primary hardware evidence format
Status: Proposed (not approved — no architecture owner assigned) · Date: 2026-09-22 · Supersedes: none

**Context.** v4.2.0 trusted a caller-supplied `hardware_identity` string (audit finding A-04). The checklist (MC-01) needs cryptographic evidence.
**Decision.** Verify `TPMS_ATTEST` (type `TPM_ST_ATTEST_QUOTE`) signed by an enrolled AK (`TPMT_SIGNATURE`, ECDSA P-256/P-384 or RSASSA/RSAPSS ≥2048), SHA-256 PCR bank only by default, crypto-agile TCG event log replay. TEE evidence goes through a `TeeAdapter` interface.
**Options considered.** (a) keep reference string binding — rejected, no authenticity; (b) adopt an external verifier (e.g. Keylime/Veraison) — deferred: not available in this environment and would need its own evaluation; (c) native parser over `cryptography` — chosen, because the parser can be fuzzed here and signature math stays in OpenSSL.
**Drivers.** p99 verify cost measured at ~12 ms end-to-end on 2 vCPU (`evidence/bench.json`); zero custom signature primitives.
**Consequences.** Real-hardware vectors are still required (blocked). SHA-1 banks need an expiring migration exception.
**Links.** THREAT_MODEL TH01, TH05, TH07, TH09 · `mc/tpm.py`, `mc/verifier.py` · `tests/test_mc_verifier.py`.
