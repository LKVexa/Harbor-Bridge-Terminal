# Failure catalog (MC-041, C051)

| # | Domain | Failure | Detection | Behaviour | Test |
|---|---|---|---|---|---|
| F01 | process | crash mid-append | torn final WAL line | truncated on start; state = last complete record | `test_torn_final_append_is_truncated` |
| F02 | process | crash after grant | term persisted before grant | restart never reissues a term; leases not restored | `test_controller_crash_restart_and_stale_leader` |
| F03 | process | defect/exception in dispatch | catch-all | `TOPO.INTERNAL`, details withheld, logged | `test_errors_do_not_leak_internals` |
| F04 | node | device/gateway loss | feed removes node / probes fail | reroute to next capable node under policy | `test_node_loss_and_region_loss` |
| F05 | link | flapping uplink | ≥4 flips/60 s | held down (flapping) | `test_link_flap_is_suppressed` |
| F06 | link | silent link (no probes) | age > suspect/stale | suspect → stale → excluded | `test_missed_probes_suspect_then_stale` |
| F07 | site | uplink loss | designated cloud unreachable | partitioned_local; local lease | integration + faults |
| F08 | site | intra-site split | quorum check | minority cannot lead | `test_minority_side_cannot_acquire` |
| F09 | region | region loss | cloud unreachable from sites | sites partitioned; cloud answers fail | `test_node_loss_and_region_loss` |
| F10 | multi-site | several sites isolated | per-site state | independent handling | `test_multi_site_isolation` |
| F11 | storage | write error / full disk | OSError | `DEPENDENCY_UNAVAILABLE`; breaker opens → `OVERLOADED`; not ready | `test_state_store_fault_*` |
| F12 | storage | corruption / tampering | MAC/chain | refuse start (fail closed) | persistence tests |
| F13 | storage | total loss | missing files | restore from export/backup | `test_disaster_total_state_loss_restore_from_backup` |
| F14 | clock | time source unhealthy | `Clock.healthy` | fail closed | `test_time_outage` |
| F15 | clock | backward step | negative elapsed | buckets clamp; credentials bounded by skew | admission test |
| F16 | dependency | key/policy/secret outage | availability flags | fail closed | outage tests |
| F17 | control plane | controller (instance) loss | restart | recovery from WAL; stale tokens fenced | faults |
| F18 | config | invalid/partial config | validation | previous generation keeps serving | `test_failed_activation_is_atomic` |
| F19 | load | overload / flood | buckets, in-flight | shed with retry_after | security + bench overload |
| F20 | data | stale latency | measured_at age | excluded or degraded | `test_stale_links_excluded_or_degraded` |
| F21 | correlated | repeated partition/heal cycles | site machine | terms increase monotonically | `test_repeated_partition_reconnect_cycles` |
| F22 | provider | wasmCloud host/NATS failure | **not testable here** | instance restart per F17 | open (MC-021) |
