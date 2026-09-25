# INV-36 operational runbooks

Status: **proposed** (5.1.0). Owners and paging targets come from `governance/owners.json`; every role is currently UNASSIGNED, so these runbooks are not yet operable in production.

Common first steps for any page:

1. `python -m inv36_control_transport.audit --only G11-real-vsock --out /tmp/ev` is *not* an incident tool; use the explain view instead: call `ControlEndpoint.explain()` (exposed by the host agent's admin socket) and capture its JSON.
2. Record the build digest, config version/digest (`ConfigStore.current.provenance()`), policy version and quarantine state from the explain output in the incident ticket.
3. Preserve forensic artifacts (see [Forensics](#forensics)) **before** restarting anything.

<a id="auth-failure-spike"></a>
## Authentication / integrity failure spike (attack class)

Signals: `INV36AuthFailureSpike`, `INV36ReplayOrReorder`; audit events `integrity.failure`, `replay.threshold`.

1. Identify sources: explain view `recent_decisions` (kind `integrity`) and audit log `actor` fields.
2. Peers exceeding `auth_failure_limit` are already isolated by `PenaltyBox` for its cooldown.
3. If one peer or endpoint: submit a `peer` or `endpoint` quarantine directive (`deny_new_sessions` or `terminate_sessions`) - see [Quarantine](#quarantine).
4. If widespread: suspect relay/path tampering or a key compromise - go to [Key compromise](#key-compromise).
5. Verify the audit chain: `python -c "from inv36_control_transport.audit_log import verify_log; print(verify_log('<path>', {...}).to_dict())"`.

<a id="identity-dependency-outage"></a>
## Identity / attestation / KMS / time dependency outage

Signals: `INV36HandshakeFailuresDependency` (`HS_DEPENDENCY`), `INV36BreakerOpen`, health reason `required_dependency_down:*`.

- Behaviour by design: existing sessions continue until `session_max_age_s`; **new handshakes fail closed**. Readiness drops to `not_ready`.
- Do not enable `allow_cached_revocation_s` without security-owner approval and an expiry.
- Restore the dependency; breakers half-open after `breaker_reset_ms`; clients reconnect with jittered backoff (no manual mass restart).

<a id="policy-misconfiguration"></a>
## Policy misconfiguration

Signals: `INV36PolicyDenialsHigh`; audit `authz.decision` with `explicit_deny`/`default_deny`.

1. Compare `policy_version` in explain output with the intended version.
2. Roll forward with a corrected, higher-version policy. Rolling back to an older version requires a recovery authorization (incident ID) and is audited (`policy.rollback_denied` otherwise).
3. Never add wildcard/break-glass rules without `approved_by` from the security owner (the loader refuses them).

<a id="overload"></a>
## Overload / shedding

Signals: `INV36Overload`, `INV36CriticalShed`, `INV36HighLoadInfo` (informational).

- OPTIONAL traffic (heartbeat/status) is shed first; CRITICAL (revoke/drain/placement) is admitted up to HWM+16.
- CRITICAL shedding is SEV2: raise `send_queue_high_water` (hot-reloadable) only within the capacity envelope in `docs/PERFORMANCE.md`, or reduce fan-in.

<a id="latency-degradation"></a>
## Latency degradation

Check `inv36_latency_seconds` by stage. `seal`/`open` regressions point at CPU contention or the crypto backend; `handshake` at dependencies; `dispatch` at handlers. Compare against `perf/baseline-reference.json` using `tools/bench.py --compare`.

<a id="reconnect-storm"></a>
## Reconnect storm

Signals: `INV36ReconnectStorm`. Clients use full-jitter backoff with a shared retry budget; confirm budget exhaustion in logs (`RETRY_EXHAUSTED`). If a host restart caused it, wait one backoff cap (`retry_cap_ms`) before intervening. Consider a temporary `site`/`node` `deny_new_sessions` quarantine to spread load (two approvers).

<a id="hypervisor-vsock-failure"></a>
## Hypervisor / vsock failure

Symptoms: `STREAM_UNAVAILABLE` / `STREAM_RESET` on connect, `/dev/vsock` missing, CID changes after migration.

1. `python -m inv36_control_transport.tools.vsock_smoke` on the affected guest/host.
2. Check `vhost_vsock` (host) / `vmw_vsock_virtio_transport` (guest) modules and VMM vsock device config (guest CID, port 5036).
3. After live migration or snapshot restore, sessions must re-handshake; this is expected, not an incident.

<a id="protocol-incompatibility"></a>
## Protocol incompatibility

Symptoms: `STREAM_LENGTH_INVALID` "peer preamble is not PK_CTRL_STREAM/1", `HS_NEGOTIATION`. A 4.x or foreign peer is connecting. Follow the rolling-upgrade order in `docs/RELEASE.md` (hosts first accept 5.1 only after all guests in the pool run >= 5.0).

<a id="key-compromise"></a>
## Identity / key compromise

1. Security owner revokes the credential serial (revocation service) and/or the key epoch: `EpochPolicy.revoke(epoch, reason=...)` - takes effect on the next handshake.
2. Terminate live sessions for the affected subject: `peer` quarantine with `terminate_sessions`.
3. Rotate: issue new credentials at `current+1`; grace window only if the old epoch is *not* compromised.
4. Audit trail: `key.revoke`, `quarantine.activate`. Verify the audit chain.

<a id="quarantine"></a>
## Quarantine and emergency disable

- Directives are signed by the quarantine authority key (HSM, break-glass). Broad scopes (`node`, `site`, `process`, `protocol`, `global`) need a second approver; `global` also needs `confirm_global=true`.
- Activation terminates matching sessions synchronously; latency is recorded (`last_activation_latency_s`) and audited.
- Lift with a signed `lift` directive; a quarantined subject can never lift its own quarantine.
- Extreme recovery: create the kill-switch file configured as `kill_switch_path` (root-owned directory, mode 0600). Remove it to restore. Engagement is audited (`killswitch.engaged`).
- Restoration checklist: root cause fixed, audit chain verified, policy/config versions confirmed, staged unquarantine (endpoint -> node -> site).

<a id="telemetry-outage"></a>
## Telemetry outage

Control traffic continues. The exporter buffer drops oldest events and counts drops. No action beyond restoring the backend; security audit events are in the separate tamper-evident log.

<a id="software-defect"></a>
## Suspected software defect (leaks, crashes)

Capture explain JSON, `inv36_process_*` metrics, and a core/stack dump (never include memory dumps in tickets: they may contain key material). Roll back per `docs/RELEASE.md`.

<a id="config-rollback"></a>
## Configuration rollback

Automatic rollback triggers when a post-activation health check fails. Operator rollback: `ConfigStore.rollback(version, actor=..., reason=...)`; revoked digests are refused. Fields marked non-hot-reloadable require restart (`restart_required` in the activation audit event).

<a id="corrupted-state"></a>
## Corrupted persisted state

Recovery reports `state_corrupt=true` and `operator_action`. Quarantine the node (`deny_new_sessions`), copy the state file for forensics, delete it and restart (dedup window starts empty; replays inside the lost window are still bounded by session re-establishment). Corrupt quarantine state makes the registry fail safe (deny all) until replaced.

<a id="forensics"></a>
## Forensic artifacts to retain

Audit log segments + last signed checkpoint, explain JSON, gate evidence of the running build, config provenance, policy document, quarantine state file, structured logs for the window, metrics snapshot. Never retain plaintext payloads or key material.
