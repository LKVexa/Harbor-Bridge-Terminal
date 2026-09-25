# berth `sub_mssl_to_lctlc` -- subsystem

UC-2.1.3. This is the project's own blank four-node-plus-fabric scaffold, loaded: 1 scripts
(18488 bytes) from `uc-mssl-tool-llrw8v7k` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
| `DF_Small/` | `N_SMALL` | 0 | 0 | `e3b0c44298fc1c14...` |
| `DF_Medium/` | `N_MEDIUM` | 0 | 0 | `e3b0c44298fc1c14...` |
| `DF_Large/` | `N_LARGE` | 0 | 0 | `e3b0c44298fc1c14...` |
| `DF_Xtra_Large/` | `N_XLARGE` | 1 | 18488 | `06a5d98034bc6816...` |
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, 9 rows (one per script), seal `6f16f73dd99e9146...`,
  reference witness `3704379664640541329`, executed on the engines in 1 segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in 22 rows, seal `7782babc189c679d...`, reference witness `3765766587618232233`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

Every container here has **its own .tif fabric** (UC-2.1.3): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/berth_sub_mssl_to_lctlc.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run sub_mssl_to_lctlc                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run sub_mssl_to_lctlc --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live sub_mssl_to_lctlc
../../uc.py verify sub_mssl_to_lctlc                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
