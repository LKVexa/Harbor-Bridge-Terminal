# Identities, capabilities and least privilege (C023, C024, C042, C043)

## Identities and authentication per boundary

| Identity | Kind | Authenticates with | Why sufficient |
|---|---|---|---|
| Workload submitter / CI | service | IdP identity token + Ed25519 artifact statement | token proves the caller; statement proves provenance of the exact bytes independently of the caller |
| Verifier / rewriter | in-process | — (same process as service) | no boundary crossed; its output is re-verified at load |
| Trusted loader | in-process | descriptor HMAC (sealing key by reference) | same trust domain as verifier; MAC binds every field |
| Runtime / orchestrator | service | IdP token | caller of load/execute; tenant-bound |
| Engine process | subprocess | none (launched by the service, stdin/stdout only) | not reachable by other callers; fresh per job |
| Operator | human | IdP token (`kind: human`) | global actions require two distinct humans |
| Policy controller | service or human | IdP token | `sfi.policy.write` only |
| CI signer | service | Ed25519 private key (outside this repo) | trust roots pinned by key id |
| Release approver | human | IdP token with `sfi.release.certify` | recorded in release evidence |
| Telemetry consumer | service | none for metrics/health (no secrets exposed); token for explain/audit | health/metrics carry no tenant data values |
| Emergency responder | human | IdP token with `sfi.quarantine` | dual authorization for global scope |

## Capability inventory

| Capability | Grants | Typical holder | Scope binding |
|---|---|---|---|
| `sfi.submit` | submit artifact | tenant CI | tenant |
| `sfi.verify` | run verifier / obtain proof (CLI) | tenant CI, operators | tenant |
| `sfi.load` | trusted load | orchestrator | tenant + optional artifact digest |
| `sfi.execute` | invoke exports | orchestrator | tenant + digest |
| `sfi.policy.write` | activate/rollback config | policy controller | global |
| `sfi.quarantine` | freeze/disable/release | operators | tenant / artifact / global (dual) |
| `sfi.audit.read` | read audit / explain | security, SRE | global |
| `sfi.keys.admin` | rotate/revoke keys and roots | security owner | global (dual — procedure in RUNBOOKS.md) |
| `sfi.release.certify` | sign release evidence | release approver | release |

Deny-by-default: `Authorizer.check` grants only when an explicit grant matches capability, tenant and
digest; a tenant-bound principal cannot act for another tenant regardless of grants. There are no role or
name checks anywhere in the code (`grep -n "subject ==" production/` only finds the dual-auth distinctness
check). Authorization is carried into the load/execute handoff through the sealed descriptor (TOCTOU).

## Least privilege per process (C042, C043)

| Process | Filesystem | Network | Devices | Env / secrets | Children |
|---|---|---|---|---|---|
| Service (verifier + loader) | read/write its `root` (config, state, audit); reads artifacts from the caller (bytes, not paths) | none required | none | two secret refs | spawns the engine only |
| Engine job (`node --permission`) | read: runner script only; **no writes** (denied by the permission model) | not needed; **not blocked** by the Node permission model — the runner exposes no network API to guest code (residual, waiver W-03) | none | **empty environment** | **denied** (permission model) |
| Guest Wasm | its partition of linear memory only | none (no imports except allowlisted host functions) | none | none | none |
| CLI | operator's local permissions | none | none | none | none |

Parsing never needs write access to the source artifact (bytes in memory); rewritten output is returned,
not written, except by the CLI to an explicit output path after verification.

Tests: `test_hostcall_not_allowlisted_is_absent`, engine preflight (`permission_model_denies_writes`),
`T04`, `T12`. Running the service itself under an OS sandbox (seccomp/AppArmor/container profile) is an
**open deployment item** (owner UNASSIGNED): profiles are not shipped because the target OS is not fixed.
