# GAP-14 v4.3.0 — Normative Design Note

Status: **normative** for v4.3.0. Covers checklist items `A02`, `A03`, `A04`, `C01`–`C05` for every component G14-P0-01 … G14-P2-40 unless a component section below overrides them. "MUST" and "MUST NOT" are binding.

## 1. Scope and non-goals

GAP-14 decides whether compute moves to data or data moves to compute (plus partial movement and replication) for **one tenant's workload–dataset pair** or an advisory DAG. It produces a signed, audited **decision envelope**.

Non-goals, unchanged from the contract: executing moves (PLN-06), authoring residency policy (GAP-13), placing compute (SCH-01), transport, storage engines, overriding a legal pin.

## 2. Decision lifecycle and invariants

```
request ─► readiness ─► admission ─► authN/authZ ─► strict parse ─► tenant binding ─► anti-replay
        ─► deadline ─► GAP-03 topology ─► SCH-01 placement ─► GAP-05 convergence ─► GAP-13 verdicts
        ─► hard constraints ─► objective ─► shadow/canary ─► provenance ─► sign ─► AUDIT ─► return
```

Invariants (each has at least one negative test):

| # | Invariant | Enforced in | Negative test |
|---|---|---|---|
| I1 | No option survives unless a **fresh, signed, request-bound GAP-13 verdict** allows the holding site | `service._gather`, `adapters.PolicyAdapter` | `test_p0_security_adapters.PolicyAdapterTest` |
| I2 | Legality is evaluated **before** cost; no objective weight can resurrect an eliminated option | `planner.plan` | `test_candidate_model_cannot_bypass_residency`, property test |
| I3 | Data never moves without a valid convergence proof for **that tenant's dataset** | `ReplicationAdapter.proof`, `planner` | `test_unconverged_blocks_move_data`, `test_proof_for_other_dataset_rejected` |
| I4 | No cross-tenant decision: dataset tenant = workload tenant = token-authorized tenant | `service.decide` | `TenantIdentityTest` |
| I5 | **No audit, no decision**: a decision leaves the service only after its audit record is durably appended | `service._decide` | `test_audit_failure_withholds_decision` |
| I6 | Missing cost data for a legal option is an error, never a default | `planner.route` | `test_missing_route_fails_closed` |
| I7 | Only `production`-mode, GAP-14-signed, unexpired, data-movement envelopes can be handed to PLN-06; exactly once per decision | `DataPlaneHandoff.submit` | `test_modified_envelope_cannot_be_executed`, `test_forged_executable_flag_rejected`, duplicate test |
| I8 | Simulations and shadow results are never executable | `simulate`, `submit` | `SimulationTest` |
| I9 | A missing/incompatible/partial `pk_core` gate can never report PASS | `compat.evaluate_gate` | `GateIntegrityTest` |
| I10 | Versions of policy/topology/placement/convergence/config never go backwards | `VersionWatermark`, `ConfigManager` | rollback tests |

## 3. Modes

| Mode | Purpose | Executable | Stale topology/price grace | Dev flags |
|---|---|---|---|---|
| `production` | live decisions | yes | none (TTL is hard) | refused (`G14_CONFIG_FORBIDDEN_IN_PRODUCTION`) |
| `staging` | pre-prod | no | 2× TTL, marked by `age_s` | allowed |
| `development`, `test` | local | no | 2× TTL | allowed |
| *simulation* (API, any mode) | what-if | never | n/a (caller inputs) | n/a |
| *shadow* (config) | candidate model evaluation | never (recorded only) | same as primary | n/a |

Residency verdicts, convergence proofs and placement snapshots have **no** stale grace in any mode.

## 4. Trust model

