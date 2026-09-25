# Licence status — OWNER ACTION REQUIRED (MC71)

No licence file shipped with v4.2.0 and none has been invented in v5.0.0: choosing a
licence is the copyright holder's decision, not an engineering one.

Until a `LICENSE` file is added, the package is **all rights reserved** by default and
must not be redistributed outside the owner's organisation.

To close MC71:

1. Choose a licence (e.g. Apache-2.0 for its explicit patent grant, or MIT).
2. Add `LICENSE` with the full text and set `license = "<SPDX id>"` in `pyproject.toml`.
3. Add `LICENSE` to `REQUIRED_GOVERNANCE` in `tools/release_evidence.py` and delete this file.

Third-party content: none. Every module is original stdlib-only Python; see `NOTICE`.
