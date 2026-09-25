# Integration, disaster, soak and fleet-scale suites (MC-16)

## Adjacent layers

| Adjacent component | Direction | How it is exercised here | Real implementation needed for certification |
|---|---|---|---|
| GAP-06 identity/attestation | upstream | `testing.World` issuer + `AllowlistAttestation` + `StaticRevocations` (versioned test doubles) | GAP-06 service |
| KMS/HSM | upstream | `InMemoryKeyProvider` with failure injection | production KMS adapter |
| Policy service | upstream | `PolicyStore` with versioned documents | policy distribution |
| Config service | upstream | `ConfigStore` | config distribution |
| PLN-03 runtime plane | downstream (producer/consumer) | handlers in `tests/test_endpoint_integration.py` | PLN-03 agents |
| GAP-12 relays | downstream | `transport.Relay` opaque forwarding | GAP-12 relay |
| INV-37 bulk data | peer | referenced by message bodies only | - |
| Telemetry backend | downstream | `BoundedExporter` with failing sender | collector |
| Lifecycle controller | upstream | quarantine directives, config activation | controller |

The **full-stack path** uses real INV-36 implementations end-to-end (stream -> handshake -> frame -> envelope -> quarantine -> authorization -> admission -> handler) over in-memory streams on every PR, and over real AF_VSOCK via `tools/vsock_smoke.py` where a peer is reachable.

## Scenarios and pass criteria

| Scenario | Test | Pass criterion |
|---|---|---|
| peer crash while the other side believes the session is live | `test_peer_restart_asymmetric_failure_forces_fresh_session` | stale side closes on first I/O; new session ID; stale frames fail authentication |
| mid-frame reset, stalled peer | `test_mid_frame_reset_and_stalled_peer` | typed stream error within the read deadline; channel closed |
| identity/revocation outage | `test_identity_outage_blocks_new_sessions_keeps_existing` | new handshakes fail closed; existing session keeps working |
| prolonged partition + reconnect | `test_prolonged_partition_then_reconnect` | every reconnect gets a fresh session ID |
| key rotation + emergency revocation under traffic | `test_key_rotation_and_revocation_under_active_traffic` | live traffic unaffected by rotation; revocation blocks new sessions immediately |
| quarantine during traffic | `QuarantineIntegrationTest` | matching sessions terminated < 1 s; keys discarded; others unaffected |
| cross-tenant ciphertext | `test_historical_ciphertext_not_openable_by_other_sessions_or_tenants` | authentication failure |
| overload | `test_overload_does_not_bypass_authorization` | denial precedes admission; overload is typed |
| soak (short, per PR) | `SoakFleetShortTest.test_short_soak_no_leaks` | no FD/thread growth |
| fleet (24 guests, per PR) | `SoakFleetShortTest.test_small_fleet_fair_and_bounded` | per-tenant fairness, bounded metric cardinality, jittered reconnect spread |

`tools/soak.py` runs the long versions: nightly 10-minute soak with rotations/reloads and a 200-guest fleet; release certification requires a 6-hour soak (`--seconds 21600`) whose windows show no monotonic RSS/FD/thread growth and stable p99 (waiver W-002 is proposed until a dedicated runner exists). Results are archived as CI artifacts (`soak.json`, `fleet.json`).

Not covered here (need real infrastructure): VM/host reboot, live migration, snapshot restore on real hypervisors, heterogeneous-fleet staged rollout, global dependency load. They are listed as mandatory rows in `compat/matrix.json` and block certification until run.

Every production-like failure found gets a regression test in this directory (policy in `docs/GOVERNANCE.md`).
