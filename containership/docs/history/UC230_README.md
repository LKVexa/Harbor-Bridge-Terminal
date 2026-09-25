# Unikernel Containership — UC-2.3.0

**Development foundation release applied to UC-2.2.0 using the attached 96,000-task series.**

This is still a trusted-local Python control plane over the delivered native VM engines and hull. It is not a bootable guest, hypervisor boundary, authenticated multi-tenant service, or fully executed 96,000-task platform. The source task pack is preserved byte-for-byte under `workflow/series.zip`; the separate application ledger records all task IDs and the limited implementation scope.

## Start in a new workspace

Extract this release to a new short directory, such as `D:\UC230`; keep the previous workspace and your own edits. This is a full-source package, not an in-place installer. No Python packages, toolchains, hypervisor, registry setting or execution-policy change is silently installed.

```bat
cd /d D:\UC230
python -X utf8 -B uc.py --version
DOCTOR.cmd
SELFTEST.cmd
python -X utf8 -B uc.py workflow check
BUILD.cmd
VERIFY.cmd
RUN.cmd vm_small --sealed
python -X utf8 -B uc.py lifecycle vm_small
```

Python, Pillow, and the native toolchains remain prerequisites. `py -3 -X utf8 -B uc.py ...` is an alternative where the Python Launcher is configured. The observed qualification host for this release is Linux x86-64 with CPython 3.13.5; Windows and macOS were not executed.

## New executable behavior

Strict ship-owned JSON readers reject duplicate keys, excessive nesting, nonfinite numbers and incompatible new contracts. A local SQLite control store tracks workload UUIDs, monotonic generations and operation outcomes. Protected CLI mutations prepare verified snapshots of managed berth/registry/seal/studio files before running, retain pending journals after abrupt termination, and expose explicit pending-recovery commands. Stronger requested isolation refuses instead of falling back. New graph/object tools validate typed dependency DAGs and publish bounded hash-addressed blobs. Ship-owned helper subprocesses have bounded output and deadlines.

```bat
python -X utf8 -B uc.py capabilities
python -X utf8 -B uc.py contract-check docs\examples\request.json
python -X utf8 -B uc.py graph validate docs\examples\graph.json
python -X utf8 -B uc.py graph affected docs\examples\graph.json --changed source
python -X utf8 -B uc.py recover list
python -X utf8 -B uc.py workflow status
python -X utf8 -B uc.py workflow show UC-M01.04-C002-T03
```

Use `--generation N` on supported named mutations after reading `lifecycle`. Never guess a generation from the directory name. The first tracked load allocates generation 2 from an initial generation-1 identity; replacement, unload and pending recovery advance it further. `--require-isolation hypervisor` deliberately returns refusal because this release has no such backend.

`verify` preserves the inherited all-runnable-gates PASS meaning but now also reports explicit nested coverage and promotion blockers. `verify --require-complete` refuses every skipped gate, including the supplied optional cargo cases. A workflow accounting PASS is not task completion.

Read [the execution scope](docs/WORKFLOW_EXECUTION.md), [contracts and trust model](docs/CONTROL_CONTRACTS.md), [pending-recovery runbook](docs/RECOVERY.md), and [continuation plan](docs/CONTINUATION.md). Historical UC-2.2.0 and earlier descriptions remain in `README_START_HERE.md`; current release qualification is described here and in the accompanying execution evidence.
