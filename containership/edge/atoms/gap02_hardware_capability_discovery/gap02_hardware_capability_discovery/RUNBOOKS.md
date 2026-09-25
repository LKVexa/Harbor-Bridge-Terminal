# GAP-02 Incident Runbooks (GAP02-MC-51)

Every stable error code links here (`errors.RUNBOOK`). First step for any incident:
`python -m gap02_hardware_capability_discovery.production.agent explain <capability>` or `GET /explain?capability=…` on the loopback health port.

Emergency disable (all capabilities → unprobed, readiness 503): `QuarantineRegistry.freeze(principal, reason)` via GAP-01 `SupervisorLink.disable`. Requires `control.freeze`.

## gap02-e001
**PROBE_UNAVAILABLE** — the probe's source (runtime, sysfs node, command) is missing. Expected on hosts without that hardware. If the hardware exists: install/enable the vendor runtime; confirm path in `COMPATIBILITY_MATRIX.json`.
## gap02-e002
**PRIVILEGE_DENIED** — agent lacks access (e.g. `/dev/tpmrm0`, KFD). Grant the narrow device ACL to the agent identity, or route the query through the broker (`production/broker.py`). Never run the whole agent as root.
## gap02-e003
**UNSUPPORTED_PLATFORM** — by design; capability stays unprobed. No action unless the platform should be supported (raise a matrix change).
## gap02-e004
**TIMEOUT** — a probe exceeded its deadline and was abandoned. Check for a wedged driver (`nvidia-smi` hang, D-state processes). Repeated timeouts open the circuit (E019). Consider quarantining the backend.
## gap02-e005
**DRIVER_ERROR** — runtime answered with an error (e.g. NVML cannot reach driver). Check kernel module load, driver/runtime version skew, dmesg Xid events.
## gap02-e006
**MALFORMED_RESPONSE** — unparseable vendor output. Capture raw output for a fixture; check for a vendor tool version change.
## gap02-e007
**STALE_DATA** — report/envelope older than its freshness bound. Check executor liveness (`/readyz`), sweep deadline, publisher backlog.
## gap02-e008
**SIGNATURE_FAILURE** — envelope did not verify (tamper, revoked or unknown key). Treat as security incident: quarantine node's reports, check GAP-07 key state, compare audit head.
## gap02-e009
**DEPENDENCY_FAILURE** — GAP-06/GAP-07 or transport unavailable. Retryable. Check sibling health.
## gap02-e010
**RUNTIME_INCOMPATIBLE** — runtime/driver mismatch. Upgrade driver to the vendor minimum listed in `accelerators.NVIDIA_MIN_DRIVER`.
## gap02-e011
**UNHEALTHY** — device reports faults (ECC/Xid). Drain workloads via GAP-11; RMA path per vendor.
## gap02-e012
**REPLAY_DETECTED** — duplicate nonce or non-increasing sequence. Security incident if not explained by a restart bug; compare boot_id and state file.
## gap02-e013
**CLOCK_UNTRUSTED** — no trusted sync, sync expired, or wall/monotonic divergence (rollback). Fix time sync (NTS/PTP); do not widen skew tolerance without review.
## gap02-e014
**CONFIG_INVALID** — config rejected. Fix the named key; unknown keys are errors by design.
## gap02-e015
**POLICY_DENIED** — authorization refused. Check principal→role bindings in the authz policy.
## gap02-e016
**PROVENANCE_FAILURE** — plugin digest/version/license/signature check failed. Do not bypass; rebuild from approved source.
## gap02-e017
**QUARANTINED** — backend or node deliberately disabled. Release only with a recorded reason.
## gap02-e018
**RESOURCE_EXHAUSTED** — ceilings hit (`limits.Ceilings`). Investigate leak before raising limits.
## gap02-e019
**CIRCUIT_OPEN** — backend failing repeatedly; it will half-open after cooldown. Resolve the underlying E004/E005.
## gap02-e020
**SCHEMA_INCOMPATIBLE** — peer speaks an unsupported schema major or sent an unknown critical field. See `COMPATIBILITY_MATRIX.json`.
## gap02-e021
**UNATTESTED** — identity or confidential-computing attestation missing. Check GAP-06; a node must not sign reports without an attested identity.
## gap02-e999
**INTERNAL** — unexpected exception, failed closed. File a defect with the explain output and logs.
## flapping
Capability changing state repeatedly — suspect a marginal device or hot-plug storm; check hot-plug debounce and hardware health.
