# berth `vm_large` -- vm

UC-2.1.3. This is the project's own blank four-node-plus-fabric scaffold, loaded: 893 scripts
(4241632 bytes) from `Large.zip` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
| `DF_Small/` | `N_SMALL` | 438 | 447377 | `d20fee1bb860e01e...` |
| `DF_Medium/` | `N_MEDIUM` | 359 | 3387916 | `131e186314efb01d...` |
| `DF_Large/` | `N_LARGE` | 41 | 235863 | `cdb7b5dd886ec2a1...` |
| `DF_Xtra_Large/` | `N_XLARGE` | 55 | 170476 | `ed2acabdb7327ec4...` |
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, 901 rows (one per script), seal `6c28234553fa0da2...`,
  reference witness `11338925930947832812`, executed on the engines in 11 segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in 22 rows, seal `d24d263f7ec98344...`, reference witness `15355811372695196182`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

Every container here has **its own .tif fabric** (UC-2.1.3): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/berth_vm_large.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run vm_large                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run vm_large --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live vm_large
../../uc.py verify vm_large                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
