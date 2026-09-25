# Compatibility and versioning policy (M11/M21/M79)

Semantic versioning applies separately to: the Python package (`VERSION`), wire protocol (`meta.protocol`, currently 1.0–1.1), WIT package (`inv60:lattice@1.0.0`), config schema (`inv60.config/1.0.0`), error registry (`1.0.0`), evidence schema (`inv60.acceptance/1`).

| Change | Class | Rule |
|---|---|---|
| New optional field, new error code, new enum value clients may ignore | additive | minor bump |
| Tightened validation of previously accepted input | conditionally compatible | minor bump + release note + waiver if a supported client breaks |
| Removed/renamed field, retyped field, changed code meaning, reused code number | breaking | major bump; new WIT package version; migration guide |

- **Unknown fields:** wire requests reject unknown fields (tag-substitution defence); responses may add fields and clients MUST ignore unknown ones. **Unknown codes** decode to `UNKNOWN` (999).
- **Mixed versions:** control plane N supports clients/hosts N and N-1 (protocol 1.0 and 1.1 today). Negotiation (`fabric/negotiation.py`) picks the highest common version ≥ configured minimum and never silently downgrades; offers are signed.
- **Deprecation:** minimum one minor release and 90 days notice; removal only in a major.
- **Downgrade:** state store schema `inv60.state/1` is forward-only; rollback across a state-schema change requires restore from the pre-upgrade snapshot (`docs/runbooks/BACKUP_RESTORE.md`).
- **Release gate:** compatibility review is a named sign-off in `release/ACCEPTANCE.json` (currently unsigned).
