# Unikernel Containership UC-2.4.0 — integrated VWS terminal

This candidate integrates the supplied **HERMIT RAMWS** virtual WebSocket terminal into **Unikernel Containership UC-2.3.0**, adds a gateway-owned, allowlisted Python control bridge, and reapplies the supplied **VWS Master Prompt Workflows 2.0.0** as a traceable, evidence-qualified integration pass.

**This is a trusted-local host-process application, not a bootable unikernel, hypervisor, hostile-tenant sandbox, or production/public service release.** The original 6,360 VWS work packs remain available; they have not all been completed. See `docs/vws/REAPPLICATION.md`.

## Start on Windows

Extract into a new short folder, for example `D:\UC240`. Keep the existing UC230 installation and its live state untouched. The archive contains one top-level `UC240` folder; avoid nesting another identical folder.

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

See `docs/vws/VALIDATION.md` for actual observations and unsuccessful/blocked attempts, `docs/vws/SECURITY.md` for limits, and `docs/vws/OPERATIONS.md` for credentials, cancellation, recovery and rollback. `vwsflow/series.zip` is the exact supplied master-workflow archive. `provenance/vws/source.zip` is the exact supplied terminal archive. The pre-existing 96,000-task containership workflow remains separate in `workflow/`.

## Licensing

All supplied license and copyright notices are preserved. The terminal carries its supplied **All rights reserved** notice; this integration does not relicense the package or grant distribution rights. Review the source notices before publication.
