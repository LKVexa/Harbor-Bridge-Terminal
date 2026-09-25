# INV-23 Repository Audit Report — 5.0.0

## Scope
This pass executes `INV23_Missing_Components_Remediation_Checklist.md` (MC-01…MC-14 plus the
cross-cutting and Final Production-GO lists) against the 4.2.0 audited archive. It was a
junkyard chop-shop overhaul in degraded mode: the yard office has no map, ledger or context
graph installed, so no donor cars were searched. The previous 4.2.0 report is kept in
CHANGELOG.md.

## Result
| Axis | 4.2.0 | 5.0.0 |
|---|---|---|
| Files | 10 | 134 in total: 34 source modules, 12 test modules, the vendored pk_core, schemas, docs and workflows |
| Tests | 6 standalone, with conformance skipped | **88 tests. All pass under `python` and `python -O`.** 1 skip is environmental (running as root). 5,000-example fuzz run is green. |
| pk_core conformance | not runnable | **100/100 satisfied, pk_core gate GO.** Uses vendored pk_core 4.0.0 (SHA-256 pinned). Also passes under `-O`, from outside the repo root, and from the installed wheel. |
| Wheel | none | Builds reproducibly (two builds give identical sha256). Installs into a clean venv, and its suites pass there. |
| Probe p99 | none | 0.67 ms on the sandbox guest. SLO < 50 ms passes, but the machine is unclassified. |
| Production gate (`tools/gate.py`) | none | **NO_GO (exit 3), which is the honest result.** Two blockers remain: no usable-host hardware evidence, and no license. Evidence verifies intact, and tampering is detected. |

## Work-package status
Statuses: **done** means implemented, tested and evidenced here. **partial** means implemented, but some items need an environment or a decision this pass could not supply. **open** means not possible here.

| MC | Status | What closed it | What remains |
|---|---|---|---|
| 01 pk_core | **done** | `pkcore_compat.py` handles precedence, API/version checks, shadow rejection and release hard-fail. pk_core 4.0.0 is vendored and pinned, and was identical in 4 source copies. Preflight, smoke, 100/100, `-O`, out-of-root and installed-wheel runs all pass. Resolution evidence is written into the gate. | Windows path-layout install is covered only by the CI matrix, which has not run here. |
| 02 MASTER.md | **done** | Restored verbatim from `PK_Master_Applied_All_Batches.zip` (UC270). Its sha256 and provenance are recorded. The test checks 100 section IDs 1:1 against CHECKLIST.json, plus no BOM, LF endings and no truncation. It is packaged, and marked provenance-only. | — |
| 03 host probe | **partial** | Linux KVM, Windows WHPX and macOS HVF backends. Adds an `indeterminate` state (schema /2), 14 reason codes, timeout, TTL cache and invalidation. Exceptions never become `usable`. Nested depth is never fabricated. Every branch is unit-tested with mocks, and a real probe ran on this host (row LNX-GUEST-NOVT). | Tests on Intel, AMD, bare-metal, nested, firmware-disabled, Windows and macOS hardware. No native CPUID helper is shipped; that is a deliberate choice, recorded in the threat model as T14. |
| 04 cross-process claim | **partial** | `ClaimProvider` has memory, POSIX `flock` and Windows `msvcrt` implementations. Tokens are 256-bit and only their hash is stored at rest. Acquire and release are atomic. Tested with 12 processes × 25 rounds (exactly one winner each round), unauthorised and stale release, and tampering. | The Windows and macOS providers have not run on those OSes. Separate-UID and service-vs-user scenarios are untested. |
| 05 leases / fencing | **done** (POSIX) | Durable record, fencing generation floor file, and leases. Liveness uses PID + start time + boot id. Stale takeover keeps history. Corrupt state fails closed, and `repair()` recovers it. Tested with SIGKILL, pause beyond the lease, PID reuse, reboot, partial write, impossible records and a clock jump. | Suspend/resume and real reboot need lab hosts. |
| 06 schemas | **done** | 6 normative JSON Schemas with a stdlib validator and semantic invariants. 25 fixtures, cross-checked with `jsonschema`. Versioning rules and a changelog are in place. Runtime outputs are validated, and the schemas are packaged. | — |
| 07 telemetry | **done** | 11 metrics, 9 event IDs and 4 spans. Labels are bounded, secrets are redacted, exporter failures are isolated, and a diagnostic snapshot is available (`inv23-probe --status`). There is an optional OTel sink. | OTel sink not exercised (package unavailable here). |
| 08 SLO | **partial** | Benchmark with nearest-rank p99, baselines, regression and noise exit codes, and waiver handling. Wired into the gate. | Needs runs on qualified Intel, AMD, Windows and macOS hosts (WVR-002). |
| 09 matrix | **partial** | `compatibility.json` has 18 rows and generates `COMPATIBILITY.md`, which the tests check is fresh. Row IDs are tagged in the hardware workflow. | 1 of 18 rows is verified. The rest need lab runners (WVR-001). |
| 10 property / fuzz | **done** | Covers the constructor, a stateful model, ownership, schema mutation and backend evidence fuzzing. Uses a seeded stdlib generator, plus a Hypothesis layer that CI runs. | — |
| 11 lifecycle | **partial** | Real processes: contention, SIGKILL, restart, tampering. Fault injection covers device loss, revoked permission, timeout, clock jump and telemetry failure. The adjacent-layer admission contract is in `admission.py`. | Host reboot, firmware toggling, L1/L2 nesting, read-only and disk-full runs as non-root, and the real GAP-02, INV-24, INV-40 and INV-43 packages. |
| 12 build / CI | **partial** | pyproject, reproducible wheel, clean-venv install tests, ruff and ruff-format, mypy (clean), version check, SBOM (CycloneDX 1.5), provenance (in-toto/SLSA shape), and ci, hardware and release workflows. | The workflows have never run on GitHub. `pip-audit`, gitleaks and `build` could not run here (PyPI blocked). |
| 13 governance | **partial** | SECURITY, SUPPORT, THREAT_MODEL (20 threats × 8 fields, plus trust boundaries), CODEOWNERS, incident runbook and waiver ledger with validator. | **License is undetermined, and deliberately not invented** (WVR-003). Independent security review is still needed. |
| 14 gate evidence | **done** (unsigned) | `tools/gate.py` produces evidence that is hash-chained to the previous head and checksummed. `tools/verify_evidence.py` checks every listed item. A manual tamper check (editing the verdict to GO) was detected. | No signing infrastructure yet (WVR-004). |

## Defects found during this pass
- **The 4.2.0 contract overclaimed.** It described "exclusivity of the KVM-equivalent device", but `/dev/kvm`, WHPX and HVF are not exclusive. It has been restated as a project slot.
- **The generation floor was not checked on validate.** A tampered generation file went undetected until the next acquire. It is now checked on every read.
- **A test-design finding confirmed recovery works as intended.** When a contender's winner exited early, the next contender legitimately took over the dead owner's claim. The multiprocess test now keeps winners alive.

## Honest gate position
`conformance/PK_GATE_RESULTS.json` says **NO_GO**, and `certifiable=false`. pk_core's own gate says GO for 100/100. That only shows the answers conform to the declarations: the reference assessment still exercises the legacy in-process model for a handful of findings. Production GO needs the open items in the work order.
