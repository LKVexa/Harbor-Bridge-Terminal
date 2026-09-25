# Support and end-of-life policy — INV-23

- **Python:** 3.9 – 3.13 (CI matrix). A Python version is dropped one minor release after
  its upstream EOL.
- **Operating systems / architectures:** exactly the rows of `COMPATIBILITY.md`.
  Only rows marked **verified** are supported for production; `implemented-unverified`
  and `experimental` rows are best-effort; `unsupported` rows fail explicitly with
  `indeterminate`.
- **Release support:** each minor release receives fixes for 6 months after the next
  minor release; security fixes per SECURITY.md.
- **Deprecation:** interface fields are deprecated for ≥ 1 minor release before removal
  in a new schema major (`schemas/CHANGELOG.md`). Deprecations are announced in
  CHANGELOG.md under a "Deprecated" heading.
- **EOL signalling:** EOL versions are listed in SECURITY.md's table; the release gate
  refuses to certify an EOL version.
