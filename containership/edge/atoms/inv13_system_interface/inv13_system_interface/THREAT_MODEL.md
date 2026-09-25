# INV-13 Threat Model (v4.3.0)

Scope: guest component ↔ INV-13 host boundary, control plane ↔ host, host ↔ OS. Method: STRIDE per boundary; every threat is tied to at least one automated test. Review cadence: every world/WIT change and every release (owner: see OWNERSHIP.md).

| ID | Threat | Boundary | Mitigation (code) | Test(s) | Residual |
|---|---|---|---|---|---|
| T-01 | Path traversal (`..`, absolute, NUL) escapes preopen | guest→fs | `fs.split_guest_path`, `runtime.Instance.resolve` | `test_fs_descriptor::*test_lexical_escapes`, `Fuzz.test_path_resolvers_never_escape` | none known |
| T-02 | Symlink planted/swapped mid-walk (TOCTOU) | guest/host→fs | openat2 `RESOLVE_BENEATH|NO_SYMLINKS`; O_NOFOLLOW walk | `test_symlink_swap_race`, `test_symlink_intermediate_dir_refused` | walk mode relies on per-component O_NOFOLLOW |
| T-03 | Host root renamed/replaced after grant retargets authority | host→fs | preopen is an fd, never re-resolved | `test_host_root_rename_does_not_retarget` | — |
| T-04 | Bind-mount / mount crossing inside preopen | host→fs | `RESOLVE_NO_XDEV`, per-step `st_dev` | `test_mount_crossing_refused` | — |
| T-05 | Guest imports an ungranted host function | guest→runtime | `wasm_loader.admit` + adapter re-check of engine import list | `WasmLoader.test_undeclared_import_rejected_before_engine`, `V8Adapter.test_ungranted_capability_never_reaches_engine` | component binaries unsupported |
| T-06 | Malformed module crashes parser / host | guest→loader | bounded LEB128, section overrun checks, size ceilings | `Fuzz.test_wasm_parser_total_on_garbage` | engine-side parsing is V8's |
| T-07 | Clock used as a timing side channel | guest→clocks | quantisation ≥ 1 µs (default 1 ms), capability gating | `Clocks.test_side_channel_resolution_floor` | coarse channels remain by design |
| T-08 | Weak/replayable randomness in production | host | CSPRNG only; deterministic provider requires non-prod profile + ack | `Randomness.*` | — |
| T-09 | Secret leaks via env/argv/stdout/audit | guest↔host | `SecretRef`, non-inheritance, sink redaction, privacy filter | `EnvStdio.*`, `Audit.test_privacy_filter_applied_before_write` | secrets in guest memory after reveal |
| T-10 | Stale/forged handle aliases another resource | guest→resources | generation-tagged handles, typed lookup | `ResourceTableTest.*`, `Races.test_resource_table_concurrent_push_drop` | 12-bit generation wrap after 4095 reuses of one slot |
| T-11 | Cross-tenant authority (overlapping roots, wrong tenant) | control plane | policy validation rejects overlap; descriptor tenant check | `Policy.test_invalid_documents_rejected`, `Descriptors.test_cascading_revocation_and_tenant_scope` | — |
| T-12 | Rights amplification via derived descriptors | control plane | attenuation-only `derive` | `Descriptors.test_attenuation_only` | — |
| T-13 | Forged / replayed / malleable actor token | control plane→host | HMAC, canonical base64, nonce cache, expiry ceiling, audience/role/workload binding | `Identity.*`, `Fuzz.test_identity_tokens_mutation` | shared-key HMAC is reference only |
| T-14 | Attestation unavailable → silently accepted | node | fail-closed gate | `Identity.test_attestation_fails_closed` | real TEE verifier absent |
| T-15 | SSRF (private IPs, metadata, DNS rebinding, redirects, v4-mapped v6) | guest→http | resolved-IP vetting of every hop, IP pinning, scheme/port/host allowlists | `Http.test_ssrf_defences` | — |
| T-16 | TLS downgrade / unverified certs | guest→http | CERT_REQUIRED + hostname check enforced at construction; https→http refused | `Http.test_tls_verification_cannot_be_disabled`, `test_untrusted_certificate_refused` | — |
| T-17 | Ambient network | guest→net | empty policy denies connect/listen/DNS | `Sockets.test_no_ambient_network` | — |
| T-18 | Resource exhaustion (fds, sockets, streams, entropy) | guest→host | quotas, admission, bounded streams, token bucket | `Quotas.*`, `Async.test_backpressure_bounded`, `Randomness.test_rate_limit_backpressure` | memory limits inside the engine not enforced |
| T-19 | Audit tampering / truncation | host storage | chain + HMAC checkpoints + verify-on-open | `Audit.test_tamper_detection` | attacker with checkpoint key |
| T-20 | Partial config activation / concurrent writers | control plane | stage-by-digest, CAS, atomic replace, recovery | `Config.*`, `Races.test_concurrent_config_writers_single_winner` | in-process lock + file CAS, not a distributed lock |
| T-21 | Operator abuse of emergency controls | operator | operator-role token + mandatory reason + audit | `Controls.*` | no two-person rule yet |
| T-22 | Telemetry cardinality explosion / PII in metrics | host→observability | label enumerations collapse to `other`; allowlist privacy filter | `Telemetry.*` | — |
| T-23 | Failure paths create ambient authority | all | fail-closed on provider/identity/config/entropy loss | `Faults.*` | — |
