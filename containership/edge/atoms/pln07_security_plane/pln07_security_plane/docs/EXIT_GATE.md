# Production exit gate (MC-72)

Run `python -m pln07_security_plane.ci.gate`. It writes `evidence/EVIDENCE.json` with artifact digests, SBOM digest, stage results and a verdict:

- **NO_GO** — any stage failed.
- **CONDITIONAL_GO** — all stages pass, but external blockers are open or the pk_core framework gate is blocked.
- **GO** — all stages pass, no open blockers, framework gate passed.

A verdict is a machine result, not an approval. Promotion needs the table below signed.

| Role | Name | Decision | Date | Evidence digest |
|---|---|---|---|---|
| Owner | | | | |
| Security lead | | | | |
| Release authority | | | | |

**4.3.0 result at build time:** see `evidence/EVIDENCE.json` (CONDITIONAL_GO expected: 14 external blockers open).
