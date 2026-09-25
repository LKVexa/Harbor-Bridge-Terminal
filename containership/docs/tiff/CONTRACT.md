# UC-2.5.0 TIFF/GIF pixel-state contract

## Implemented local profile

The live state remains **PA21FABTIF/1 TIFF**. A container tick reads this image, reconstructs PA21FAB1 logical state, executes the existing native VM, and writes a validated new TIFF page. The implementation adds a bounded binary admission layer, a minimal raster-only decoder adapter, reversible GIF transport, and checked pixel-cell operations. It does not replace the native engines or introduce a new bootable operating-system kernel.

The four logical tiles are 16 × 8 RGBA8 pixels each. Each holds 512 raster bytes, but native guest payload capacity is **464 bytes / 58 little-endian u64 words** because the VM's full storage record reserves framing and integrity bytes. The default grid is 2 × 2 tiles, giving a 32 × 16 image. Hull codec layouts with 1–4 columns are supported; ship-managed state requires the default 2-column layout. Scalar slots 0, 1, 6 and 7 reside in bounded metadata, not editable raster cells.

## TIFF admission and reconstruction

Inputs are read as bounded immutable snapshots. Directory, tag and strip/tile spans are checked before the raster decoder is called. Classic TIFF and BigTIFF headers are parsed in both byte orders. BigTIFF support here means checked 64-bit directory addressing **within the local 8 MiB input limit**, not multi-gigabyte or out-of-core processing. The writer emits classic TIFF, not BigTIFF.

The profile accepts chunky unsigned RGBA8, RGB photometric interpretation, unassociated alpha and top-left orientation. Raw, LZW, Deflate and PackBits are allowlisted; other color models and lossy compression are refused. Sample/color conversion, quantization and implicit alpha association are not performed. Strip and tile storage layouts are supported independently of the logical tile grid. TIFF predictor admission is limited to values 1 and 2; codec execution is delegated to Pillow/libtiff. No custom LZW, zlib, SIMD, LERC or predictor encoder is claimed.

Only validated decode-critical tags and the original compressed raster blocks are copied into a minimal, single-page classic TIFF for Pillow. This excludes private metadata from the decoder's input and avoids the installed Pillow 12.3.0 big-endian BigTIFF header limitation observed during independent fixture testing. Eight independently generated fixtures exercise classic/BigTIFF × little/big endian × strips/tiles. The independent encoder is a test dependency, not part of the runtime.

Limits are cumulative, not alternative allowances:

| Resource | Limit |
|---|---:|
| Input/output TIFF or GIF | 8 MiB |
| History pages / GIF frames | 512 |
| Tags per TIFF IFD | 128 |
| Individual TIFF tag payload | 65,536 bytes |
| Cumulative decoded tag payloads | 4 MiB |
| Decoded TIFF raster per page | 4,096 bytes |
| Compressed raster bytes per page | 65,536 bytes |
| Scalar slot | 4,096 bytes |
| Pixel patch batch | 1,024 operations |

Duplicate/unordered tags, IFD cycles, overlapping raster/metadata spans, invalid dimensions, invalid scalar hex, duplicate JSON keys, non-finite JSON constants and conflicting state/tick metadata mirrors are rejected. Header version, counters, tile lengths and all offsets are checked without silent truncation or numeric masking.

A full BRO1 VM storage record is validated by version, object identity, length and SHA-256 before its guest-visible payload is represented in the TIFF. Short user payloads beginning with the letters BRO1 are not mistaken for frames. **Logical state** is reversible; private BRO1 wrapper bytes are deliberately normalized, not preserved as editable pixels. Digests detect inconsistency; they do not authenticate a maliciously rewritten image.

## History, commit and checkpoint

Page zero is newest. History frames retain their own tick, counters, scalar metadata and exact logical state. Missing or malformed history metadata is an error; the writer does not invent or silently discard it. The writer encodes and validates every output page before a same-directory replacement. Optional expected-file SHA-256 checks reject stale cooperative writes.

The ship CLI holds its existing workspace lock. Live `pixels paint` and `pixels checkpoint` additionally use the existing generation-aware managed transaction layer. The standalone codec's optimistic digest checks are not a lock against hostile filesystem peers. No guarantee against all symlink-replacement races or power-loss scenarios is claimed. Rename is the commit point; an error during post-rename directory synchronization can occur after replacement. Managed CLI transactions can restore their protected files; native/external side effects are outside that rollback guarantee.

A full history is refused before another hull VM tick starts. An explicit checkpoint validates all old frames, preserves the complete TIFF in a content-addressed archive under `_runs/pixels`, verifies that archive, then atomically reduces the live TIFF to its unchanged newest logical state and tick. It is never automatic truncation. Archives require operator-managed retention and disk space; the release does not include a new global disk quota service.

## Reversible GIF transport

**UC/FABRIC_GIF/1** is a restricted GIF89a state-transport profile, not arbitrary artwork import and not the live execution format. Each grayscale palette index is one exact byte of the logical PA21FAB1 state. The complete blob, including counters and scalar slots, is present in each frame. This is an encoded state visualization, not a color-faithful screenshot of the RGBA TIFF.

Each frame has independent bounded JSON metadata, a SHA-256, a full-screen image and deterministic byte palette. Cropping, transparency, interlacing, per-frame palettes, unknown extensions and missing metadata are refused. Frames are encoded separately so equal raster states are not merged. The sequence is newest-first, matching TIFF history. A conventional GIF viewer may display the byte planes but cannot validate the state contract. Re-saving through an image editor may remove metadata or alter indices; such files are not trustworthy state backups.

GIF export does not change live TIFF state. Restore validates every GIF frame and writes a separate, previously nonexistent TIFF file. It does not adopt, activate or overwrite a live berth. Operators must review any later state-adoption decision separately.

## Pixel execution semantics

`pixel_kernel.py` implements deterministic local CPU `set`, `add` and `xor` operations on u64 cells. Inputs must be actual nonnegative Python integers, not booleans, strings or floats. Addition rejects overflow unless the operation explicitly requests wrapping. Batch edits are prepared on a private copy and returned only when every operation succeeds. Optional logical-state hashes and expected-cell values provide compare-and-swap checks. Results expose changed tiles, before/after values, cell-to-pixel coordinates and logical-state digests.

The active ship `paint` path calls this kernel, replacing silent u64 masking and over-capacity writes. Native ticks still execute the unchanged four DF engines from the supplied hold. This is not GPU acceleration, a new machine ISA, a hypervisor or an independently bootable unikernel.

## Trust and unimplemented scope

The VWS terminal exposes only read-only `pixels status`, `pixels inspect`, `pixels cell` and `tiff-workflow status` commands. Pixel edits, exports, checkpoints and restoration remain explicit local CLI operations, even when the terminal is launched in control mode. Existing credential, generation, deadline, output and cancellation boundaries remain in place.

No OME/GeoTIFF scientific interpretation, COG server, Zarr/Xarray/Dask backend, distributed execution, cloud storage, SIMD/GPU pipeline, arbitrary image filtering, public deployment qualification, Windows-native execution evidence, browser UI evidence or native-child CPU/memory quota enforcement is claimed. Pillow/native codecs still run in a host process; binary admission is not a decoder sandbox.
