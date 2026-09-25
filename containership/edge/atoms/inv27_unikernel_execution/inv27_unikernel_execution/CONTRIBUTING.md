# Contributing to INV-27

**Environment:** CPython ≥ 3.10. The runtime has no third-party dependencies; `cryptography` is an
optional extra. Fixtures need gcc and binutils for x86_64 (`tests/fixtures/build_fixtures.sh`).

**Before every push**, run `python -B inv27_unikernel_execution/tools/ci.py`. It runs the tests
under `python` and `python -O`, the lint, coverage, dependency check, RTM, MC status, the pk_core
gate and the manifest. Mandatory tests must not skip; the only declared skip lanes are the optional
`cryptography` ones.

**Changes needing review by specific owners** (see `.github/CODEOWNERS`):

| Area | Paths | Reviewer |
|---|---|---|
| Parser, facts, admission | `image/`, `admission.py` | security owner |
| Trust | `trust/` | security owner |
| VMM and isolation | `vmm.py`, `isolation.py` | security owner + architecture reviewer |
| Schemas and error codes | `schemas/`, `errors.py` | architecture reviewer (append-only codes) |
| Release gate and waivers | `tools/release_gate.py`, `ops/WAIVERS.json` | release approver |

**Schemas and evidence:** change the schema file and the parser together; `test_seal` checks them
against each other. Regenerate evidence with `tools/ci.py --write`.

**Fixtures:** any new sample binary must be built from source in this repository. Record its sha256
in `FIXTURES.json`. Third-party binaries need their licence recorded in `THIRD-PARTY-NOTICES.md`.

Never bypass `tools/release_gate.py`. A PROPOSED waiver does not unblock anything.
