# Contributing (INV-32)

1. `python -m unittest discover -s inv32_elastic_virtualization/tests -t inv32_elastic_virtualization/tests`
   (stdlib only; no network).  Integration tiers need infrastructure (docs/TESTING.md).
2. `ruff check inv32_elastic_virtualization` and `mypy inv32_elastic_virtualization --exclude tests` must be clean.
3. `python -m inv32_elastic_virtualization.release sast` and `... release rtm-check` must pass.
4. Every behaviour change updates `RTM.json` (via `tools/build_rtm.py`), `CHANGELOG.md`, and — for external
   contracts — `schemas/` + `conformance/` fixtures (additive only within a major).
5. **Security review is mandatory** for any new `authz.ACTIONS` entry, provider primitive, or config key marked
   security-critical: add/extend a row in `docs/THREAT_MODEL.md` and name the reviewer in the PR.
6. Never add a runtime dependency without an ADR and a lock/hash entry.
