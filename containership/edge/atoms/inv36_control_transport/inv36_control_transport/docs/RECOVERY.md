# Restart, crash consistency and recovery (MC-10)

Implementation: `recovery.py`, `config.ConfigStore.recover`, `quarantine.QuarantineRegistry.load`, `audit_log.AuditLog.open`.

**Decision:** cryptographic session state is never persisted or resumed. There is no resume protocol; every restart, reconnect, guest/host reboot, live migration or VM snapshot restore performs a fresh PK_CTRL_HS/1 handshake with new CSPRNG ephemerals, so a nonce/sequence can never be reused under the same key, and two clones restored from one snapshot derive different keys (ephemerals are generated after restore; `StateStore.write` refuses key/sequence/session fields).

| State | Class | On restart |
|---|---|---|
| session ID, traffic keys, sequence counters | ephemeral | discarded; re-handshake |
| peer identity | reconstructable | re-proven by the handshake |
| partial inbound bytes, unauthenticated buffers | ephemeral | discarded (`Connection.close` clears) |
| pending outbound work | ephemeral | discarded; callers re-submit with the same op_id |
| op_id dedup window | persisted (`inv36.state/1`) | reloaded; replays across restart refused |
| configuration | persisted | `ConfigStore.recover()` (digest-checked, re-validated) |
| quarantine directives | persisted | re-verified signatures; unverifiable state => deny all |
| audit cursor/head | persisted (the log) | torn tail truncated; chain continues |
| shutdown marker | persisted | clean/unclean detection |

Replay eligibility: only operations classed `retry_with_dedup_token` (LEASE_*, PLACEMENT, DRAIN) may be re-submitted after restart, and only with their original op_id.

Persistence format: JSON document `{"schema":"inv36.state/1","body":{...},"sha256":...}` written `tmp -> fsync -> rename -> fsync(dir)`; wrong schema or checksum => `StateCorrupt`, recovery reports `state_corrupt` with an operator action (see RUNBOOKS "corrupted-state").

RTO: ready within 5 s after process restart with healthy dependencies (recovery itself measured in milliseconds; readiness additionally waits for required dependencies). Readiness after restart means: config snapshot valid, policy loaded and unexpired, identity key usable, quarantine state verified. Recovery never restores stale authorization decisions - policy/config/quarantine are re-evaluated.

Semantics per event: process restart, guest reboot, host reboot, live migration and snapshot restore are listed in `recovery.RESTART_SEMANTICS`.

Tests: `tests/test_resilience_recovery.py::RecoveryTest`, `tests/test_endpoint_integration.py::DisasterPartitionTest`. Real VM reboot/snapshot tests need a certified VM row (waiver W-001, proposed).
