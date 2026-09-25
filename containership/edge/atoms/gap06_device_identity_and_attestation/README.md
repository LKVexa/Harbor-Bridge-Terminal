# GAP-06 - Device identity and attestation

**Version:** 5.0.0 (see `CHANGELOG.md`)  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Audit status:** hardened reference implementation plus missing-components pass; **not** authorised for production trust decisions (`governance/PRODUCTION_GATE.json`: NO_GO)

Device identity and attestation is where trust starts. A node proves what it is with challenge-bound evidence, the evidence is checked against an accepted measurement set, and the resulting verdict expires so trust must be continuously re-earned.

## Responsibility

Own node identity and the attestation lifecycle: enroll each node, bind hardware-capable nodes to a known hardware identity, issue unpredictable expiring challenges, verify canonical evidence against the accepted measurement set, quarantine measurement drift, and expire verdicts.

## v5.0.0 — missing components

`mc/` implements the 54 components of `governance/GAP06_Missing_Components_Professional_Checklist_v1.0.0.md` as far as this environment allows. Item-by-item status with re-verified evidence: `CHECKLIST_STATUS.md` (and `docs/CHECKLIST_ANNOTATED.md`). Start with `docs/MASTER.md` (reconstructed), `docs/THREAT_MODEL.md` and `docs/RUNBOOKS.md`. Requires `cryptography==46.0.7` (`requirements.lock`).

Regenerate all evidence: `python -B -m gap06_device_identity_and_attestation.tools.release`

## v4.2.0 reference core (unchanged)

`attestation.py` now provides a standard-library-only trust core with:

- explicit enrollment and revocation;
- 256-bit cryptographically random challenge nonces;
- node-bound, expiring, single-use challenges;
- replay detection and cross-node challenge protection;
- canonical and bounded evidence validation;
- accepted-measurement validation and version tagging;
- fail-closed quarantine for bound evidence that drifts from policy;
- hardware-level trust only when evidence names the node's enrolled hardware identity;
- verdict expiry and logical-clock rollback rejection;
- immutable evidence/verdict value objects;
- thread-safe state mutation and bounded outstanding challenges.

The `hardware_identity` check is intentionally only a **reference binding**. It is not cryptographic proof of a TPM/TEE quote. Production quote/certificate verification remains a P0 missing component; see `MISSING_COMPONENTS.md`.

## Owns

- Node identity enrollment and revocation
- Node identity binding to a hardware identity record
- Attestation challenge lifecycle
- Attestation evidence verification
- Accepted measurement set and version tagging
- Attestation verdict expiry
- Quarantine of nodes whose bound evidence drifts

## Explicitly does not own

- Capability probing
- Artifact signing
- Policy authorship
- General node lifecycle
- Grant issuance

## Interfaces

The architectural contract names these interfaces:

- `attest` - `PK_ATTESTATION/1`
- `enrol` - `PK_NODE_IDENTITY/1`
- `measurements` - `PK_ACCEPTED_MEASUREMENTS/1`

Typed external schemas/transport bindings for those interfaces are **not included** in this archive and remain tracked in `MISSING_COMPONENTS.md`.

## Service-level objectives

- **verdict soundness** - zero attested verdicts for measurements outside the accepted set (no error budget)
- **replay resistance** - zero verdicts issued for evidence reusing a spent nonce (no error budget)
- **re-attestation** - 99.9% of nodes re-attest before verdict expiry (0.1% may fall to untrusted and be cordoned)

## Running tests

From the directory containing this package:

```text
python -m unittest discover -s gap06_device_identity_and_attestation/tests -p "test_*.py" -v
python -O -m unittest discover -s gap06_device_identity_and_attestation/tests -p "test_attestation.py" -v
```

The v4.2.0 security-core tests require only the Python standard library; the v5.0.0 `test_mc_*` tests require `cryptography`. The framework conformance tests additionally require `pk_core`; set `PK_CORE_PATH` if that framework lives elsewhere.

When `pk_core` is available, the intended framework commands are:

```text
python -m pk_core list
python -m pk_core run GAP-06 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-06 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** enroll nodes, publish an accepted measurement-set version, run the component checks, and archive evidence as a baseline.
- **Day 1:** gate deployment on conformance and verify that identity/measurement policy provenance is approved.
- **Day 2:** re-attest before verdict expiry, monitor quarantine/replay signals, rotate policy safely, and verify evidence continuity.

A complete production runbook, external schemas, persistence layer, real hardware quote verifier, telemetry pipeline, HA design, and operational gate artifacts are still missing. See `MISSING_COMPONENTS.md`.

## Archive note

The original `MASTER.md` was never in any supplied archive. `docs/MASTER.md` is a reconstruction from the implemented code and is labelled as such.
