# UC-2.7.0 Pixel/TIFF State Specification

## State carrier
Live execution state remains TIFF/BigTIFF. GIF is a reversible transport/history representation and is not silently activated as live state. TIFF admission validates byte order, directory structure, bounds, storage layout and payload budgets before pixel-kernel access.

## Pixel kernel ABI
ABI identifier: `UC/PIXEL_KERNEL_ABI/1`.

Supported integer operations in the bounded local kernel are `set`, `add`, and `xor` over checked unsigned 64-bit values. Coordinates and values are non-negative integers within 64-bit bounds. Unsupported operations or ABI versions are rejected.

The native tile payload ceiling is **464 bytes**. The kernel descriptor records unsupported/unfinished capabilities such as multi-tile transactions, qualified SIMD and qualified GPU execution rather than inferring them from hardware presence.

## Integrity and generations
State-changing paths use digest/generation fencing and managed checkpoints where implemented. Existing 1-bit TIFF carriers are validated before replacement; ordinary native tiles are not silently converted into UC1B packets.

## Determinism
Integer kernel semantics are deterministic for the documented operations. Cross-CPU/GPU floating-point determinism is not claimed.
