# Dependencies

## Runtime

- **Core** (`manifest.py`, `redaction.py`, `errors.py`, `service.py` and all 4.3.0 control modules): Python 3.10–3.13 standard library only.
- **Optional `crypto` extra**: `cryptography>=42` (tested 46.0.7) for EdDSA tokens, Ed25519 release signatures and AES-256-GCM sealed storage. Without it those features *refuse* (`crypto.unavailable` / signature failure); nothing falls back to plaintext or weaker checks.

## pk_core (integration framework) — BLOCKED_EXTERNAL

`component.py` and `contract.py` import `pk_core`, which is **not** in this
archive, and whose version, source and digest are unknown. Chosen distribution
model once supplied: a **pinned release artifact** (version + SHA-256 tree
digest recorded in `compatibility.json` `pk_core.pin_version` / `pin_sha256`),
mounted as a workspace sibling or via `PK_CORE_PATH`. Until then:

- `tools/preflight.py --certification` reports `pk_core.pin: BLOCKED` and fails;
- `tests/test_component.py` fails (dependency assertion) and skips conformance — the release gate treats both as failures;
- `python -m pk_core list|run|gate` cannot run; the gate requires its PASS output (`--pk-gate`).

Preflight verifies, when pk_core is present: import origin after `realpath`
(symlink/junction resolution), version attribute, tree digest against the pin
(tamper/drift ⇒ FAIL), and refuses group/world-writable dependency
directories and `PK_CORE_PATH` values that resolve outside their root.

### Upgrade / rollback procedure (when pk_core exists)

1. Obtain the new release artifact from the approved mirror; record version + digest in `compatibility.json` on a branch.
2. Run `tools/run_evidence.py` with `PK_CORE_PATH` pointing at it; the certification job must pass with zero skips.
3. Review `pk_core`'s capability/authority needs (SECURITY_ARCHITECTURE §3).
4. Merge; roll out with `rollout.py`. Rollback = restore the previous pin (git revert) and redeploy; state formats of INV-64 do not depend on pk_core.

## Build / certification tooling

setuptools ≥ 68 (PEP 517 backend), wheel; `build` for isolated builds in CI;
`pip-audit` for advisories (CI). Certification constraints:
`constraints-certification.txt` (library consumers are not constrained by it).
Offline path: `tools/bootstrap.sh --wheelhouse DIR` installs from a local
wheelhouse only.
