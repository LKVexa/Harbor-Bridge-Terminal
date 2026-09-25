# INV-41 threat model (v1.0.0)

Machine-readable form: `docs/threats.json` (threat → requirements → tests → mutants). Architecture decision: ADR-0001. Re-review on any change to trust boundaries, authentication, isolation, configuration, serialization or revocation code (CODEOWNERS routes these to the security approver). `tools/mutation.py` proves each mapped control actually fails when disabled; `tests/test_governance.py::test_GV009` fails if a high/critical threat has no test or mutant.

## Assets

Authority seals · policy state · references · holders · membrane state · audit chain and sealing key · configuration and signing keys · release artifacts · integration identities · operator credentials.

## Actors

Trusted runtime · tenant workload (cooperating) · hostile workload · operator · peer node · identity/key provider · build system · control plane · external dependency (pk_core).

## Trust boundaries and data flow

```
 standalone library mode
 ┌──────────────────────────── one Python process ─────────────────────────────┐
 │  config (signed JSON) ──► ConfigStore.activate ──► Authority(seal, policy)   │
 │                                                     │ grant/bind            │
 │  cooperating component ◄── Holder ◄── Reference ◄───┘                        │
 │        │ use/attenuate/wrap                                                  │
 │        ▼                                                                     │
 │  Broker ── audit chain ──► collector (untrusted network, B-KEY-01)           │
 │         ── metrics/logs/traces ──► backends (B-DEPLOY-01)                    │
 └─────────────────────────────────────────────────────────────────────────────┘
 isolated mode
 ┌──────── trusted broker process ────────┐   JSON over pipe   ┌── child (-I -S -B, env={}, rlimits) ──┐
 │ Holder ─► CapabilityBridge (handles) ◄─┼────────────────────┼─ untrusted code sees opaque handles   │
 └────────────────────────────────────────┘                    └───────────────────────────────────────┘
```

Untrusted data first enters at: `Authority(policy)` / `ConfigStore.activate` (config), identifiers passed to every API, `HmacTokenAdapter.authenticate` (credentials), `CapabilityBridge.request` (child messages), `parse_traceparent` (headers). It becomes security-relevant at the seal check, the policy subset check and the principal binding.

## Threats and treatment

| ID | Threat | Sev | Controls / tests | Residual |
|---|---|---|---|---|
| T-FORGE | Forge a reference (construct, fabricate seal) | crit | guarded init + HMAC; PR001, CT011; M01, M02 | low |
| T-WIDEN | Widen via grant/attenuate | crit | subset checks; PR002; M03, M04 | low |
| T-XAUTH | Cross-authority substitution, same-id impostor | crit | id+seal check; PR003, CT006; M05 | low |
| T-DEPUTY | Confused deputy via name lookup | high | alias-only resolution | low |
| T-REVOKE | Revocation escape (nesting, attenuation, races) | crit | membrane chain registration; RC001–RC007, PR006; M06, M07 | low |
| T-SERIAL | Reference theft via pickle/copy | high | non-serializable; CT009; M09, M09b | low |
| T-LEAK | Leakage via repr/errors/logs/audit/metrics/traces | high | redaction everywhere; CT010, PR005, BT002, BT007; M08, M19 | medium (core dumps are a deployment control) |
| T-INPUT | Control chars, huge ids, hostile `__hash__` | med | type-before-hash, limits; CT002, PR004; M11 | low |
| T-DOS | Floods, deep nesting, big op sets, queue saturation | high | hard limits + admission; CT004, RS004, scale/burst; M10 | medium |
| T-AUDIT | Tamper with or suppress audit | high | chain+HMAC+seq; mandatory audit; AU002, AU006, BT009; M12, M13, M18 | medium until external anchor |
| T-CFG | Unauthorized / stale / rollback config | high | signature, key revocation, monotonic version; CF001, CF002; M14, M15 | medium until KMS signer |
| T-REPLAY | Credential replay | high | nonce window; ID002; M16 | low in-process; cross-process needs shared nonce store |
| T-AUTHN | Spoofed identity | high | iss/aud/exp/nbf/sig checks; ID001; M17 | medium until production adapters |
| T-RETRY | Retry storm / retrying denials | med | terminal classes never retried, budget; RS001; M20 | low |
| T-INTROSPECT | Reflection, gc, monkey patching, ctypes, debugger in-process | crit | **not mitigable in pure Python** → isolation tier | **HIGH** — WVR-001, B-ISO-01 |
| T-ESCAPE | Child reaching fs/net/processes | high | rlimits, empty env, `-I`; IS002–IS006 | **HIGH** — no namespaces/seccomp |
| T-SIDE | Timing/cache side channels | low | `hmac.compare_digest` | micro-arch channels need hardware isolation |
| T-SUPPLY | Compromised source/build/release/policy | high | stdlib-only, deterministic build, manifest; GV003 | medium until signed provenance |
| T-CLOCK | Clock manipulation | med | skew bound; audit uses monotonic ordering | medium |

Out-of-scope for this component, documented for completeness: memory residency of seals in swap/core dumps (disable core dumps, encrypted swap — DATA_PROTECTION.md), control-plane spoofing (no control plane exists yet; the `control-plane (future)` boundary is catalogued as BLOCKED).

## Coverage measurement

Threat coverage ≠ line coverage. Current evidence: `evidence/mutation.json` — every mapped control has a mutant and every mutant is killed; two threats (T-INTROSPECT, T-ESCAPE) are open release blockers carried as an approved-pending exception, not silently accepted.
