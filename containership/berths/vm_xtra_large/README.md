# berth `vm_xtra_large` -- vm

UC-2.1.3. This is the project's own blank four-node-plus-fabric scaffold, loaded: 5513 scripts
(20528603 bytes) from `Xtra_Large.zip` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
| `DF_Small/` | `N_SMALL` | 3794 | 5576699 | `de5c70bf1409183b...` |
| `DF_Medium/` | `N_MEDIUM` | 1418 | 12805475 | `0631e9447d40e1c1...` |
| `DF_Large/` | `N_LARGE` | 3 | 533608 | `5a5d0c6a3e10e734...` |
| `DF_Xtra_Large/` | `N_XLARGE` | 298 | 1612821 | `c76c85e28e776a2e...` |
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, 5521 rows (one per script), seal `86e60c88397fcf01...`,
  reference witness `18176639773570921958`, executed on the engines in 66 segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in 22 rows, seal `68f8aef74f1b3690...`, reference witness `3207394530149930380`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

Every container here has **its own .tif fabric** (UC-2.1.3): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/berth_vm_xtra_large.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run vm_xtra_large                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run vm_xtra_large --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live vm_xtra_large
../../uc.py verify vm_xtra_large                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
