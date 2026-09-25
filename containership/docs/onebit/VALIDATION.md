# UC-2.6.0 1-bit validation scope

Validation covers canonical packing/unpacking, CRC refusal, FP32 fallback, warmup and transition logic, residual feedback, adaptive scale bounds, routing, bounded in-memory backpressure, TIFF packet capacity and round trip, recovery, checkpoint integrity, deterministic replay, A/B reconstruction accounting and byte/effective-bit accounting.

The full Python regression suite, VWS Node suite, workflow source integrity checks and fresh-extraction checks are release evidence. Passing these tests does **not** qualify absent JYRM model training, NCCL/GPU, public networking, Windows named pipes, external product adapters, or end-to-end model quality.
