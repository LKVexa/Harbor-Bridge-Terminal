# Offline behaviour, precedence, failure modes, encryption, telemetry (MC-009/010/052/056/060/061/083/084)

## Offline / dependency unavailable (MC-009, MC-053, MC-061)
| Dependency | Unavailable → behaviour |
|---|---|
| Control plane / policy source (GAP-13) | `offline_mode=refuse` (default): no new launches; running sandboxes continue to their timeout. `cached-profiles-only`: launches allowed only with profiles already on disk and digest-pinned. |
| Identity / key service | token and evidence verification fail → E_UNAUTHENTICATED / E_ATTESTATION_FAILED; never allow-by-default |
| Trusted time | E_DEPENDENCY_UNAVAILABLE, refuse |
| Telemetry export (GAP-09) | **degraded, not blocking**: metrics/logs stay in bounded in-process buffers; status stays ready |
| Audit sink (local file) | append failure raises → launch refused (security evidence is mandatory) |

## Precedence when goals conflict (MC-010)
**security > data residency > SLO > cost.** Concretely: an overlay may never loosen a security key (tighten-only rules), admission sheds load rather than relaxing controls, and a timeout never skips verification.

## Failure-mode matrix (MC-056, MC-062, MC-060)
| Failure | Detection | Result | Test |
|---|---|---|---|
| control fails to apply | child reports F / read-back mismatch | tree killed before exec, E_APPLY_FAILED / E_NOT_APPLIED | test_resilience, test_pre_exec_refusal |
| supervisor dies mid-launch | PDEATHSIG | workload dies; host raises | test_supervisor_killed_during_verification |
| host process dies | PDEATHSIG chain | whole tree dies | test_host_crash_kills_sandbox |
| workload hangs | timeout | pid namespace killed | test_timeout_kills_whole_tree |
| node reboot | — | sandboxes are not resumed (by design); callers re-launch through PLN-04; evidence is node-bound and not transferable | — |
| corrupt active config | JSON load | history file used | test_restart_with_corrupt_active_config_uses_history |
| tampered audit chain | verify on open | service refuses to start | test_tampered_audit_blocks_service_start |
| backend errors repeated | breaker | E_CIRCUIT_OPEN, half-open probe | test_breaker_opens… |
| site/region failover | — | **no cross-node failover**: isolation evidence and residency are node-local; failover = re-admission elsewhere by PLN-04 under the same profile digest | design only |

## Encryption and secrets (MC-028, MC-052)
* No remote transport exists in this repository; any future transport of profiles/evidence MUST use mutually-authenticated TLS 1.3 and carry the signed records unchanged.
* At rest: audit chain and config history are integrity-protected (hash chain, digests) but **not encrypted** — they contain no workload data or secrets by construction (redaction on every log/diagnostic path). Encryption at rest is delegated to the node's disk encryption. Status: PARTIAL (design only).
* Secrets never appear in configuration: `node_key_ref` must be `env:`, `file:` or `vault:`; `redact()` masks secret-named keys, HMAC signatures and PEM private keys in logs/diagnostics.

## Telemetry retention, sampling, export (MC-083) and alerts (MC-084)
Retention default 30 days (config `telemetry.retention_days`, enforced by the export target), diagnostic sampling `telemetry.sample_rate`, export `none` until GAP-09 is wired. Alert rules that keep load, degradation, policy rejection, dependency failure, attack and software defect distinct: `observability.ALERT_RULES`. Dashboards: not deployed (PARTIAL).
