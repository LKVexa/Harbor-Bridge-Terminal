# Unikernel Containership UC-2.8.0 — edge-component atoms applied

UC-2.8.0 combines the UC-2.7.0 master-series candidate with the **99 supplied edge-component atom archives** (the `Edge Components in` set: GAP-01…15, INV-02…72, PLN-01…07, SCH-01, iOS735 LCTL). Every archive is kept byte-for-byte under `edge/source/`; one canonical build per element (86 elements) is extracted under `edge/atoms/`, four distinct alternative builds under `edge/variants/`, and 85 atoms are bound to the PK element of the same id in `pk/PK_ATOM_BINDINGS.json`. Atom suites run as isolated child interpreters in disposable copies. Start with `EDGE.cmd status`, `EDGE.cmd check --deep`, `EDGE.cmd test all`, and read [docs/edge/EDGE_INTEGRATION.md](docs/edge/EDGE_INTEGRATION.md). Recorded here: **9,833 atom tests pass / 41 fail / 0 errors (59 suites green, 27 red)**, all classified; nothing is promoted to PASS and this is still **not Production GO**.

## UC-2.7.0 — master-series applied candidate

UC-2.7.0 applies the attached **15-volume / 150-component / 375,000-record master prompt and workflow series** as a conservative engineering execution layer. The exact source volumes are retained under `masterflow/source/`; `MASTER_FLOW.cmd check --deep` verifies their hashes and full task-ID coverage. Local platform primitives now add bounded eventing, hash-chained audit records, metrics, traces, health/capability inspection, queue backpressure/idempotency, quotas, feature/retention validation, capacity planning, an explicit pixel-kernel ABI/capability descriptor, and a compatibility matrix. None of these local controls are relabeled as a hypervisor, multi-host consensus system, public deployment, production key authority, or multi-tenant isolation boundary.

Use `MASTER_FLOW.cmd status`, `MASTER_FLOW.cmd check --deep`, `MASTER_FLOW.cmd execute`, and `python uc.py platform status`.

This candidate applies the supplied **TIFF Nine-Phase Prompt/Workflow v1.6.0** to UC-2.4.0: bounded TIFF state admission and atomic history, reversible GIF byte-plane transport, a checked u64 pixel kernel, local state tools and read-only VWS integration. The original native engine archives, sealed berths, genesis states and prior VWS integration are retained.


UC-2.6.0 introduced the ten supplied **JYRM 1BNCF v3.1.0** phase archives as a bounded local communication subsystem. Use `ONEBIT.cmd status`, `ONEBIT.cmd demo`, `ONEBIT_FLOW.cmd check`, and `VERIFY_1BIT.cmd`. Local computation remains full precision; only the guarded sign stream is one bit per scalar. See `docs/onebit/`.

**This is a trusted-local host-process application, not a bootable unikernel, hypervisor, hostile-tenant sandbox, or production/public service release.** The original 6,360 VWS work packs remain available; they have not all been completed. See `docs/vws/REAPPLICATION.md`.

## TIFF/GIF tools

Read **[TIFF/GIF quick start](docs/tiff/START.md)**, [format and kernel contract](docs/tiff/CONTRACT.md), [workflow application](docs/tiff/WORKFLOW_APPLICATION.md), and [current validation](docs/tiff/VALIDATION.md). Start with `PIXELS.cmd status`, `PIXELS.cmd inspect vm_small DF_Small`, and `VERIFY_TIFF.cmd --deep`. The TIFF workflow is separate from the retained VWS workflow: 325,000 source task dispositions and nine full-series gates remain blocked; passing local tests are not whole-source completion.

## Start on Windows

Extract into a new short folder, for example `D:\UC280`. Keep the existing UC240/UC270 installations and their live state untouched. The archive contains one top-level `UC280` folder; avoid nesting another identical folder.

Double-click **`TERMINAL.cmd`** or **`START.cmd`**. An installed **Node.js 22+** and usable **Python 3.10+** are required. The launcher probes Python and installs nothing. The gateway uses built-in Node modules; neither `npm install` nor Electron is needed for this web-terminal path. Only Node 22.16.0 / Python 3.13.5 were exercised here; other accepted versions are not individually qualified.

