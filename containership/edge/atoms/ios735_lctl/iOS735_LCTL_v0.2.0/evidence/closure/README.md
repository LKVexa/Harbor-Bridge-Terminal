# Closure-pass run records (2026-09-23)

- `unittest-transcript.txt`: the full offline and closure suite (49 tests). JDK and OpenSSL were present, so no tests were skipped.
- `preflight.txt`: the release gate state after this pass (6 gates open, all owner-dependent).
- `schema-strict.txt`: validation with both the stdlib validator and the `jsonschema` 4.26 package.

The environment was Linux, Python 3.11.15 and OpenJDK 21.0.10. The genuine LCTL toolchains were not available, so the simulator-based tests are test-only and are not verification evidence.
