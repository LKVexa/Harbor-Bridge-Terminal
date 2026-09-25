# Current release: UC-2.3.0

Start with [README.md](README.md). The following UC-2.2.0 and earlier material is preserved as historical baseline documentation, not a claim that its measurements were rerun for UC-2.3.0. New transaction/recovery behavior and limits are in `docs/RECOVERY.md` and `docs/CONTROL_CONTRACTS.md`.

---

# Unikernel Containership -- START HERE

**UC-2.2.0** · hull: PA Language Studio 2.0.0 (unchanged) · hold: DF-PA21.2-1.0.0 (unchanged) ·
language: PA-LCTL 1.6.x · **runs on the .tif distributed fabric**

## UC-2.2.0 — current release notes

This is a **local VM-orchestration skeleton with ship-layer safety repairs**, not yet a bootable or hypervisor-isolated unikernel. `NETWORK=deny` is not an OS firewall rule. Read `SECURITY.md` before loading external projects. The historical design and conformance narrative below are retained for context; the new release audit and test evidence take precedence for current validation claims.

Extract to a new short directory, for example `D:\UC220`, rather than over an existing workspace. Keep your previous installation and user edits intact. This is a full source archive, not an in-place updater. Runtime dependencies are not silently downloaded; no host registry settings or execution policies are changed.

Run these from Command Prompt so errors remain visible:

```bat
cd /d D:\UC220
python -X utf8 -B uc.py --version
DOCTOR.cmd
SELFTEST.cmd
BUILD.cmd
VERIFY.cmd
RUN.cmd vm_small --sealed
RUN.cmd vm_small --ticks 1
```

On a machine with only the Python Launcher, use `py -3 -X utf8 -B uc.py doctor` (and replace `doctor` with each other command), or set `PYTHON` to the full path of a usable Python executable before invoking the wrappers. A Windows Store alias is not evidence that a usable runtime exists. Python 3.10+, the selected native toolchain and Pillow are prerequisites; see `REQUIREMENTS.txt`. Native Windows/macOS execution was not observed during this audit.

`doctor` checks source integrity, hold pins, prerequisites and pending transactions, and explicitly reports absent isolation capabilities. `self-test` is the added ship regression suite; `verify` also runs the inherited native/berth/hull gates. `verify --require-complete` blocks any skipped nested gate. Keep failed/skipped evidence visible rather than resealing to silence it.

Replacement is staged; previous cargo is kept under `_runs/backups/`. Unload is recoverable instead of destructive. Complete cross-resource crash recovery and automatic backup/history pruning are not implemented. Ship-managed TIFF history stops at 512 pages. See `CHANGELOG.md`, `docs/AUDIT_REPORT.md` and the 96-component backlog in `docs/MISSING_COMPONENTS.md` (plus JSON and 12 individual phase files).

## What this is

A containership: the PA Language Studio (the hollow scaffold) combined with the DF containers (the four
VM nodes + fabric). Load a VM or a sub-system and the ship breaks it up script by script, sorts every
script into one of the four nodes by measured needs and complexity, and gives the project **its own blank
four-node-plus-fabric scaffold** -- a berth -- holding the sorted cargo, its declarations as PA-LCTL
bundles, its seals and its hull face. Every berth pulls from the same four engines in the hold.

New in UC-2.1.3: **every container gets its own .tif fabric.** The studio's 2.0.0 fabric is a picture you
can run -- a container's device fabric as a tiled, multi-page `.tif`, read back as the state of the next run --
and the ship gives that to each of a berth's six containers: the four node containers (their picture holds the
container's state and the berth's declaration as cells; a tick hands what the picture says to the engine),
the fabric container (the federation's vote and sealed event log) and the hull face (ticked by the hull's VM
itself). `./RUN <berth>` is a tick: six pictures in, executed, six new frames out. Paint a cell in a `.tif`
and the next tick executes what you painted -- and says so. And a berth whose cargo is itself a studio container is **hull cargo**: broken up like anything
else, re-assembled from its slots by BUILD, mounted in the hull with its own picture, and ticked on it --
the container keeps running its own program in the ship (`ARCHITECTURE.md` s5.1).
`ARCHITECTURE.md` is the systems architecture (s6.1 the fabric); `reports/SORT_POLICY.md` is the sort
policy; `registry/BILL_OF_LADING.md` is what is loaded.

Loaded here: `sub_mssl_to_lctlc`, `sub_pa21_language_studio`, `vm_large`, `vm_medium`, `vm_small`, `vm_xtra_large`.

## The four entry points

