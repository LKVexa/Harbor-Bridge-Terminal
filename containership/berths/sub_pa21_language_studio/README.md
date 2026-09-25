# berth `sub_pa21_language_studio` -- subsystem

UC-2.1.3. This is the project's own blank four-node-plus-fabric scaffold, loaded: 23 scripts
(478955 bytes) from `PA21_Language_Studio` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
| `DF_Small/` | `N_SMALL` | 4 | 1070 | `11089c03d82f1131...` |
| `DF_Medium/` | `N_MEDIUM` | 1 | 31213 | `04fc22d654fdb622...` |
| `DF_Large/` | `N_LARGE` | 1 | 21466 | `f925126bf87400fa...` |
| `DF_Xtra_Large/` | `N_XLARGE` | 17 | 425206 | `d0ea89811ab9ff89...` |
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, 31 rows (one per script), seal `ced34085fe28f8b5...`,
  reference witness `13787820642529720862`, executed on the engines in 1 segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in 22 rows, seal `ae178ece847b4124...`, reference witness `10906907802389691971`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

Every container here has **its own .tif fabric** (UC-2.1.3): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/berth_sub_pa21_language_studio.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run sub_pa21_language_studio                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run sub_pa21_language_studio --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live sub_pa21_language_studio
../../uc.py verify sub_pa21_language_studio                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
