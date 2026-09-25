# Start here — UC-2.5.0 TIFF/GIF pixel infrastructure

## Keep the earlier installation intact

Extract `Unikernel_Containership_v2.5.0_TIFF_GIF.zip` into a new short location so that `uc.py` is at **`D:\UC250\uc.py`**. The archive already contains a `UC250` top-level folder. Do not extract over UC240, copy its live `_fabric` files automatically, or replace an existing installation's mutable state. This is a separate candidate, not an in-place installer. Original engine archives, sealed berths and genesis states are retained.

The runtime needs installed Python 3.10+ and Pillow for TIFF/GIF commands. The retained VWS launcher additionally needs Node.js 22+. Native execution needs the existing C11/make/OpenSSL toolchain; see `REQUIREMENTS.txt`. These launchers neither install dependencies nor require administrator elevation. Linux was exercised; native Windows execution and browser UI interaction were not. Python 3.13.5, Pillow 12.3.0 and Node 22.16.0 were observed on the qualification machine. Other accepted versions are not individually qualified.

## Inspect without running a workload

In Command Prompt:

```bat
cd /d D:\UC250
PIXELS.cmd status
PIXELS.cmd inspect vm_small DF_Small
PIXELS.cmd cell vm_small DF_Small 0 0
PIXELS.cmd export-gif vm_small DF_Small
TIFF_FLOW.cmd status
TIFF_FLOW.cmd check --deep
VERIFY_TIFF.cmd --deep
```

Inspection and export read the live TIFF when present, otherwise the sealed genesis TIFF. Export writes a separate GIF under `_runs\pixels`; it never changes a live image. The printed result gives its exact filename. GIF is a reversible byte-plane transport, not the runtime's live execution format or a color-faithful screenshot.

`VERIFY_TIFF.cmd` runs the workflow-integrity check and the 100 TIFF/GIF/pixel regression tests. It does not certify all 325,000 source tasks. The independent TIFF encoder test requires optional NumPy/tifffile packages; absent packages yield an explicit skip. The tested optional dependency versions are in `requirements-tiff-test.txt` and require Python 3.12+ together.

To choose an interpreter explicitly:

```bat
set "PYTHON=C:\full\path\to\python.exe"
PIXELS.cmd status
```

For complete local Python regression, use:

```bat
python -B -m unittest discover -s tests -v
```

Unix equivalents are `./PIXELS`, `./TIFF_FLOW`, `./VERIFY_TIFF`, or `python3 -B uc.py pixels ...`. Run checks sequentially, not concurrently with a build or workload operation; the workspace lock intentionally refuses overlap.

## Build and explicitly edit live state

Run the existing `BUILD.cmd` (or `python -B uc.py build`) once the native toolchain is available. The release does not ship qualification-machine `_engines`, `_studio`, live `_fabric`, credentials or run databases. Build creates local runtime outputs and initializes state. Do not force-reset a pre-existing live state merely to make an example command work.

Then inspect the current workload generation and live TIFF digest:

```bat
python -B uc.py lifecycle vm_small
PIXELS.cmd inspect vm_small DF_Small
```

Substitute the returned generation and the complete `file_sha256` in the following command; `N` and `SHA256` are placeholders, not defaults:

```bat
PIXELS.cmd paint vm_small DF_Small 0 0 40 --generation N --expect SHA256
PIXELS.cmd cell vm_small DF_Small 0 0
python -B uc.py run vm_small --ticks 1 --no-view --generation N
```

This modifies only live tile 0, u64 word 0. Tile indices are 0–3; native word indices are **0–57**, not 0–63. Values are unsigned 64-bit integers. A new digest must be read after any write. A successful command does not necessarily increment the workload generation; generation identifies an incarnation, not the count of operations.

At the 512-page history limit, another write is refused rather than silently deleting history. To preserve the entire current TIFF and reset the live history to its unchanged newest state:

```bat
PIXELS.cmd inspect vm_small DF_Small
PIXELS.cmd checkpoint vm_small DF_Small --generation N --expect SHA256
```

The checkpoint prints the archive path and its full digest. Keep archives safe and manage their retention and disk usage. There is no new global disk-quota service. Interrupted managed operations must be investigated with the existing recovery tools before retrying; see `docs/vws/OPERATIONS.md`.

## Restore a GIF as an offline TIFF

Use the exact exported filename and a **new** output filename:

```bat
PIXELS.cmd restore-gif "D:\UC250\_runs\pixels\vm_small\DF_Small\EXPORTED.gif" "D:\UC250\_runs\pixels\restored.tif"
```

Restore validates every frame and refuses an existing output. Inside the ship, restoration is restricted to `_runs` or `_scratch`; it does not activate a restored state, overwrite a live berth, or modify the sealed release. Do not re-save state GIFs through an ordinary image editor: palette or metadata edits can destroy reversibility.

## Retained web terminal

Start `TERMINAL.cmd`; open the printed local URL and enter the first-launch token. Read-only commands include:

```text
ship pixels status
ship pixels inspect vm_small DF_Small
ship pixels cell vm_small DF_Small 0 0
ship tiff-workflow status
```

Pixel writes, exports, checkpoint and restoration are deliberately not exposed over the WebSocket, even with `--control`. Existing generation-checked native workload commands remain available in explicit control mode. See the root README and `docs/vws/OPERATIONS.md`.

## Source workflow execution

```bat
TIFF_FLOW.cmd show C313-T001.05
TIFF_FLOW.cmd execute
```

The first command shows an exact retained source task and its disposition. The second executes the candidate's bounded local phase-ordered qualification profile, not an automatic implementation of all source tasks. P08's absent cloud/Zarr backend is not run. Local tests can pass while all nine full-source approval gates remain blocked. See `WORKFLOW_APPLICATION.md` and `VALIDATION.md` for the precise scope and evidence.