* **Producers**: GAP-13 (`gap13-policy`), GAP-03 (`gap03-topology`), GAP-05 (`gap05-replication`), SCH-01 (`sch01-placement`), PLN-06 (`pln06-dataplane`), identity service (`estate-identity`), config authority (`gap14-config-authority`). GAP-14 signs as `gap14-data-gravity`; audit MACs use a separate audit key.
* Every artifact is `{"body": …, "sig": {"alg","kid","iss","mac"}}` over canonical JSON (sorted keys, no whitespace, finite numbers only). Keys are 256-bit minimum, scoped to one issuer, with validity window and revocation.
* **HMAC limitation (accepted, documented risk R-1):** HMAC proves possession of an estate-distributed key, not non-repudiation, and anyone holding a verification key could forge. Production MUST distribute per-producer keys through the estate KMS and SHOULD replace `KeyRing` with an asymmetric `Verifier` (Ed25519) — the `Verifier` protocol exists so this is a drop-in change. This is why the certification manifest marks cryptographic items `implemented-fixture`, not `certified`.
* Request binding: GAP-13 verdicts carry `request_hash = sha256(canonical(request))`; convergence proofs carry tenant+dataset; placement snapshots carry tenant; PLN-06 acks carry `handoff_id`.

## 5. Threat model (STRIDE per trust boundary) — `C01`

| Threat | Boundary | Mitigation | Test |
|---|---|---|---|
| Spoofed verdict/snapshot | dependency → GAP-14 | issuer-scoped keys, `expected_issuer` | `test_unknown_issuer_key_rejected` |
| Tampered payload | all | MAC over canonical body | tamper fault matrix |
| Replay of old allow verdict | GAP-13 → GAP-14 | TTL + request hash (contains `evaluated_at`) + version watermark | stale/rollback tests |
| Replay of a caller request | caller → GAP-14 | `ReplayGuard` per tenant/request_id, 15-min window | `test_replayed_request_id_refused` |
| Privilege escalation via token edit | caller | signed claims; scope + tenant checks; max 1 h lifetime | `AuthTest` |
| Cross-tenant access | caller, explain | tenant equality + tenant-scoped explain | `TenantIdentityTest`, `test_explain_is_tenant_scoped` |
| Cost manipulation to pull data to attacker site | config, request | economics only from **signed config**; request cannot set prices; residency first | I2 property test |
| Classification downgrade | caller | classification is echoed into the verdict request and bound by hash; GAP-13 is source of truth | binding test |
| Info disclosure in logs/metrics | observability | redaction (keyed hash), secret-field drop, bounded labels | `MetricsLoggingTest` |
| DoS (payload, concurrency, fan-out) | caller | admission bounds, deadlines, bounded retries, breakers | `AdmissionTest`, fault matrix |
| Unsafe fallback on outage | dependency | fail-closed; no cached "allow" | `test_outage_is_fail_closed_no_decision_emitted` |
| Execution of a simulation | GAP-14 → PLN-06 | `executable` + mode + signature checks | `SimulationTest` |

## 6. Data classification — `C05`

| Field | Class | Logs | Metrics | Audit | Provenance |
|---|---|---|---|---|---|
| tenant_id, workload_id, dataset, subject | confidential identifiers | keyed-hash redacted | never | plain (access-controlled evidence store) | plain |
| token claims, MACs, key material | secret | dropped | never | never | never (token_id only) |
| costs, directions, reason codes | internal | plain | bounded labels | plain | plain |
| obligations | policy-controlled | not logged | never | via envelope digest | plain |

Encryption in transit is the transport's responsibility (mTLS in the estate client); the audit store MUST be encrypted at rest with retention ≥ the regulatory retention of the decisions it records. Least privilege: `gravity:explain` is separate from `gravity:recommend`; `gravity:admin` is required for config activation/rollback by the operator tooling.

## 7. Versioning and compatibility — `A03`

* Wire schemas are versioned by name suffix (`/1`, `/2`). A breaking change bumps the suffix; consumers MUST reject unknown schema tags (`G14_INVALID_REQUEST`). Unknown fields are rejected everywhere (strict mode) — additive changes therefore also require a version bump for producers that feed GAP-14.
* `PK_GRAVITY_RECOMMENDATION/1` (engine) is unchanged and still produced by `GravityManager.recommend`. The service emits `PK_GRAVITY_DECISION/2`, whose `recommendation` block is a superset of /1's fields.
* See `COMPATIBILITY.md` for the matrix.

## 8. Component notes (P0/P1/P2)

