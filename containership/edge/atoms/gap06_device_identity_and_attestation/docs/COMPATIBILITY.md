# Compatibility matrix (MC-28) — v5.0.0

| Cell | Status | Evidence |
|---|---|---|
| TPM 2.0 quote, SHA-256 bank, ECDSA P-256 AK | format verified against **software-simulated** vectors | `tests/test_mc_verifier.py` |
| TPM 2.0 quote, ECDSA P-384 / RSASSA / RSAPSS AK | code path present, **no vectors** | — |
| SHA-384/512 PCR banks | parser accepts; verifier default policy selects SHA-256 only | — |
| SHA-1 PCR bank / TPM 1.2 | **unsupported** (SHA-1 needs an expiring migration exception) | `AlgorithmAgilityTest` |
| Firmware TPM (Intel PTT, AMD fTPM), discrete TPM vendors | **untested — no hardware** | — |
| vTPM (swtpm, Hyper-V, GCP shielded VM, Nitro) | **untested**; host-binding evidence not implemented | — |
| TEE: generic signed JSON report | verified with simulated vendor key | `TeeAdapterTest` |
| AMD SEV-SNP, Intel TDX, Arm CCA | **unsupported** | — |
| TCG crypto-agile event log (Spec ID Event03) | parser + replay; data-binding for EV_IPL/EV_S_CRTM_VERSION | `EventLogTest` |
| IMA ASCII list, `ima-ng` template | supported; `ima-sig`/`ima` rejected by default | `VerifierTest.test_ima` |
| Wire schemas | `PK_*/1` only; a `/1` server rejects `/2` | `ErrorsSchemasTest.test_schemas` |
| Python | 3.11 tested (3.11.15); `-O` tested | `evidence/test_results.json` |
| OS / arch | Linux x86_64 tested only | `evidence/bench.json` |

Deprecation rule: removing a supported cell requires one minor release of notice and a gate entry.
