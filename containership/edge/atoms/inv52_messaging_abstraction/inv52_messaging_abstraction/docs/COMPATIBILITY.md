# Compatibility matrix and version policy — `DOC-INV52-COMPAT` v4.3.0 (C027, C031, C084, C093)

## Interface versions

| Contract | Supported majors | Negotiation |
|---|---|---|
| PK_MSG_ENVELOPE | 1 | `schemas.negotiate` picks the highest common major; no overlap → `PK_MSG_VERSION_UNSUPPORTED` (terminal) |
| PK_MSG_PUBLISH / SUBSCRIBE / CONFIG / DECISION / HEALTH | 1 | same |

Within a major, peers MUST ignore unknown optional fields (tested: `test_integration.py::VersionTest`). Mixed-version peers on the same major interoperate; a peer on a different major is refused, never guessed.

## Runtime / platform matrix

| Dependency | Pinned / supported | Evidence here | Status |
|---|---|---|---|
| CPython | 3.10, 3.11, 3.12, 3.13 (CI matrix on Linux, macOS, Windows) | 3.11.15 Linux x86_64 in this build; matrix defined in `.github/workflows/ci.yml`, not yet executed | PARTIAL |
| CPU architectures | any (pure Python); x86_64 and arm64 targeted | x86_64 only | PARTIAL |
| Dapr runtime (`daprd`) | **1.17.x candidate** (Dapr supports the current and previous two minors; 1.17 released 2026-02-27). Exact patch to be fixed at approval. | wire mapping tested against an HTTP emulator of the v1.0 publish API, **not** against `daprd` | BLOCKED (approval + live run) |
| Dapr HTTP API | v1.0 publish + subscription delivery contract | emulator tests | PARTIAL |
| CloudEvents | 1.0 structured mode | round-trip tests | EVIDENCED_LOCAL |
| Brokers (via Dapr components) | redis, kafka, Azure Service Bus, NATS JetStream — candidates, none certified | none | BLOCKED |
| Hypervisors / providers | not relevant to pure-Python library; inherited from the host platform | — | N/A (declared) |

**Cross-car finding:** sibling INV-46 v4.3.0 pins `daprd 1.14.4` (its SBOM and deploy manifests). 1.14 is outside Dapr's N-2 support window as of 2026. INV-46 and INV-52 must converge on one supported minor before either is approved.

## Upgrade / downgrade

* Package: semantic versioning; 4.3.0 is API-compatible with 4.2.0 (additive: new errors carry the same base class, `subscribe` now returns an id, `metrics()` adds structured keys). One behavioural change: `envelope`/`validate_envelope` now reject a malformed `traceparent` field that 4.2.0 ignored.
* Config: `PK_MSG_CONFIG/1` generations are kept; downgrade = `ConfigManager.rollback`.
* Dapr: upgrade one minor at a time, canary per OPERATIONS.md.