**P0-01 pk_core.** `compat.handshake()` → `OK | UNPINNED | G14_PKCORE_*`. Certified range `>=1.0.0,<2.0.0`, schema `PK_CHECKLIST/1`, API surface listed in `PKCORE_PIN`. `evaluate_gate` requires certifying handshake, exactly 100 unique checks, zero failures, and every skip approved. `digest` is `None` until release engineering records the certified build digest; until then the handshake is `UNPINNED` = non-certifying.

**P0-02 GAP-13.** One verdict per candidate holding site (`process` at data site, `hold` at compute site). Obligations of every site the chosen option touches are attached to the decision and forwarded to PLN-06.

**P0-03 GAP-03.** Snapshot with id/version/issued_at; per-route `available`, `locality_multiplier`, `egress_per_gb` (asymmetric), `bandwidth_gbps`, `congestion`. Unavailable route eliminates (`ROUTE_UNAVAILABLE`); absent route is an error (I6).

**P0-04 GAP-05.** Proof bound to tenant+dataset; `converged && open_conflicts == 0` or it is treated as not converged; version watermark per dataset; TTL 60 s.

**P0-05 SCH-01.** Tenant-bound snapshot of site availability, architectures, runtimes, free CPU/GPU, quota and storage. Drives `COMPUTE_UNAVAILABLE`, `COMPUTE_INCOMPATIBLE`, `QUOTA_EXCEEDED`.

**P0-06 PLN-06.** Handoff id = hash(decision_id) → idempotent; signed by GAP-14; `not_after` = issue + 300 s; ack must be signed by PLN-06 and echo the id.

**P0-07/08 Identity.** Capability token `PK_CAPABILITY_TOKEN/1`; scopes `gravity:{recommend,handoff,explain,simulate,admin}`; tenant list or `*` (operator only). `WorkloadIdentity(tenant_id, workload_id, environment)` is in the request, provenance, audit, and PLN-06 handoff.

**P0-09 Provenance.** `decision_id`, `issued_at`, `mode`, engine version + model revision, identity, actor, sanitized request, all input refs (topology/placement/convergence/policy/config), `input_digest`, obligations, trace ids. The whole envelope is signed.

**P0-10 Audit.** Hash chain + per-record MAC; `FileAuditSink` fsyncs each append and verifies the existing chain on open. Events: `decision.issued`, `decision.refused`, `handoff.accepted`, `simulation.run`, `dag.planned`, `outcome.recorded`. Config activation events are emitted via `ConfigManager.on_event` and MUST be wired to the same sink at composition.

**P0-11 Config.** Signed `PK_GAP14_CONFIG/1`; transactional activation; revision strictly above the highest ever activated; explicit rollback to a previously verified revision; dev flags refused in production.

**P0-12 Integration.** `tests/fixtures/estate.py` implements every dependency's wire contract with signing and fault knobs. The live estate run (against certified GAP-13/GAP-03/GAP-05/SCH-01/PLN-06) is **not** possible in this build environment and is an open certification item.

**P1-13…21** — see `resilience.py`, `observability.py`, `service.health/explain`; knobs in `OPERATIONS.md`.

**P2-28…39** — `planner.py` (hard constraints: legality, convergence, compute compatibility, quota, thermal, route availability; objective = money + time value × transfer hours + carbon price × kg CO₂, all per run with amortisation), `modeling.py` (Page-Hinkley drift, canary router), `service.simulate/plan_dag/record_outcome`. Without a workload profile the planner is **exactly** the v4.2.0 engine (property-tested).

**P2-40** — `RUNBOOKS.md`.

## 9. Known limitations (carried into the certification decision)

* R-1 HMAC symmetric trust (see §4).
* R-2 CPython GIL: one process sustains ~1.5 k decisions/s with p99 ≈ 1.2 ms in-process, but p99 degrades past 50 ms at ≥ 8 concurrent threads in one process (evidence/bench_*). Deploy **one worker per core, `max_concurrent` ≤ 4 per process**.
* R-3 Replay guard and explain cache are per-process memory; a multi-replica deployment needs a shared replay store (or sticky routing by tenant) to make replay detection global.
* R-4 DAG planning is exhaustive up to `max_batch × 400` assignments, greedy beyond (reported in `method`).