```
./BUILD [--pa21 <PA21.2 root>]      extract + build the four engines from hold/, install the hull into _studio/,
                                    register every berth's hull face, materialise every container's live .tif from
                                    its sealed genesis  (idempotent; duration depends on host and toolchain)
./VERIFY [--quick]                  the ship battery: integrity, policy, engines, hull (its own 135-check verifier),
                                    bill of lading, every berth (B0-B11: incl. the .tif fabric and hull cargo), studio test, the
                                    .tif codec; exit non-zero on any FAIL
./RUN <berth> [--ticks N]           one tick (or N) of the berth's .tif fabric: six pictures in, executed, six new
                                    frames out;  --sealed runs the sealed bundles' programs (replica + pipeline + BSP)
./LOAD <dir|zip> --name N --kind vm|subsystem
                                    load a project into its own berth, six pictures included (then ./VERIFY N)
```

Windows twins: `BUILD.cmd`, `VERIFY.cmd`, `RUN.cmd`, `LOAD.cmd` (they call `python`). Everything is offline
(`NETWORK=deny`, `BACKEND=none`). `python3 uc.py --help` lists every command (`status`, `berths`, `sort`,
`fabric`, `mount`, `mounts`, `slot-run`, `unload`, `seal`, `studio-register`, `studio-test`). `LOAD` and `unload` re-seal the ship
(MANIFEST.json + SHA256SUMS.txt) because they change what it carries; the assembly seal stays on record. The
pictures need Pillow (`pip install Pillow`, see REQUIREMENTS.txt); without it the .tif gates are SKIPPED and
`./RUN --sealed` still runs.

Examples:

```
./RUN vm_medium                           # tick vm_medium: its six .tif fabrics read, executed, written back
./RUN vm_medium --ticks 5                 # five ticks; the accumulator chains through the pictures
python3 uc.py fabric status vm_medium     # what every picture says (tick, accumulator, agreement, intact)
python3 uc.py fabric view vm_medium       # PNG views of the six pictures (berths/vm_medium/*/_fabric/*.png)
python3 uc.py fabric live vm_medium --ticks 20 --interval 0.5     # the fabric in flux
python3 uc.py fabric init vm_medium --force                       # back to the sealed genesis
./RUN vm_medium --sealed                  # the sealed bundles on the four engines (replica + pipeline + BSP)
python3 uc.py sort some/script.py         # where would it go, and why (rule + measured features)
berths/vm_small/DF_Small/RUN examples/boot.mssl      # run one cargo script on the Small engine
./LOAD ~/myproject --name myproject --kind subsystem && ./VERIFY myproject
```

## Historical UC-2.1.3 assembly measurements (not UC-2.2.0 evidence)

17 of 19 ship gates passed (2 skipped: the two seal gates that can only run after sealing);
details in `conformance/UC_GATE_RESULTS.json`, the hull's own verifier log in `conformance/logs/`, and
`ARCHITECTURE.md` s10.

The same BUILD and VERIFY were also run on a copy of this tree as a **Windows-like host without a C toolchain** (no cc/make, no `sh`, no `fork`, a non-UTF-8 console -- `conformance/LIMITED_HOST_REHEARSAL.md`): BUILD `BUILT_HOST_LIMITED`, VERIFY `PASS` with 14 passed, 0 failed, 5 skipped of 19 ship gates (berth gates SKIPPED with a reason on such a host: B7, B8, B10, B11). That is what a Windows machine without a compiler will see; a C toolchain with make turns the SKIPPED gates into observed ones.

## Layout

```
README_START_HERE.md  ARCHITECTURE.md  MANIFEST.json  SHA256SUMS.txt  LICENSE  REQUIREMENTS.txt
BUILD VERIFY RUN LOAD (+ .cmd)   uc.py
hull/        PA Language Studio 2.0.0, byte-identical (+ HULL_DIGEST.json)
hold/        DF_Small.zip DF_Medium.zip DF_Large.zip DF_Xtra_Large.zip DF_Fabric.zip DF_INDEX.md DF_SHA256SUMS.txt
             HOLD_DIGEST.json  PA21_LEDGER_EXCERPT/ (the PA21.31 capability ledger for the hull's PA21 gate)
ship/unikernel/   sorter · berth (loader) · tif_fabric (the pictures, the tick) · registry · engines · studio_face · gates · cli
berths/      one directory per loaded project (each container's genesis .tif sealed inside; live pictures under _fabric/)
registry/    BILL_OF_LADING.json/.md
schemas/ conformance/ reports/ authority/ provenance/ corpus/
_engines/ _studio/ _runs/     BUILD/VERIFY/RUN outputs (not delivered; excluded from the inventory)
berths/*/_fabric/ berths/*/*/_fabric/   the live pictures (state; excluded from every seal, made by BUILD/RUN)
```

