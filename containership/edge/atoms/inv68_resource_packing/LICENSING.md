# Licensing — INV-68 4.3.0

**Distribution license: UNDECIDED.** The supplied 4.2.0 archive carried no LICENSE
file and no license field. Only the owner (David Paul Russell / LinearFinance.org
Research Division) can choose one; this pass does not invent one.

Until a license is chosen:

- `pyproject.toml` declares `LicenseRef-Proprietary-Pending` and the
  `Private :: Do Not Upload` classifier, so the wheel cannot be published to PyPI by mistake;
- the release gate treats the missing license as a governance blocker (MC-42);
- `THIRD-PARTY-NOTICES.md` lists every donor and dependency; nothing copyleft is included.

To close: add `LICENSE` with the chosen text, set `license` in `pyproject.toml`,
replace this file's status line, and re-run `tools/run_evidence.py`.
