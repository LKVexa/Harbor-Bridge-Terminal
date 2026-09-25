# Third-party and reused material

| Component | Source | Licence | Modified |
|---|---|---|---|
| `_vendor/pk_core/` | owner's PK framework, `New folder\PK_Master_Applied_All_Batches.zip :: UC270/pk_core` (identical in 4 copies) | owner's material, no licence file | no (digests in `_vendor/PK_CORE_PROVENANCE.json`) |
| `MASTER.md` | owner's `PK_Master_Applied_All_Batches.zip :: UC270/pk_components/inv27_unikernel_execution/MASTER.md` | owner's material | no |
| `trust/ed25519.py` | owner's INV-60 v4.3.0 (`fabric/ed25519.py`), written from RFC 8032 | owner's material | no |
| `audit.py`, `redaction.py`, `resilience.py`, `telemetry.py` | owner's INV-72 v4.3.0 remediated | owner's material | renamed codes/metrics (ACCEL→UK) |
| `tools/_refs.py`, `tools/rtm.py`, `tools/release_gate.py`, `tools/manifest.py`, `tools/pk_gate.py` | patterns from owner's INV-72 v4.3.0 | owner's material | rewritten for MC registry |
| RFC 8032 test vector | IETF RFC 8032 §7.1 | IETF Trust (code components under Revised BSD) | quoted |

No third-party open-source code is copied. `cryptography` is an optional runtime dependency
(Apache-2.0 OR BSD-3-Clause) and is not vendored.
