# Release procedure (M30, M31, M32)

1. `python -B -m unittest discover -s tests` green locally; CI matrix green (`.github/workflows/inv61-ci.yml`).
2. `python -B tools/run_gate_tests.py` with `INV61_REQUIRE_PK_CORE=1` — zero skips (blocked on M01 today).
3. Regenerate the lock with hashes from the approved index:
   `pip-compile --generate-hashes` (or `pip download` + `pip hash`) → `requirements.lock`; install with `--require-hashes`.
4. `python -B tools/bench.py --baseline <previous>/bench.json --max-regress 0.25` — non-zero exit blocks.
5. `python -B tools/soak.py --seconds 300 --clients 16` — non-zero exit blocks.
6. `python -B tools/sbom.py --out evidence/sbom.cdx.json --sums SHA256SUMS`; commit both.
7. `python -B tools/checklist_status.py --check` — every requirement's cited test id still exists.
8. Sign `SHA256SUMS` (signing key: **not provisioned** — BLOCKED) and record the release in CHANGELOG.md.
9. Owner approval of the production exit gate (OPERATIONS.md §8) — owner **UNASSIGNED**.
