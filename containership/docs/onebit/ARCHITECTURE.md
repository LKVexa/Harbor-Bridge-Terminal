# UC-2.6.0 1-bit communication architecture

UC-2.6.0 applies the attached JYRM 1BNCF v3.1.0 series as a **bounded communication subsystem**. It does not turn local computation or cognition into 1-bit arithmetic. Residuals, scale estimation, momentum, monitoring, recovery decisions and reductions remain full precision.

## Wire profile

`UC1B` v1 uses a little-endian fixed header carrying version, flags, header length, sequence, source ID, destination ID, scalar count, an IEEE-754 binary64 scale sideband and CRC32. The sign payload is canonical LSB-first: `1` means nonnegative and `0` means negative; zero is encoded as `1`. Unused high tail bits must be zero. The packet is rejected on count/length disagreement, unsupported header fields, non-finite/negative scale, bad tail bits or CRC mismatch.

`UCFP` v1 is the guarded FP32 reference/fallback transport. It carries the same routing/order metadata and CRC. Local controller state remains Python double precision.

## Controller

Each logical channel starts in WARMUP and sends FP32. Stable scale evidence permits ONE_BIT. Error feedback adds the prior residual before quantization. Adaptive scale is bounded against the warmup reference and against the prior step. Compression error, bit balance and scale behavior are monitored. A failed probe immediately transmits the original block by FP32, enters RECOVERY and retains an auditable transition. Checkpoints are SHA-256 protected and deterministic replay is tested.

## TIFF/GIF state integration

A 1-bit packet can be carried in the existing TIFF fabric tile payload. The native tile budget is 464 bytes, allowing at most 3,392 scalars in this wire profile. A live `tiff-put` requires current generation fencing and exact TIFF digest, and refuses to overwrite a non-empty tile unless that tile is already a valid UC1B carrier. GIF remains the existing reversible offline transport; it is not used as a live communication wire.

## Boundaries

The local profile has an in-memory bounded backend and local routing/reduction helpers. It does not claim NCCL/GPU execution, TCP networking, Windows named-pipe qualification, JA21/QAM/FXSpot/Junkyard adapters, JYRM neuron groups, or model-level convergence/equivalence. Those source components remain blocked.
