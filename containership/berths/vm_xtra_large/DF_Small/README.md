# vm_xtra_large / DF_Small -- node slot N_SMALL

Hollow slot of berth `vm_xtra_large` (UC-2.1.3). It holds no VM: the engine is `hold/DF_Small.zip`, extracted and built once under `_engines/`. This slot holds the 3794 script(s) (5576699 bytes) the sort policy placed on `N_SMALL` (rules {"S6": 2740, "S7": 22, "S8": 1032}), under `cargo/` with their original relative paths, plus `cargo/CARGO_MANIFEST.json`, `node/NODE.pal` (this berth's declaration of the node, sealed), `SLOT.json`, and this container's own .tif fabric: `fabric/GENESIS.fabric.tif` + `fabric/FABRIC.json` (tick 0, sealed) and, once BUILD or RUN made it, the live image `_fabric/DF_Small.fabric.tif` (state, outside the seal): tile 0 the state, tiles 1-2 the berth's declaration as row-word cells, tile 3 the seals. A tick (`../../../uc.py run vm_xtra_large`) reads it, executes it on this engine, and appends a frame.

```
./RUN <cargo path>       run one runnable cargo script (dialect MSSL_ASM-1, or a .pal bundle) on the engine
./VERIFY                 the berth battery (sort ledger re-derived, seals, witnesses on the engines, studio face)
./BUILD                  the ship's BUILD (extract + build engines, install the hull)
```
