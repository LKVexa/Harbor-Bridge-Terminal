# PA21 Language Studio

A scriptable installer and runtime for COLUMNED LCTL applications, built from a
copy of the BOTTLE ROCKET 4.7.0 container VM and bound to a PA21.31 delivery.

Two ways in, the same behaviour behind both:

| | |
|---|---|
| **Window** | `INSTALL.cmd` (Windows) or `./INSTALL.sh` — opens the install/remove window in your browser |
| **Command line** | `studio.cmd status --json` / `./studio.sh run myapp` — every command takes `--json` |
| **Python** | `from pa21studio import Studio` — the window and the CLI are both thin views over this |
| **Something that is not a person** | `studio.cmd describe --json` for the contract, `studio.cmd try --from -` for one round trip — see [Letting something else write the code](#letting-something-else-write-the-code) |

Everything the studio says about itself is checkable from inside it:
`studio abi` demonstrates the language contract, `studio test` runs every
container against its own declared answer, `studio doctor` says what this host
has actually exercised, and `verify_studio.py` does all of it from a scratch
install.

---

## What it installs

The studio takes the container VM package, **copies** it into a studio root,
re-hashes every copied file against the package's own `RELEASE_CONTENTS.sha256`,
compiles a host runner against the VM's C core **and its memory adapter**, and
then — before it reports success — compiles four applications from source and
executes them, checking each against the answer that application declares.

```
<studio root>/
  studio.json        the install manifest: sources, hashes, and the exact
                     list of paths this installation owns
  runtime/           the copied BOTTLE ROCKET container
  bin/brrun          the host runner, built here from the copied source:
                     the VM core plus the memory adapter that backs its
                     device fabric
  containers/        one container per project, plus a derived REGISTRY.json
  logs/
```

The studio root holds containers and nothing else: the runtime arrives as one,
and every project you create becomes one beside it.

Default root: `%LOCALAPPDATA%\PA21LanguageStudio` on Windows,
`~/.pa21-studio` elsewhere, or `PA21_STUDIO_HOME`, or `--root`.

**Uninstall removes only what that manifest lists.** Anything else under the
root is reported as residue and left alone.

---

## The container is the backend

The VM core on its own is half a machine. The other half is the device and I/O
service architecture the package defines — console, persistent block, monotonic
state with anti-rollback, entropy, clock, mailbox, diagnostics — and a VM
created without a host abstraction layer has none of it. A program that touches
any service on such a VM does not degrade quietly; it traps `BR_TRAP_HOST` at
the first service call and stops.

So the runner stands that fabric up on the package's own **memory adapter**:
four guest storage objects, a bounded console in and out, a monotonic counter,
a seeded entropy source, a clock, and the device-call path — all of it in the
process's own memory. No file is opened, no socket exists, and nothing is
written to disk to make it work. That is what makes the studio runnable
wherever the C core compiles, and it is why the runtime is delivered as a
container rather than as a library.

Two backend kinds, and the difference is the point:

| backend | behaviour |
|---|---|
| `--adapter memory` | entropy and clock seeded per run |
| `--adapter deterministic` | the replay substitutes: two runs of one image produce identical fabric bytes |

### The host side of the fabric

A device with no host on the other end is half a device. Three switches
complete it:

```
studio.cmd run app --console-in 48690a          bytes for CONSOLE_READ to find
studio.cmd run app --mailbox-in cafebabe        a host-owned message for MAILBOX_GET
studio.cmd run app --state keep                 carry the fabric into the next run
```

`--mailbox-in` matters more than it looks: `MAILBOX_GET` reads **host-owned**
messages only, so without it that service can only ever answer 0 — a guest
cannot receive its own `MAILBOX_PUT`. Whatever the guest does put is received
by the host after the run and reported as `mailbox_received_hex`, which closes
the loop in both directions.

`--state keep` carries the storage objects and the monotonic and clock counters
into the next run, in one small file per container under `<root>/state/`, held
outside the container so the seal is unaffected. Without it the persistent
block device is not persistent: every run starts empty, and `STORAGE_READ` can
never read what an earlier run wrote.

```
studio.cmd run counter --state keep     R3=1
studio.cmd run counter --state keep     R3=2      reading back its own writes
studio.cmd run counter                  R3=1      a default run is unaffected
studio.cmd containers --state-reset counter
```

Keeping state is a decision per run, never a default, because a run that
silently depends on an earlier one is not reproducible. A container can declare
that it needs it — `studio new ledger --state keep` — and then say so in its own
manifest before it is installed anywhere.

Every run reports what the fabric holds afterwards:

```
studio.cmd run fabric_app --adapter deterministic --seed 7
  fabric_app: OK trap=0 in 0.002s (DEVELOPMENT_RAW, deterministic backend in RAM)
    registers  R0=0 R1=4 R2=0 R3=825377104
    fabric     console 4 byte(s) 'PA21', 1 storage object(s) written, monotonic 0
```

and an application can assert on it:

```json
"expect": { "status_name": "OK", "trap": 0,
            "fabric": { "console_out_text": "PA21", "console_out_bytes": 4 } }
```

`--console-in <hex>` hands bytes to the guest's console before it runs;
`--devices` configures the optional network and wall-clock extension devices,
which are absent by default exactly as the package specifies.

---

## Every project is a container

`studio new <name>` does not create a folder of loose files. It creates a
container, in the same format and with the same seal file the runtime container
uses, in the studio's own registry:

```
containers/<name>/
  CONTAINER.json            identity, capabilities, fabric requirement, digests
  RELEASE_CONTENTS.sha256   every file in the container, hashed
  README.md                 generated: what it is and what it needs
  src/main.lctlc            the source of record
  image/<name>.brimg        the compiled image, after `studio build`
  image/<name>.provenance.json
  image/<name>.brir.json
```

It is sealed from creation, in state `SOURCE_ONLY`, and becomes `SEALED` once
built — at which point the manifest carries the image's own digest. The
container declares the services its source actually calls, read out of the
source rather than typed by hand:

```json
"capabilities": ["CONTROL", "MEMORY", "SERVICE", "STATE"],
"services": ["CONSOLE_WRITE", "STORAGE_WRITE", "STORAGE_READ", "MONOTONIC"],
"fabric": { "devices": ["console", "monotonic state", "persistent block"],
            "adapter": "memory", "backend": "RAM" }
```

so a container says which devices the host must stand up **before** it is
installed, instead of trapping when it is run.

```
studio.cmd containers --verify          # every container, seal and gate re-derived
studio.cmd containers --pack pricing    # -> pricing_0.1.0.pa21c, one file
studio.cmd containers --install X.pa21c # verified on the way in, or refused
studio.cmd containers --remove pricing  # removes exactly that container
studio.cmd run pricing                  # by name, from the registry
```

`REGISTRY.json` is rebuilt from disk on every change, never appended to, so it
cannot describe a container that is no longer there. A container whose files
have been edited fails its seal, and **`run` refuses it** until it is rebuilt —
including a file *added* to it, which a verifier that only walked the seal
would miss.

---

## How you actually work

**The container comes first, and then you never leave it.** It is the project
folder — you edit inside it with whatever you write in.

```
studio.cmd new pricing --template fabric     # the container now exists, sealed
notepad %LOCALAPPDATA%\PA21LanguageStudio\containers\pricing\src\main.lctlc
studio.cmd run pricing --build               # build from what you just saved, then run
```

Or leave the loop running and just keep saving:

```
studio.cmd watch pricing
  watching: …\containers\pricing\src — save to rebuild
  built: 224 bytes, sealed
  ran: OK trap=0 R0=0 R1=4 R2=0 R3=825377104
```

Every save rebuilds, re-seals and re-runs, and a source the compiler refuses is
printed and the loop keeps going — that message is the reason to have the loop.

### Editing does not break anything

A container you are editing is in state **DRAFT**, and the studio says so:

```
pricing   0.1.0   DRAFT   edited since build   gate ok   console, persistent block
          next: studio build pricing
```

DRAFT is not damage. It means the image on disk came from the previous version
of the source, so `run` will not quietly execute stale code — it tells you, and
offers `run --build`. A change to anything *outside* `src/` is a different
verdict, **BROKEN**, because that is the artifact moving under its own manifest
rather than an author at work.

| state | meaning | next |
|---|---|---|
| `SOURCE_ONLY` | written, never built | `studio build` |
| `SEALED` | the image on disk came from the source on disk | `studio run` |
| `DRAFT` | you have edited since the last build | `studio build`, or `run --build` |
| `BROKEN` | something outside `src/` no longer matches the seal | rebuild, or restore |

### Code you already have, or code something else writes

You do not have to start from a template. Point the studio at a file, or pipe
it in:

```
studio.cmd new pricing --from C:\repo\pricing.lctlc
mygenerator.exe | studio.cmd new pricing --from -
```

Either way you get a sealed container around it, and the same
build / run / pack / import path as everything else. That is the answer for a
scripter or a code generator: it writes source, the studio wraps it in a
container, and nothing downstream needs to know which one produced it.

### Where a repository fits

A container **is** the unit to commit. `containers/pricing/` holds the source,
the manifest, the seal, and the built image; check that directory into your
repository and a clone can `studio containers --install` it, or just build it.
`RELEASE_CONTENTS.sha256` changes on every build, so a diff shows exactly which
files a build moved.

---

## Scripting it

### Python

```python
from pa21studio import Studio

s = Studio()                                   # or Studio("/path/to/root")

if not s.status()["installed"]:
    s.install(vm_source="Large.zip", pa21_root=r"C:\Users\you\Desktop\PA21.2")

s.new_app("pricing", template="fabric", requires_operational=[181, 209, 262])
s.build_app("pricing")                         # compiles, folds in, re-seals
r = s.run_app("pricing")                       # refuses if the seal is broken

s.list_containers(verify=True)                 # what this studio holds
s.pack_container("pricing")                    # -> one .pa21c file
s.import_container("elsewhere/other.pa21c")    # verified, or refused

assert r["ok"], r
print(r["registers"]["R2"], r["status_name"], r["execution_mode"])
```

Every method returns a JSON-serialisable dict. Refusals raise `StudioError`
with a `.detail` mapping. Nothing prints unless you pass `on_event=`.

### Any other language

```
studio.cmd --json status
studio.cmd --json install --vm Large.zip --pa21 "C:\...\PA21.2"
studio.cmd --json new pricing --template loop --requires 181 209 262
studio.cmd --json build pricing
studio.cmd --json run pricing          # exit 0 only if it met its expectations
studio.cmd --json uninstall
```

Exit codes: `0` it happened · `1` it did not, and the JSON says why · `2` the
request was malformed.

`examples/embed_studio.py` is a complete host application doing exactly this.

`--json` may go before or after the verb. `studio --json describe` and
`studio describe --json` are the same request.

---

## Letting something else write the code

A person can read this file. A generator, a script or a model has only what
the studio will tell it in one call, and can only act on what a failed attempt
returns. So the studio hands over three things, and nothing else is needed.

**The contract, in one call.**

```
studio.cmd describe --json
```

That is the whole language as the installed runtime defines it — the opcode
list, the service table, the capability each opcode class requires, the limits,
the arity of every opcode — read out of the runtime's own `tools/lctl430.py`
and `src/brvm.h` rather than restated here, so it cannot drift from the
compiler that will judge the result. Alongside it: the three preamble lines a
first attempt always omits, one worked example that is known to compile, the
per-service operand convention (what `ra` holds, what `rb` holds, what the
destination register means — and which services never write it at all), and
the refusal table.

**One call to try something.**

```
type candidate.lctlc | studio.cmd try --from - --json
```

The candidate is built and run in a scratch container that is deleted again,
so iterating fifty times leaves nothing behind. The answer says whether it
compiled, what the compiler refused if it did not, what the run did, and what
every register held afterwards — all sixteen, because a service writes its
result into whichever register the row named.

**Errors you can act on.**

A refusal comes back with the rule it broke and the correction:

```json
{"compiled": false,
 "error": "ERROR: row outside table",
 "hint": {"means": "a row appeared before the column header line",
          "do": "emit the three preamble lines in this description …"}}
```

And the failure a status code cannot show — a program that compiles, runs to
`HALT`, returns trap 0, and does nothing — is named rather than left to be
noticed:

```json
{"status_name": "OK", "trap": 0,
 "effects": {"observed": {"MAILBOX_PUT": {"bytes_returned": 8}},
             "quiet": [{"service": "CONSOLE_WRITE",
                        "why": "nothing reached the console",
                        "do": "the length register was zero, or the offset
                               window held no bytes …"}]}}
```

`observed` is what the run visibly did. `quiet` is every service call that ran
and left no trace, with the reason — usually an operand convention rather than
a syntax error, which is exactly the class of mistake a compiler cannot catch.
`studio run` reports the same block for a built container, so a promoted
candidate behaves no differently from the scratch it came out of.

When the candidate is right:

```
type candidate.lctlc | studio.cmd try --from - --keep pricing
```

which promotes it into the registry as a sealed container, identical to one
made any other way.

`studio explain "<message>"` maps a refusal to its rule on its own, for a
caller holding an error from somewhere else.

### The description is checked, not asserted

The ledger's rule is that nothing is operational because a file says so. The
studio's description of the language is a file, so it gets the same treatment:

```
studio.cmd abi
[HOLDS   ] MAILBOX_GET    a host-delivered message is copied into guest memory …
             the four delivered bytes are in guest memory and R2 is 4
[HOLDS   ] STORAGE_WRITE  … and the destination register is NOT written
             object 1 holds a frame, object 0 does not, and the sentinel in R2 survived
14/14 claims demonstrated
```

Each claim is a small program that exercises one service and asserts what the
description says will happen — the register that must hold a byte count, the
register that must be untouched, the bytes that must appear in the fabric. A
claim that cannot be demonstrated is reported UNPROVEN with the reason rather
than quietly dropped. Writing this found one wrong sentence immediately: the
description said a `YIELD` ends the run "SUSPENDED, not OK", and the runtime
actually ends it with `machine_status` SUSPENDED while `status_name` stays OK.
Two fields, and only one of them changes.

### When it traps, it says where

```
studio.cmd run pricing --trace
  pricing: STATE trap=6 in 0.003s (SIGNED_VERIFIED, deterministic backend in RAM)
    trapped    DIV_ZERO at row C (DIVU), source line 6: C│exec│DIVU│R2│C0:ARITH│R0›R1│_│_
               the VM logged DIV_ZERO at row C (line 6)
    trace      step 0: row A MOVI — A│exec│MOVI│R0│C0:CONTROL│_│imm=7│_
    trace      step 1: row B MOVI — B│exec│MOVI│R1│C0:CONTROL│_│imm=0│_
    trace      step 2: row C DIVU — C│exec│DIVU│R2│C0:ARITH│R0›R1│_│_
```

The trap frame and the diagnostics ring are the VM's own records; the row and
line come from the BRIR the compiler emits. Nothing is reconstructed — two
records the system already keeps are joined. `--trace` runs the same executor
one instruction at a time through the VM's own step, so the trace is what
happened rather than a simulation of it.

---

## Containers as a regression suite

A container that declares what it does is a test. Recording that declaration
is one command:

```
studio.cmd expect pricing            record what it does now as what it should do
studio.cmd test                      run every container against its own answer
```

```
[PASS           ] counter
[FAIL           ] pricing              registers.R2: expected 42, got 54
[NO_EXPECTATION ] sketch               this container does not declare what it should do
1 pass, 1 fail, 1 no expectation
```

A container may declare a trap as its answer: one that demonstrates a
`DIV_ZERO` is right when it traps and wrong when it does not.

Expectations are captured on the deterministic adapter and from a fresh fabric,
because an expectation taken from a run that carried the previous run's state
describes that moment rather than the container — and they are checked on the
same terms they were captured on. A container with no declared answer is
reported, not passed: silence is not success.

---

## Signed images

Where the host has OpenSSL, the studio builds the runtime's own `brctl`,
generates an Ed25519 key at install, signs every image it builds, and the VM
verifies that signature **through the HAL, before the first instruction runs**.

```
studio.cmd status
  execution       SIGNED_VERIFIED
  signing         images are signed at build and verified before they run

studio.cmd run pricing
  pricing: OK trap=0 in 0.005s (SIGNED_VERIFIED, deterministic backend in RAM)

studio.cmd run pricing --unsigned
  pricing: OK trap=0 in 0.003s (DEVELOPMENT_RAW, deterministic backend in RAM)
```

The package's own signing path uses the POSIX adapter, which keeps its state in
files, so signed images and the RAM fabric looked mutually exclusive. They are
not: the HAL is a table of function pointers, and the studio's runner is the
memory HAL with exactly one entry replaced by an Ed25519 verify. Storage,
console, entropy, clock and mailbox are still the package's own RAM
implementations, byte for byte.

A flipped byte in a signed image is refused before execution
(`SIGNATURE_REFUSED`), and so is an unsigned image where a signature is
required. The install proves both rather than claiming them.

**Trust is separate from integrity.** A container built elsewhere carries the
public key it was signed with, and this studio has never seen that key — so it
runs on the raw path and says why:

```
studio.cmd run imported
  unverified this container was signed with a key this studio does not trust;
             run `studio trust imported` to accept it
studio.cmd trust imported
studio.cmd run imported
  imported: OK trap=0 (SIGNED_VERIFIED, …)
```

The private key is generated in the studio root, never leaves it, and is never
packed into a container.

---

## What runs where

```
studio.cmd doctor
  Linux 6.18, Python 3.11, /usr/bin/cc (unix)
    ok  paths_with_spaces_and_non_ascii: sealed and re-verified 1 file(s)
    ok  seal_uses_forward_slashes: a seal written on one platform is readable on the other
    ok  vm_core_selftest_here: PASS
    untested: the Windows entry points and the %LOCALAPPDATA% root: written,
              and not executed on this host, which is Linux
```

Three separate things: what is present, what was exercised here just now, and
what this host cannot demonstrate. Every build line goes through one place that
speaks both dialects — `cc`/`gcc`/`clang` and MSVC `cl.exe` — so adding a
compiler is one change rather than three. On Windows with MSVC the runner
builds and `brctl` does not, because `brctl` is POSIX C: signing there needs a
MinGW toolchain, and the studio says that instead of failing the install.

An untested item is not a broken one. It is one this host cannot demonstrate,
and the studio would rather say so than imply otherwise.

---

## The fabric as a picture you can run

A distributed fabric language's state is a spatial field, not a scalar — so the
studio can persist a container's device fabric as a **tiled TIFF**, and run the
language *both directions*: it writes the image from a run, and reads the image
back as the state of the next run.

```
studio.cmd new grid --template field       a container whose state changes each tick
studio.cmd build grid
studio.cmd fabric init grid                the fabric becomes a .tif
studio.cmd fabric live grid --ticks 20     read it, run it, write it back, repeat
studio.cmd fabric view grid                render the current field as a PNG
studio.cmd fabric frames grid              the immutable frame history
```

The four guest storage objects are laid out as tiles of one raster: a cell's
position in the fabric **is** its position in the picture — shards are tiles.
The counters and non-guest slots are scalar, so they ride as private TIFF tags
rather than pixels. Every tick is appended as a new page, so the file is a
frame-by-frame record of the fabric evolving.

**It is reversible, and that is the point.** The map fabric↔image is a bijection
over the guest-visible payloads, so the loop is a fixpoint: image in, execute,
image out, and the next tick reads whatever the image now says. That includes
an edit made to the image *from outside* while the loop runs — paint a cell in
the `.tif` and the next tick executes it. The verifier proves exactly this:
it paints the counter cell in the image to 200, and the next run advances it to
201. The image is the live state, in constant flux, which is what a distributed
fabric demands.

One honesty note: the editable fabric is the guest **payload**, not the VM's
framed storage wrapper. The VM wraps a stored object in a content-hashed frame;
that hash is integrity over the frame, not user data, and painting raw pixels
over it would break it. So the image holds payloads and the VM reframes them on
read — which is why an outside edit is adopted rather than rejected.

The whole subsystem depends on nothing but Pillow, which the studio already
uses for the window, so a container's fabric image works wherever the studio
runs.

---

## What it corrects for you

Naming a correction and applying it are different promises. Where a refusal
admits exactly one legal edit — the column header row goes in one place,
`@unit version` has one legal value, ARG keys have one legal order, a source
operand separated by a comma was meant to be separated by U+203A — the studio
makes the edit itself:

```
studio.cmd fix --from pricing.lctlc --write        # correct the file in place
studio.cmd try --from - --fix                      # correct, then compile and run
studio.cmd watch pricing --fix                     # correct on every save
generator.exe | studio.cmd fix --from - | studio.cmd try --from -
```

It reports every edit it made, with the refusal that prompted it:

```
fixed: ERROR: bad register R0,R1
  line 6: source operands 'R0,R1' were not separated by U+203A; wrote 'R0›R1'
fixed: ERROR: MUL: declared capability CONTROL, expected ARITH
  line 6: MUL declared CONTROL; its opcode class requires ARITH
fixed: ERROR: MUL: capability ARITH exceeds @unit declaration
  added ARITH to br_request_caps; a row uses it and the unit had not asked for it
  the source compiles
```

Three rules keep this honest. **Only determinate corrections** — sixteen of
them, listed under `repair` in `studio describe --json`. **Every edit is
reported**, never applied silently. And **the compiler decides**: each round
applies one correction and asks the runtime's own toolchain again, so nothing
here holds an opinion about whether a program is valid.

What it will not do is guess. `MOVI requires imm` needs a number only the
author knows; `invalid opcode MULTIPLY` would need a guess at which opcode was
meant; renumbering a duplicate row ID would silently redirect every branch to
it. Eleven refusals are declined on purpose, each with the reason, and they are
listed in the same place:

```
still refused: ERROR: MOVI requires imm
  not mine to fix: the immediate is a value only the author knows
```

`studio fix` writes the corrected source to stdout and the account of what
changed to stderr, so it composes in a pipeline; `--write` puts it back over
the file instead.

---

## The PA21 bridge

An application declares the ledger items it depends on:

```json
{ "name": "pricing",
  "entry": "src/main.lctlc",
  "budget": 4096,
  "pa21": { "requires_operational": [181, 209, 262] },
  "expect": { "status_name": "OK", "trap": 0, "registers": { "R2": 55 } } }
```

Before running, the studio reads the bound delivery's newest capability ledger
and checks that **every** declared item is `OPERATIONAL`. If one is not — or if
the ledger has never heard of it — the run is refused with the item, its actual
status, and the round the ledger belongs to. The gate fails closed, and it
fails *before* anything is executed.

```
studio.cmd ledger --item 181 206      # what the delivery says about an item
studio.cmd seal --pa21 "C:\...\PA21.2"  # re-derive SHA256SUMS for every package
```

`expect` is the application's own contract: `run` compares the machine's
registers, status and trap against it and exits non-zero when they differ, so a
build pipeline can gate on `studio run` alone.

---

## What it does not claim

**A verified signature is not a provisioned trust chain.** Where the host has
OpenSSL, images are signed and the VM verifies that signature before executing
them, and results say `SIGNED_VERIFIED`. That proves the image was signed by a
key this studio trusts and has not changed since — it is not the package's
BRTM/1 production trust chain, which requires a provisioning path the package
does not expose. Loading is still the development raw-load path the package's
own test binaries use, with a signature check in front of it. Where the host
has no OpenSSL, nothing is signed, every result says `DEVELOPMENT_RAW`, and the
studio says why.

**Compiling is not executing.** On a machine with no C compiler the studio
installs anyway and says so: images can still be compiled, their provenance
verified, and their structure checked — they just cannot be run there. On a
machine with no OpenSSL development headers, image *signing* and authenticated
state (the package's own `brctl`) are unavailable; running is not affected.

---

## Writing an application

Four rules the compiler enforces, and the scaffolds already obey:

1. `@unit version` is the **language** revision — `4.3.0` — not your
   application's version. Put your version in `pa21app.json`.
2. Source operands are separated by `›` (U+203A), not a comma:
   `R0›R1`.
3. Every row names a capability register and a capability, the capability must
   be the one the opcode class requires (`ARITH` for arithmetic, `CONTROL` for
   flow, `MEMORY` for loads and stores, `SERVICE` or `STATE` for service
   calls), and it must also appear in the unit's `br_request_caps`. A unit
   whose control flow contains a loop must declare `termination=budgeted`.
4. `ARG` keys are lexically ordered — `offset=0;svc=STORAGE_WRITE`, not the
   reverse. A service call passes the guest-memory offset and the transfer
   length in its two source registers and names the storage object in
   `offset=`.

```
studio.cmd templates
# hello   arithmetic
# loop    counted loop (declares termination=budgeted)
# fabric  console + persistent block + monotonic, on the RAM backend
# memory  guest-memory round trip
```

---

## Checking the studio itself

```
python3 verify_studio.py --vm Large.zip --pa21 "C:\...\PA21.2"
```

132 checks: it performs a real install into a scratch root, compiles and runs
real images, exercises the device fabric (console, block round trip, monotonic)
and confirms nothing reached the disk to achieve it, shows the deterministic
backend replaying byte-for-byte, creates a project and checks it is a sealed
container, breaks that seal two ways and confirms the studio refuses to run it,
packs it, imports it into a second studio and runs it there, refuses a tampered
archive, edits a source and confirms the studio calls that a DRAFT rather than
damage, runs the save-driven authoring loop and checks the answer changed with
the code, flips a byte in an image to confirm verification fails, compiles the
example the description carries and confirms a program written from `describe`
alone runs, checks that a refusal comes back with the rule it broke and that a
run which succeeds while doing nothing is reported as such, promotes a candidate
into a sealed container, breaks a source ten separate ways and confirms each
one is repaired and reported, confirms two refusals it must decline are
declined with a reason, runs one image three times to confirm the persistent
block device is persistent and a fresh run is not, sends a message from the
host into the guest and back out again, demonstrates all fourteen ABI claims
the description makes, records a container's run as its expectation and then
breaks the container to confirm the suite catches it, signs an image and
confirms the VM refuses a flipped byte in it before execution, imports a
container signed by another studio and confirms it runs unverified until its
key is trusted, traps a program on purpose and checks that the failure names
the row of source that did it, exercises every refusal, uninstalls, and then
looks at the disk to confirm that what it created is gone and what it did not
create is still there. Exit 0 only if all of them pass.

---

## The window

`INSTALL.cmd` opens it. Three modes: **Install**, **Containers**, **Remove**.
The Containers view creates a project from a template, then builds, runs, packs
or removes it, showing each container's state, seal and PA21 gate — and the
run's console output, storage and register state in the drawer. It binds
`127.0.0.1` on an ephemeral port with a single-use token in the URL, so nothing
else on the machine — or off it — can drive an install. It shows the plan before
the action, streams each step as it happens, and keeps the receipt.