The launcher prints the local URL, normally `http://127.0.0.1:10000/`, and on first launch a one-time-display token. Paste the token into the terminal's Sign in form. The launcher attempts to open the browser; use the printed URL manually when browser opening is unavailable. Keep the launcher console open while using the terminal.

```bat
TERMINAL.cmd --check --no-browser
TERMINAL.cmd --port 10001
TERMINAL.cmd --no-browser
```

Default mode allows inspection, not workload execution. Missing Node/Python, incompatible configuration, and a busy port produce a visible nonzero exit. To select an interpreter explicitly:

```bat
set "PYTHON=C:\full\path\to\python.exe"
set "NODE=C:\full\path\to\node.exe"
TERMINAL.cmd
```

Linux: `./TERMINAL --no-browser` or `python3 -B uc.py terminal --no-browser`.

## Inside the virtual terminal

```text
ship help
ship status
ship berths
ship capabilities
ship lifecycle vm_small
ship fabric status vm_small
ship vws-workflow status
ship tiff-workflow status
ship onebit-workflow status
ship onebit status
ship pixels status
ship pixels inspect vm_small DF_Small
ship workflow status
```

SPIRAL's existing virtual commands, VT display, virtual files, pipelines and editor are retained. `ship` is an additional capability-filtered command, not a passthrough to CMD, PowerShell, Bash or a host shell.

## Explicit workload control

Build the native engines using the existing local `BUILD.cmd` / `python -B uc.py build` before executing workloads. Building requires the existing project's platform toolchain; TIFF operations also require Pillow. Read-only terminal inspection does not require native engines to have been built. This package does not include this qualification machine's `_engines` or `_studio` outputs.

Stop the terminal launcher, then use:

```bat
TERMINAL.cmd --control
```

The launcher grants control only when both the global control option and the principal's `ship.control` capability are present. Inspect the current generation first:

```text
ship lifecycle vm_small
ship run vm_small --sealed --generation N
ship run vm_small --ticks 1 --generation N
ship verify vm_small
```

Replace `N` with the current generation; when lifecycle reports no tracked workload, the existing UC contract starts at generation 1. A successful run does not necessarily increment the generation; generation fences identify an incarnation, not each command. Ticks are limited to 1–10 per request. `ship verify BERTH` runs one berth's existing quick gate battery and is not a production certification. Global/all-berth verification remains a local CLI operation.

Only one broker operation may run globally; concurrent requests are refused, not queued. The existing ship lock also refuses overlap with a local CLI operation. Do not run a native build/verify concurrently with the integration test suite. Never automatically retry interrupted mutations: inspect `ship recover list`, then use the local recovery CLI as described in Operations.

`load`, `unload`, `build`, `seal`, arbitrary paths, arbitrary command flags, and recovery writes remain outside the web bridge.

## Verification and provenance

```bat
CHECK_VWS.cmd
VERIFY_VWS.cmd
VWS_WORKFLOW.cmd check
```

`CHECK_VWS.cmd` checks terminal file integrity. `VERIFY_VWS.cmd` runs portable Node test-file discovery with per-file deadlines and writes results under `_runs/vws-tests`; explicitly optional tests are reported as skipped, not observed passes. `VWS_WORKFLOW.cmd check` verifies source and ledger identity, not engineering completion. The wrapper uses `PYTHON` or `python`; the Python-launcher equivalent is `py -3 -B uc.py vws-workflow check`.

Full original context for a work pack:

```bat
python -B tools\vws-pack.py C18-001
python -B uc.py vws-workflow show I026
```

Keep generated context files outside the sealed release, or under `_runs`, to avoid adding unbound files to its inventory.

See `docs/tiff/VALIDATION.md` for current TIFF/GIF observations and `docs/vws/VALIDATION.md` for historical UC-2.4.0 observations and unsuccessful/blocked attempts, `docs/vws/SECURITY.md` for limits, and `docs/vws/OPERATIONS.md` for credentials, cancellation, recovery and rollback. `vwsflow/series.zip` is the exact supplied master-workflow archive. `provenance/vws/source.zip` is the exact supplied terminal archive. The pre-existing 96,000-task containership workflow remains separate in `workflow/`.

## Licensing

All supplied license and copyright notices are preserved. The terminal carries its supplied **All rights reserved** notice; this integration does not relicense the package or grant distribution rights. Review the source notices before publication.
