# Compatibility policy (C016, C027, C084, C093)

## Versioned surfaces
| Surface | Identifier | Rule |
|---|---|---|
| Wire protocol | `inv53.wire/1` | Minor: add optional request fields, add outcome codes. Major: anything else. |
| Error taxonomy | `inv53.errors/1` | Codes are never renumbered or re-meant; new codes may be added. |
| Store format | `inv53.store/1` | A reader refuses unknown schemas (`_migrate`); every new schema ships a registered migration and a restore test. |
| Config | `inv53.config/1` | Unknown keys are refused; renamed keys keep the old name as an alias for one major. |
| Python API | package `__version__` (semver) | 5.x keeps `ReliableQueue`, `Delivery`, `DeadLetter`, `IdempotentConsumer` signatures. |

## Mixed-version behaviour
Clients send one version in `v` and may call `negotiate([...])` offline; servers reject unknown versions with
`E_PROTOCOL_VERSION` (never guess). During a rolling upgrade both versions of a server must accept every
version in the older server's `SUPPORTED` tuple. Store files are written by exactly one writer, so mixed
versions never co-write a store; a newer reader opening an older store is allowed, the reverse is refused.

## Supported-version matrix
| INV-53 | Python | wire | store | pk_core | Support |
|---|---|---|---|---|---|
| 5.1.x | 3.10 – 3.13 (all four CI-verified on Linux, `evidence/CI_MATRIX.json`; Windows declared, not run) | 1 | 1 | 4.0.0 (pinned digest) | current |
| 5.0.x | 3.10+ | — (in-process only) | — (memory only) | 4.0.0 | security fixes until 5.1 has an approved exit gate |
| ≤ 4.1 | — | — | — | — | end of life (stale-ack defect) |

CI proves only what it ran: Linux CPython 3.10, 3.11, 3.12 and 3.13 produced identical source digests and a byte-identical release tarball. Windows (the `msvcrt` lock path) has not been executed.
