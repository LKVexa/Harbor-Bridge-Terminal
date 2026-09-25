# Compatibility and versioning policy  (C016, C027 · components 07, 23, 93)

- Package: SemVer. `VERSION` is the single source; tests assert `__init__`, `pyproject.toml` and `CHANGELOG.md` agree.
- Interfaces: `PK_BROKER_<NAME>/<major>.<minor>`; negotiation in `negotiation.py` picks the highest common version, lower minor governs; different majors are incompatible (`INV54-E0801`).
- Error codes, config schema (`inv54.config/1`) and on-disk format (`storage.FORMAT_VERSION=1`) are versioned separately; a bump requires a migration note in CHANGELOG.
- **Deprecation window:** a major is supported ≥ 2 minor releases or 180 days after its successor, whichever is longer. Deprecated majors are listed in `negotiation.DEPRECATED`.
- **Mixed-version operation:** during rolling upgrade, nodes negotiate down; storage format changes ship read-old/write-old first, write-new in the following release.

## Supported-version matrix (component 93)
| INV-54 | Python | PK_BROKER_LOG | PK_BROKER_FANOUT | storage format | Kafka client | pika | boto3 |
|---|---|---|---|---|---|---|---|
| 4.3.x | 3.10–3.12 (tested: 3.11.15) | 1.0–1.1 | 1.0–1.1 | 1 | 2.6.1 (UNVERIFIED) | 1.3.2 (UNVERIFIED) | 1.35.99 (UNVERIFIED) |
| 4.2.x | 3.10+ | 1 | 1 | none (memory) | — | — | — |
