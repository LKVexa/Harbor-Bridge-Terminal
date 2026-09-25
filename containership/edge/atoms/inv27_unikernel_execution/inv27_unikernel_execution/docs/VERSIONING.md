# Versioning and compatibility (MC-017; C016, C027, C093)

- **SemVer on the package.** MAJOR changes a wire schema incompatibly or removes an error code.
  MINOR adds a format, toolchain profile, field or code. PATCH is fixes only.
- **Wire schemas carry their version in the name** (`PK_UNIKERNEL_SEAL_MANIFEST/1`, and so on).
  Parsers accept only listed versions (`manifest.SUPPORTED`). An unknown version gets
  `UK_UNSUPPORTED_VERSION`, never best-effort parsing.
- **Error codes are append-only.** `ops/ERROR_CODES.json` is the published list, and
  `test_platform.FailureModel` fails if a published code disappears.
- **Deprecation.** A field or code is marked deprecated for one MINOR release before a MAJOR
  release removes it.
- **Supported versions and security windows** are in `ops/EOL.json`. v4.2.0 is unsupported because
  it trusts caller metadata.
- **Adjacent layers.** The INV-28 image formats, INV-23 VMM versions and PLN-04 interface versions
  are declared in `ops/COMPATIBILITY_MATRIX.json`.
