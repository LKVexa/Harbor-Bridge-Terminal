# External estate gate runtime (`pk_core`) contract (MC-01)

| Item | Decision |
|---|---|
| Module / distribution | `pk_core` |
| Supported versions | `>=4.0.0,<5.0.0` (INV-36 side; **awaiting estate-owner confirmation**) |
| Semantic versioning | minor = additive symbols/fields; major = breaking; INV-36 raises its upper bound only after an integration run |
| Python ABI | CPython 3.11-3.13 |
| Classification | certification dependency (`[estate]` extra); never imported by the transport runtime |
| Boundary | `pkcore_adapter.py` is the only module that imports `pk_core` (enforced by `PkCoreAdapterTest.test_single_import_boundary`); `contract.py`/`component.py` obtain symbols through `pkcore_adapter.require()` |
| Required symbols | `pkcore_adapter.REQUIRED_SYMBOLS` (Contract, Dependency, Slo, ChecklistItem, Finding, Component with signatures, return types, side effects, exceptions) |
| Evidence schema | `pk_core.findings/1`; other revisions are rejected deterministically (`GATE_SCHEMA`) |
| Missing / incompatible | typed `GateUnavailable` (`GATE_UNAVAILABLE`); in certify mode the gate exits 2; it is never a PASS |
| Execution | subprocess with timeout (`GATE_TIMEOUT`), so a hung estate gate cannot deadlock the pipeline |
| Reproducibility | certification runs install `pk_core` from a hash-pinned artifact (`pip install --require-hashes`) in a clean venv with only declared dependencies; offline/hermetic path: pre-downloaded wheelhouse + `--no-index --find-links` |
| Owner / escalation | Post-Kubernetes estate maintainers (contact UNASSIGNED in `governance/owners.json`) -> INV-36 technical owner |

Command: `python -m inv36_control_transport.audit [--certify]` (exit codes in `gate.py`). Evidence: `evidence/<timestamp>/gate-evidence.json` (`schema/gate-evidence.schema.json`) + `.sha256` + raw logs, all made read-only; bound to the git source digest and, when supplied, the artifact digest (`--artifact-digest`). Environment fingerprint includes OS, kernel, arch, Python, `cryptography` + backend version, build backend and vsock capability.

Status: the adapter, fake-runtime tests (pass / fail / skip / malformed / short / wrong schema / crash / timeout), certify-mode negative test and golden evidence fixture exist. An integration run against the real `pk_core` has **not** happened - the package was not supplied.
