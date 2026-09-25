# Fuzzing and property-based robustness (MC-14)

Harness: `tools/fuzz.py` (dependency-free, seeded). Targets:

| Target | Boundary | Key invariants |
|---|---|---|
| record_header | PK_CTRL_STREAM/1 header parser | typed refusal only; bound checked before allocation |
| stream_fragmented | Connection over a stream fragmented at 1..7-byte chunks | exact reassembly; clean EOF |
| stream_garbage | Connection over mutated/random bytes | no crash; tracemalloc peak <= 4 x max record |
| frame_open | PK_CTRL_FRAME/2 open (AEAD wrapper, header parse) | failed opens never move `recv_seq`; accepted frames advance by exactly one |
| session_stateful | random drop/duplicate/reorder schedules | accepted sequence strictly +1; rejects never move state |
| message_decode | PK_CTRL_MSG/1 decoder (typed schema decoder, dispatcher input) | canonical round-trip; non-canonical encodings never accepted |
| handshake | PK_CTRL_HS/1 CLIENT_HELLO + credential parser | typed `HandshakeError` only |
| config | configuration validator | typed `ConfigError` only |
| policy | policy document parser | typed refusal only |
| quarantine | directive parser/verifier | typed refusal only |

Corpus/generators: valid minimum/typical/maximum messages of every registered type, 64 KiB frames, near-2^64 sequence values (`FuzzPropertyTest.test_near_2_64_sequence_values`), truncations, overlong/huge length claims (`0xFFFFFFFF`, `0x7FFFFFFF`), zero lengths, duplicates, reordering, unknown versions/types, non-zero reserved fields, bit flips anywhere in header/ciphertext/tag, random bytes. Text fields are ASCII-restricted, so Unicode attacks reduce to rejection.

Differential testing: `test_differential_golden_frames_independent_derivation` re-derives keys and ciphertext through an independent code path and must reproduce the golden fixture bytes.

Execution: PR CI runs 300 iterations/target (property tests) + the bounded gate campaign; nightly runs 20,000 iterations/target with a date-derived seed (`.github/workflows/ci.yml`). Every failure records target, case seed, campaign seed, error and stack in `fixtures/fuzz-regressions/*.json`; the test suite replays every persisted case forever. CI fails on any crash, invariant failure or allocation violation. Coverage is tracked per target by iteration counts in `fuzz.json`; a target that stops running shows zero iterations in evidence.

Limitations (debt D-003): no coverage guidance, no byte-level shrinking (the per-case seed is the reproducer), no sanitizer build - the native dependency is `cryptography`/OpenSSL, which is fuzzed upstream (OSS-Fuzz).
