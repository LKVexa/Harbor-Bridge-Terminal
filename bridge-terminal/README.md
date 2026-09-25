# HERMIT — a virtual terminal on the SPIRAL backend

HERMIT is a professional-grade **virtual terminal** built from source as an
Electron desktop application. It pairs a hand-written **ANSI/VT rendering
engine** with **SPIRAL**, a shell backend that provides an in-memory
filesystem, an extensible command registry, a real pipeline parser, and a
readline-grade interactive line editor. A dockable **browser pane** hosts the
VB-JA21 v9.8.7 engine through a documented adapter seam.

Nothing here wraps a system shell or a third-party terminal emulator — the VT
engine, the shell, and the filesystem are all implemented in this repository.

```
┌───────────────────────────── HERMIT window ─────────────────────────────┐
│  chrome: brand · [browser] · url bar                                     │
├──────────────────────────────────┬──────────────────────────────────────┤
│  terminal (canvas)                │  browser pane (BrowserView)          │
│    VT engine                      │    VB-JA21 v9.8.7 adapter             │
│    Screen · Parser · Renderer     │    (fallback: Chromium)              │
└──────────────────────────────────┴──────────────────────────────────────┘
                    ▲  ANSI byte stream / key encodings  │
                    │  (contextBridge IPC, sandboxed)    ▼
┌──────────────────────────── main process (Node) ────────────────────────┐
│  SpiralKernel   sessions · REPL · pipeline execution                     │
│    ├─ VFS            in-memory POSIX-ish filesystem                       │
│    ├─ Registry      command descriptors + getopt parser                  │
│    ├─ Pipeline      tokenizer · expansion · pipes/redirs/&&/||           │
│    └─ LineReader    readline discipline, emits ANSI to redraw            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Quick start

```bash
npm install
npm start          # launch HERMIT
npm run dev        # launch with devtools
npm run check      # parse-check every .js file
```

Build a Windows executable:

```bash
npm run dist:win   # NSIS installer + portable .exe in dist/
npm run pack       # unpacked app dir (fast, for smoke-testing packaging)
```

`electron-builder` emits `HERMIT-1.0.0-x64.exe` (installer) and
`HERMIT-1.0.0-portable.exe`. Cross-building a Windows target from macOS/Linux is
supported by electron-builder but building **on Windows** is the most reliable.

> Requirements: Node 18+ and the platform toolchain electron-builder expects for
> your target. `electron` and `electron-builder` are the only dependencies.

---

## Project layout

```
hermit-spiral-terminal/
├─ package.json            electron + electron-builder config, scripts
├─ scripts/syntax-check.js parse-gate for CI
├─ src/
│  ├─ preload.js           contextBridge: exposes window.spiral / window.hermitBrowser
│  ├─ main/
│  │  ├─ main.js           window, IPC router, kernel <-> renderer wiring
│  │  ├─ browser-pane.js   dockable BrowserView, adapter discovery
│  │  ├─ browser-adapter.js adapter interface + Chromium fallback
│  │  └─ spiral/           ── SPIRAL backend ──
│  │     ├─ kernel.js      session supervisor + shell interpreter
│  │     ├─ vfs.js         virtual filesystem
│  │     ├─ registry.js    command registry + flag parser
│  │     ├─ pipeline.js    command-line tokenizer/parser/expansion
│  │     ├─ line-reader.js interactive readline discipline
│  │     ├─ env.js         scoped environment store
│  │     └─ commands/      built-in command families
│  │        ├─ system.js   help, about, env, alias, history, exit, …
│  │        ├─ fs.js       ls, cd, tree, find, mkdir, cp, mv, rm, …
│  │        ├─ coreutils.js echo, cat, grep, sort, wc, head, tail, …
│  │        └─ browser.js  browser open/go/close/info
│  └─ renderer/            ── VT engine + UI ──
│     ├─ index.html
│     ├─ styles.css
│     ├─ renderer.js       controller: input encoding, layout, session boot
│     └─ vt/
│        ├─ screen.js      grid, cursor, pen, scroll region, scrollback
│        ├─ parser.js      ANSI/VT state machine
│        └─ renderer-canvas.js  canvas painter + 256-color palette
└─ vendor/browser/         drop VB-JA21 v9.8.7 here (see its README)
```

---

## The VT engine

A three-part pipeline, deliberately mirroring a real terminal:

**`vt/parser.js`** is a ground/escape/CSI/OSC state machine modeled on the DEC
VT500 parser. It decodes C0 controls, `ESC` sequences (`7 8 D E M c`), CSI
sequences (`A B C D E F G d H f J K L M @ P X S T r m h l s u`), private modes
(`?25` cursor show/hide), OSC window-title updates, and full SGR including
256-color (`38;5;n`) and truecolor (`38;2;r;g;b`).

**`vt/screen.js`** is the model: a grid of styled cells with a cursor, the
current pen (SGR attributes), a DEC scroll region, tab stops, deferred
auto-wrap, and a bounded scrollback ring (5,000 lines). It implements insert/
delete char & line, erase-in-line/display, reverse index, and save/restore
cursor.

**`vt/renderer-canvas.js`** paints the model onto a 2D canvas — background
fills, glyphs with bold/dim/italic/underline/strike/inverse, a block cursor
(solid when focused-blink-on, hollow otherwise), HiDPI scaling, and a
scrollback viewport. It also computes the grid geometry that fits the element.

Because the backend emits ANSI and the frontend interprets it, the display
contract is identical to a PTY. The interactive line editor
(`spiral/line-reader.js`) exercises this fully: arrow keys, Home/End, kill-ring
edits (`^U ^K ^W`), history (`↑/↓`), `^L` clear, and Tab completion all work by
the backend emitting redraw sequences the VT engine renders.

---

## The SPIRAL backend

`SpiralKernel` runs one REPL per session:

1. build and emit the prompt (PS1 with `\u \h \w \$` and SGR),
2. read a line through `LineReader` (echo, editing, history, completion),
3. parse it with `pipeline.js` into segments → pipelines → commands,
4. execute against the `CommandRegistry` and `VFS`,
5. stream stdout/stderr back as ANSI, set `$?`, repeat.

**Shell features:** quoting (single/double/backslash), `$VAR`/`${VAR}`/`$?`
expansion, `~` home expansion, pipes (`|`), redirection (`>`, `>>`, `<`),
sequencing (`;`), conditionals (`&&`, `||`), aliases, and environment
variables. `Ctrl-C` aborts the running pipeline via an `AbortController` that
commands observe through `ctx.signal`.

**Virtual filesystem** (`vfs.js`): an in-memory tree with a real path engine
(`.`/`..`/absolute/relative), `stat`, directory listing, recursive mkdir,
move/copy/remove, and a seeded `/etc`, `/home/operator`, `/var/log`, `/tmp`.
It is a true sandbox — no host disk access.

### Command index

`help` lists everything; `man <cmd>` and `help <cmd>` show details. Highlights:

| family     | commands |
|------------|----------|
| shell      | `help` `man` `about` `clear` `history` `env` `export` `unset` `alias` `unalias` `which`/`type` `whoami` `uname` `date` `sysinfo` `exit` |
| filesystem | `pwd` `cd` `ls` `tree` `find` `mkdir` `rmdir` `rm` `touch` `cp` `mv` `stat` `write` |
| text       | `echo` `printf` `cat` `head` `tail` `wc` `grep` `sort` `uniq` `rev` `tr` `seq` `true` `false` `sleep` |
| browser    | `browser open\|go\|close\|info` · `open <url>` |

Try:

```
ls -l
cat /etc/hermit.conf
seq 1 20 | grep 3 | sort -n
echo "hello spiral" | rev
tree /
browser open example.com
```

### Extending: writing a command

A command is a descriptor. Register it after constructing the kernel, or add it
to a file under `spiral/commands/`:

```js
kernel.registry.register({
  name: 'greet',
  summary: 'print a greeting',
  usage: 'greet [-u] NAME',
  parse: { valued: [] },              // short flags that take a value
  async run(ctx) {
    const name = ctx.args[0] || 'world';
    const text = ctx.flags.u ? name.toUpperCase() : name;
    ctx.stdout.write(`hello, ${text}\n`);
    return 0;                          // exit code
  }
});
```

`ctx` gives you `args`, `flags`, `stdin`, `stdout`, `stderr`, `env`, `vfs`,
`host`, `registry`, `signal`, `cwd`, `resolve(path)`, and `chdir(abs)`. Install
a whole pack with `kernel.registry.install([...])`.

---

## Browser integration (VB-JA21 v9.8.7)

The pane is engine-agnostic. Out of the box it uses a Chromium `BrowserView`
fallback so the app is fully functional. To plug in your browser, drop the
v9.8.7 bundle into `vendor/browser/` and provide an `index.js` adapter — see
`vendor/browser/README.md` and the annotated template
`vendor/browser/index.example.js`. The adapter contract is four members
(`name`, `attach`, `resolveUrl`, `navigate`); the reference implementation lives
in `src/main/browser-adapter.js`.

`extraResources` in `package.json` bundles `vendor/browser/` into the packaged
`.exe`, so your browser ships inside HERMIT.

---

## DF fabric integration

HERMIT is the control surface for the **DF container fabric** (`DF-PA21.2`):
four sandboxed node VMs — `N_SMALL`, `N_MEDIUM`, `N_LARGE`, `N_XLARGE` — federated
by `DF_Fabric`, running `.pal` row-sequence bundles under a replica / pipeline /
BSP model. The fabric is offline by construction (`NETWORK=deny`,
`BACKEND=none`); HERMIT adds no network.

HERMIT **ships none of the DF packages** — it locates the containers wherever
they already live and reads/drives them in place. Point it at the folder that
holds `DF_Fabric` + the four nodes:

```
df use /path/to/df           # or set the DF_ROOT environment variable
df where                     # resolved root + python + fabric dir
df nodes                     # roster: presence + build state
df bundles                   # discoverable .pal bundles
df spec fabric|index|language
```

Native, read-only renderers (no execution):

```
fabric topology              # federation domains/groups + classical links
fabric status                # presence + pinned manifest digests + bundle count
```

Driving the real DF CLIs (streamed live into the terminal; `Ctrl-C` stops them):

```
node small build             # compile a node's embedded VM (./BUILD)
node small run 01_bell_pair.pal --seed 0
node large verify
fabric build                 # build all four nodes
fabric run 01_bell_pair.pal --profile static --placement dynamic --programs replica,bsp
fabric verify
```

Bare bundle names (e.g. `01_bell_pair.pal`) are resolved to their path via
discovery, so they work from any directory. Everything else after the
subcommand is forwarded to the DF CLI unchanged. Requires Python 3 on `PATH`
(override with the `PYTHON` env var); nodes must be built once (`./BUILD` or
`node <k> build`) before they run.

Implementation: `src/main/spiral/dfabric/locator.js` (root discovery + descriptor
reads), `dfabric/runner.js` (child-process streaming with abort), and the
`df` / `fabric` / `node` commands in `commands/dfabric.js`.

## VEC1 Photon — the compute backend (Electron substituted)

Instead of doing heavy work in a Node/Electron main process, HERMIT **delegates
its complex requests to a running VEC1 "Photon"** — your Electron-substitute
control plane. VEC1's own `ELECTRON_COMPATIBILITY.md` defines the mapping this
integration targets: main process → Python control plane; renderer → app-mode
system browser; `ipcMain`/`invoke` → loopback JSON-RPC over `/api/...`; preload
bridge → `fetch('/api/...')`. So this is a *retarget onto the Photon*, not a
file-for-file Electron drop-in (VEC1 is a reference shell, not an API clone).

Bind a Photon and delegate:

```
photon use http://127.0.0.1:<port> <X-VEC1-Token>   # token from the VEC1 launcher
photon where            # url, token, reachability
photon status           # /api/status + /api/health
photon electrons        # /api/electrons
photon diagnostic       # POST /api/fabric/diagnostic (raw)
photon run [name]       # the delegated workflow, on demand
```

Once a Photon is bound, `fabric run` **delegates automatically** in the order
you specified — **electron lifecycle first, then the fabric proof**:

```
▶2 electron lifecycle        POST /api/electrons  →  operate cross_target.verify
▶1 fabric proof (control plane)   POST /api/fabric/diagnostic  →  verdict
```

`fabric topology` / `fabric status` also prefer the Photon's `/api/topology` and
report the binding. If no Photon is bound (or it's unreachable), everything
falls back to the direct DF CLI path described above — HERMIT still works
standalone.

Targets VEC1's real routes (`runtime/service.py`): `GET /api/{health,status,
topology,electrons,electrons/:id,events}` and `POST /api/{electrons,
electrons/:id/operate, electrons/:id/clone, fabric/diagnostic, shutdown}`.
Mutations carry the per-launch `X-VEC1-Token`; requests are loopback-only. The
64-bit fabric witness is preserved exactly (read from the raw response, never
rounded through a JS number).

Implementation: `src/main/spiral/photon/client.js` (loopback JSON-RPC client),
`photon/workflow.js` (the electron-then-fabric workflow), and the `photon`
command plus the `fabric` delegation in `commands/dfabric.js`.

> Auth note: VEC1 injects the token into the page it serves. A cross-process
> client (HERMIT under Electron) must be handed the token via
> `photon use <url> <token>`; alternatively, serve HERMIT from VEC1's `ui/` so
> the token is injected as `<meta name="vec1-token">`.

## Security model

- Renderer is sandboxed: `contextIsolation: true`, `nodeIntegration: false`,
  `sandbox: true`. It touches only the two `contextBridge` surfaces.
- The browser pane runs in an isolated session partition
  (`persist:hermit-browser`).
- SPIRAL's filesystem is entirely in-memory; commands cannot reach the host
  disk. (A host-backed VFS provider can be added later behind the same
  read/write/stat surface.)

---

## Notes & next steps

The engine is a deliberate, well-factored core rather than a kitchen sink. Clear
extension points if you want to push further: alternate-screen buffer and mouse
tracking in the VT engine, streaming (concurrent) pipes in the kernel, a
host-backed VFS provider, and a persisted history/rc file. Each seam is small
and isolated.

---

## RAM-resident virtual WebSocket (candidate 2.0.0-ramws.1)

This revision applies the RAMWS v1.0.0 master prompt and workflow series on top of the VWS200 candidate: the
authenticated virtual WebSocket now speaks **`hermit.vws.v2`** only (binary data frames, byte credits, session
reset on process loss), keeps every retained session/payload/transport byte in **bounded, ledgered process RAM**
(profile LOCAL_VOLATILE, one worker thread per session under an enforced heap cap), and its CPU cost was
**measured** against the previous candidate in a preregistered experiment. The kit's own boundary is kept:
RAM stores; the CPU executes. No "compute in memory" is claimed.

```
START.cmd            (Windows)          ./start.sh          (Linux / macOS)
```

then open `http://127.0.0.1:10000/`, paste the access token printed on first start, and try:

```
fabric status
node small run 01_bell_pair.pal
fabric run 02_ghz3.pal --programs replica,bsp
```

| Read | For |
|---|---|
| `docs/RAMWS.md` | the claim boundary, decisions RD-01…RD-05, descriptor fields and invariants, the memory plan, what is not claimed |
| `docs/PROTOCOL_V2.md` | control envelopes, binary data frames, credits, acknowledgement levels, session reset |
| `docs/EXPERIMENT.md` | the preregistered CPU experiment, all four runs, the ablation, gates G0/H1–H5 and status words |
| `docs/SECURITY.md` | what changed in the threat model; second adversarial review findings and fixes |
| `docs/OPERATIONS.md` | configuration reference (`VWS_PROFILE`, `VWS_WORKER_BACKEND`, memory limits, credits), `/live` telemetry |
| `ledger/DISPOSITIONS_SUMMARY.md`, `ledger/release.json` | 32 kit packages, 6300 re-audited overlays, gate decision |
| `docs/vws200/` | the previous candidate's documentation (v1 protocol, VWS200 ledger), kept for history |

Status in one line: local/loopback use **GO** (127/127 tests, CPU_BENEFIT_SUPPORTED on this host: 42 % / 67 % / 99 %
less server CPU per keystroke / MiB / paste than 1.1.0-vws.1); public or multi-tenant service **NO-GO**
(DEPLOYMENT_TESTED and RESIDENCY_VERIFIED not achieved; identity provider, hosted rehearsal and independent human
review outstanding); the Electron desktop path is untouched by this run and was not launched.
Zero third-party runtime dependencies: `npm test` needs no install.
