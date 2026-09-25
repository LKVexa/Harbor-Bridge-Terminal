# CHERI specification pin (INV30-GAP-005 · INV-30-C031, C084, C093)

**Status: PROPOSED — requires owner approval (SIGNOFFS `architecture_approver`) and confirmation of the exact
current releases at approval time.**

| Item | Proposed pin |
|---|---|
| Normative ISA | *Capability Hardware Enhanced RISC Instructions: CHERI ISA, Version 9*, University of Cambridge Technical Report UCAM-CL-TR-987 |
| Architecture profile A | Arm Morello (Armv8.2-A + Morello capability extensions), per Arm's *Morello Architecture Reference Manual Supplement* |
| Architecture profile B | CHERI-RISC-V (RV64 with CHERI extensions) as specified in ISA v9; track the RISC-V International CHERI standardisation for a later re-pin |
| Capability format | 128-bit compressed capabilities + 1 tag bit (64-bit address space) |
| ABI | pure-capability (purecap) for the native helper; hybrid ABI not supported for enforcement |
| Toolchain | CHERI LLVM/Clang (CTSRD release matching the chosen CheriBSD) |
| OS | CheriBSD release current at approval (record exact version + commit here) |
| Emulator (dev/CI only) | CHERI-QEMU from the same release train — **never** counted as production hardware evidence |

Exact version strings/commits are recorded here when a backend is built; `test_hardware_backend` records them in
evidence. Until then the hardware tier is NO_GO.