## On Windows

Use the `.cmd` twins (they call `python` in UTF-8 mode; Python 3.10+ and Pillow installed). BUILD, VERIFY and RUN
work on a Windows host, and where the host lacks something the ship works around it or says so -- never a
traceback, never a silent PASS (`ship/unikernel/host.py`; every BUILD/VERIFY/tick record carries `host` and
`limits`):

* **no C toolchain** (the usual case): the Small, Medium and Large engines are C and cannot be built, and the hull
  cannot build its runner -- BUILD ends `BUILT_HOST_LIMITED` with the reason; U2, B7, U7 and B10 are `SKIPPED`
  with the reason (B10 records what the one bound engine showed: tick 1 == reference, tick 2 chained, painted
  cells adopted and reported -- but a tick cannot complete with three pictures untouched, so it is not passed),
  B11 re-assembles, seal-checks and finds the hull cargo mounted and skips only the tick; the QUORUM engine
  (Python + the JDK's column verifier) carries every berth's witness alone (B5, B6, B8); the hull is installed
  compile-only (faces built and sealed, pictures made, hull cargo mounted; nothing run); the .tif fabric is
  complete; a `RUN` is `TICK_INCOMPLETE`. To get all four engines and the hull's own runtime, install a C
  toolchain with `make` (MSYS2/MinGW-w64: `pacman -S mingw-w64-ucrt-x86_64-gcc make`, or Visual Studio Build
  Tools + GNU make) and run BUILD.cmd again;
* **no `sh`**: the QUORUM VM's compile normally runs its bundled LCTL 1.6.1-RC1 column verifier through
  `sh START_LCTL_1_6_1.sh`; the ship's N_XLARGE binding runs the same jar directly through `java -jar` and
  records `lctl_column_verify=JVM_DIRECT` (without a JDK: `SKIPPED_NO_JDK`);
* **no `fork`**: the multi-process fabric profiles (gate B6, `--profile multi_process_*`) run as
  `multi_thread_deterministic` and the record says so (`profile_requested` / `host_note`);
* **cp1252 console**: `uc.py` runs in UTF-8 mode (re-executing itself once if the locale is not UTF-8), so the
  hull's verifier and the engines' toolchains, which write UTF-8, cannot crash the ship's stdout or their pipes.

The ship's own zip opens in Explorer
and extracts on NTFS: cargo whose original path cannot exist on Windows (a case-colliding pair, a path over the
budget) is stored under an alias and answers to its original path everywhere (`ARCHITECTURE.md` s3). No delivered
path exceeds **140 characters**, which is what makes the archive safe for Explorer's own extractor: it is not
long-path aware even where the registry is, and it unpacks into a folder it names after the archive, so a Desktop
destination leaves about 165 characters -- more than the ship needs. (Python is long-path aware where the registry
enables it, which is why `BUILD` can hold the hold's own 262-character documentation paths that Explorer cannot.)
Two things
are outside the ship's control and are reported, not hidden: `hold/DF_Xtra_Large.zip` (and the VM it carries,
`Desktop\VMs\Xtra_Large.zip`) holds one pair of files differing only by case (`vm/world/evidence/INPUT_PROVENANCE.json`
/ `input_provenance.json`) and documentation paths that exceed 260 characters under a Desktop folder -- Explorer will
call that zip invalid (7-Zip or Python open it), and BUILD, which extracts the hold with Python, keeps what the host
can hold, records the rest in `_runs/BUILD_<stamp>.json#extract.<slot>.host_limits`, and still builds and binds the engine. Enabling
Windows long paths (`LongPathsEnabled`) or extracting the ship into a short folder such as `C:\UC\` avoids the
length limit altogether.

## What is not claimed

Cargo is carried, sorted, sealed and witnessed -- not interpreted (runnable cargo in a slot's own dialect can
be executed on its engine). The fabric runs on one host with local processes. No engine has a qubit; physical
outputs are `BLOCKED_EXTERNAL_AUTHORITY`. The four node containers' pictures are read and written by the
ship around a native run on the engine; only the hull face's picture is executed by the VM itself (the
studio's loop). CARGO.pal is witnessed from its seal, not ticked. Every VM's own blockers are inherited
verbatim through the DF containers. `reports/UC_BLOCKED_REGISTER.md` has the rest.
