# Changelog - INV-36

## 5.1.0 - 2026-09-22

Missing-component pass driven by `INV36_v5.0.0_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST.md` (752 items, 23 components). Minor version: `PK_CTRL_FRAME/2` and the `Session`/`Relay` API are unchanged; new layers are additive. Endpoints built with `ControlEndpoint` speak `PK_CTRL_STREAM/1` + `PK_CTRL_HS/1` and do **not** interoperate on the wire with bare 5.0.0 frame exchange.

### Added

- `vsock.py` AF_VSOCK adapter (bounded connect/listen/accept, backlog and connection limits, per-CID churn limiting, typed failures, capability probe) and `tools/vsock_smoke.py` real-kernel smoke test.
- `stream.py` PK_CTRL_STREAM/1: version preamble (rejects legacy peers), length-validated records, single reader / serialized writers, clean EOF vs truncation, deadlines; `FakeStream` with fragmentation, short writes, stalls, resets.
- `handshake.py` PK_CTRL_HS/1: SIGMA-style signed-ephemeral X25519 with Ed25519 credentials, transcript-bound signatures, MAC key confirmation, downgrade resistance, replay registry, revocation/attestation/clock dependency handling, typed failure codes.
- `keys.py` key custody abstraction (`secretref://` handles, metadata validation, bounded cache, bounded jittered retries), key-epoch rotation/grace/revocation/rollback control, key inventory.
- `messages.py` PK_CTRL_MSG/1 canonical envelope (type, tenant, op_id, traceparent) authenticated inside the AEAD; `schema/pk_ctrl.idl.json` IDL with generated `_wire.py`/`docs/WIRE.md` and drift check.
- `policy.py` single authorization decision point, default deny, tenant binding, explicit deny precedence, versioned/expiring policies with rollback protection, audited decisions, denial rate limiting, explicit break-glass.
- `config.py` validated, provenance-tracked, atomically activated configuration with overlays, secure defaults, rollback history, auto-rollback and crash recovery.
- `health.py` health states with hysteresis, stall detection, classified bounded retries with budgets, circuit breaker, admission control with priorities, residency-preserving fenced failover.
- `recovery.py` non-resumable session design, checksummed state store, persisted op_id dedup window, clean/unclean restart detection.
- `quarantine.py` signed, versioned, scoped, two-person directives; session termination on activation; persistence; kill switch.
- `observability.py` metrics catalog with bounded cardinality and Prometheus exposition, redacting rate-limited JSON logs, trace-context sanitisation, spans, bounded exporter; dashboards and alert rules.
- `audit_log.py` hash-chained, checkpoint-signed audit log with offline verifier.
- `endpoint.py` `ControlEndpoint`/`Channel` integrating all layers; explain view; drain; penalty box.
- `errors.py` stable error taxonomy (`inv36.error/1`).
- Certification: `gate.py`, `audit.py` (`python -m inv36_control_transport.audit`), `pkcore_adapter.py` (sole pk_core boundary), evidence schema and golden fixture.
- Tooling: fuzz/property campaign, benchmark + regression gate, soak/fleet simulator, release build/SBOM/provenance/sign/verify, traceability, checklist ledger, docs consistency, secret scan.
- Governance/docs: ADR-0001, protocol spec, 48 SHALL requirements + generated traceability matrix, runbooks, governance, release, compatibility matrix, performance report, CI workflow, CODEOWNERS.
- 170+ tests (normal and `-O`).

### Changed

- Transport exceptions now subclass `errors.Inv36Error` (still `ValueError`) and carry `.code`.
- `contract.py`/`component.py` obtain pk_core symbols through `pkcore_adapter.require()`; the contract now lists the stream, handshake and message interfaces.
- Package metadata: tools subpackage and schemas packaged; `[estate]` and `[dev]` extras; Python `<3.14`.
- Metric label normalisation memoised (profiling).

### Not done (needs owner or external systems)

License selection, named owners, the decision on the still-missing `MASTER.md`, real pk_core run, certified VM rows, production KMS/HSM adapter, managed signing identity, external crypto review of PK_CTRL_HS/1, long soak runner. See `docs/MC_CHECKLIST_STATUS.md`.

## 5.0.0 - 2026-09-22

Security and correctness hardening release. This is a major version because the frame/session wire contract is intentionally incompatible with 4.x.

### Fixed / hardened

- Replaced the custom SHA-256/XOR stream plus HMAC construction with standard AES-256-GCM-SIV authenticated encryption from `cryptography`.
- Added HKDF-SHA-256 directional key/nonce derivation bound to session ID and length-prefixed peer identities.
- Added `PK_CTRL_FRAME/2` fixed header with magic, frame version, algorithm ID and authenticated 64-bit sequence.
- Added mandatory fresh session IDs to prevent deterministic cross-session key/nonce reuse.
- Changed receive semantics from merely `seq > last` to exact-next sequencing, explicitly rejecting authenticated out-of-order delivery.
- Added sequence-exhaustion refusal before wrap/nonce reuse.
- Added thread locks around send/receive state so concurrent callers cannot allocate duplicate send sequence numbers.
- Added bounded relay diagnostic history and relay wire-size enforcement.
- Removed the establishment secret from dataclass representation and drop the stored reference immediately after derivation.
- Added explicit malformed-frame, out-of-order, closed-session and sequence-exhaustion error classes.
- Separated the cryptographic transport from `pk_core` so security tests no longer disappear when the estate framework is missing.
- Reworked tests: standalone crypto/protocol tests run under normal and optimized Python; only external estate integration is skipped when `pk_core` is absent.
- Added dependency/package metadata, security documentation, compatibility documentation and machine-readable checklist audit output.
- Removed the README claim that a `MASTER.md` file is present; the file was not contained in the supplied archive and is tracked as missing rather than reconstructed.
- Stopped treating a small protocol smoke test as sufficient evidence for unrelated checklist requirements; the post-update audit explicitly records partial and missing coverage.

### Validation in this audit environment

- Python compileall: PASS.
- Standalone/unit test discovery: PASS (18 tests total; 16 pass, 2 estate tests skipped because `pk_core` is absent).
- Optimized-mode transport suite (`python -O`): PASS.
- Wheel build with local build tooling and `--no-deps`: PASS.

## 4.1.0 - 2026-09-22

Previous audit/hardening pass. Retained here for history; its statement that all 100 requirements were satisfied cannot be independently reproduced from the supplied standalone archive because `pk_core` and the referenced evidence artifacts are absent.

### Historical changes

- Replaced side-effect-bearing `assert` checks in the component adapter with optimizer-safe verification.
- Added refusal checks for expected exception paths.
- Added the initial stdlib conformance test and version pins.
- Bound directions into the legacy keystream/MAC construction and rejected frames shorter than legacy sequence+tag overhead.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
