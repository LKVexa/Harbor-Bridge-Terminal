# berth `vm_medium` -- vm

UC-2.1.3. This is the project's own blank four-node-plus-fabric scaffold, loaded: 241 scripts
(1513315 bytes) from `Medium.zip` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
| `DF_Small/` | `N_SMALL` | 96 | 142697 | `c4917a9bb34d6b90...` |
| `DF_Medium/` | `N_MEDIUM` | 61 | 518146 | `78d177a37437763e...` |
| `DF_Large/` | `N_LARGE` | 30 | 504357 | `39b375ca47d08391...` |
| `DF_Xtra_Large/` | `N_XLARGE` | 54 | 348115 | `a9ef1f12c5a4e891...` |
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, 249 rows (one per script), seal `6a4841593cf9f2df...`,
  reference witness `75913186513227538`, executed on the engines in 3 segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in 22 rows, seal `54a62a08addfa1df...`, reference witness `14203227011441505260`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

Every container here has **its own .tif fabric** (UC-2.1.3): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/berth_vm_medium.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run vm_medium                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run vm_medium --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live vm_medium
../../uc.py verify vm_medium                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
