# License: pending owner decision

No license has been selected for this repository. Choosing one is the owner's decision (MC-34) and cannot be made by the remediation pass. Until a `LICENSE` file is added:

- package metadata carries `LicenseRef-PLN05-Owner-Pending`;
- `tools/gate.py` reports `MC-34: no LICENSE` as a release blocker;
- redistribution outside the owner's organisation is not permitted.

When a license is chosen: add `LICENSE`, set `license` in `pyproject.toml` and `security/approved-versions.json`, update README, and re-run `tools/ci.py`.
