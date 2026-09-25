# berth `vm_small` -- vm

UC-2.1.3. This is the project's own blank four-node-plus-fabric scaffold, loaded: 20 scripts
(109905 bytes) from `Small.zip` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
| `DF_Small/` | `N_SMALL` | 9 | 6944 | `cf7a2d33ce9b39d1...` |
| `DF_Medium/` | `N_MEDIUM` | 2 | 2335 | `712f38e504c9df05...` |
| `DF_Large/` | `N_LARGE` | 8 | 100450 | `748f7894fedbfc57...` |
| `DF_Xtra_Large/` | `N_XLARGE` | 1 | 176 | `a6a6afc6cc4bbd5a...` |
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, 28 rows (one per script), seal `7b47f4d2aa71b9e1...`,
  reference witness `9816649208978189246`, executed on the engines in 1 segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in 22 rows, seal `b15145bb44075b3c...`, reference witness `15298326914918377449`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

Every container here has **its own .tif fabric** (UC-2.1.3): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/berth_vm_small.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run vm_small                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run vm_small --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live vm_small
../../uc.py verify vm_small                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
