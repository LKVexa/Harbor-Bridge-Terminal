# Contributing to INV-36

- Contributions are accepted only from the repository owner's organization under its internal IP policy until a license is selected (see `docs/LICENSE_STATUS.md`).
- Every change runs `python -m inv36_control_transport.audit` locally (or CI) - SKIP is never PASS.
- Protocol changes start in `schema/pk_ctrl.idl.json`; regenerate with `python -m inv36_control_transport.tools.gen_wire` and update golden fixtures deliberately.
- Requirement changes update `requirements/requirements.json`, test REQ tags and `python -m inv36_control_transport.tools.traceability --write` in the same change (impact analysis in the PR description).
- New tests must carry a `REQ: ... | KIND: ...` class docstring; orphan tests fail CI.
- Security-sensitive changes (handshake, transport, keys, policy, quarantine, audit log) need security-owner review.
- Never commit keys, tokens or real credentials; `tools/secret_scan.py` runs in CI.
