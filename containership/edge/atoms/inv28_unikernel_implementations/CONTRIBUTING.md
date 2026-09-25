# Contributing (MC-008, MC-086..MC-089)

1. Read `DEVELOPMENT.md` for setup, then `docs/ARCHITECTURE.md`.
2. Every behaviour change needs positive, boundary and negative tests. Assert the stable reason code (`errors.Reason`), not message text.
3. Run `python -B -m inv28_unikernel_implementations.tools.check_all` before pushing. It runs lint, types (when mypy is available), SAST, the secret scan, the dependency check, `MASTER.md` consistency, the MC-status traceability check and the full test profile under `python` and `python -O`.
4. Any change to production policy, schemas or reason codes is safety-relevant. It needs a `CHANGELOG.md` entry, an update to `docs/MIGRATION.md` or the compatibility matrix, and review by a code owner (`.github/CODEOWNERS`).
5. The runtime depends on the standard library only. A new third-party dependency needs an ADR and an SBOM update.
6. Security issues go through `SECURITY.md`, not pull requests.
