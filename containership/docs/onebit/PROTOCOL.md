# UC1B protocol contract

- Wire version: 1.
- One-bit magic: `UC1B`; fallback magic: `UCFP`.
- Byte order: little endian.
- Bit order: LSB-first within each byte.
- Sign mapping: 1 = value >= 0, 0 = value < 0.
- Zero: encoded as positive sign bit; zero scale reconstructs zeros.
- Scalar limit: 65,536 per general packet.
- TIFF carrier limit: 464 packet bytes / 3,392 one-bit scalars.
- Integrity: CRC32 covers a zero-CRC canonical header plus payload; SHA-256 is reported for evidence and checkpoint identity.
- Ordering: unsigned 64-bit sequence number; receiver can enforce an exact expected sequence.
- Addressing: unsigned 32-bit source and destination IDs.
- Scale: finite, non-negative binary64 sideband; local residual/error compensation remains full precision.
- Tail bits: unused bits in the final packed byte must be zero.
- Fail closed: malformed, truncated, oversized, noncanonical, stale or corrupt packets are rejected.
