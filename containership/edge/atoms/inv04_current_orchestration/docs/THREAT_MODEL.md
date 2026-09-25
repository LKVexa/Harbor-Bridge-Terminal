# INV-04 Threat Model (v4.3.0)

- **Status:** Draft for independent review. Components #73 and C041 stay open until someone other than the author reviews it.
- **Method:** STRIDE applied per trust boundary. Each mitigation links to code and tests.

## Assets

| Asset | Why it matters |
|---|---|
| Workload availability during drains | A bad drain causes an outage (contract threat "maintenance drain causing an outage") |
| Desired-state authority | Corrupting it turns reconciliation into an attack |
| Drain / config / audit journal | Needed for crash recovery, idempotent replay, and forensic trail |
| Hand-off inventory to SCH-01 | Losing workloads during migration (contract threat) |
| Credentials: signing keys, bearer tokens, kubeconfig | Full control of the orchestrator |
| Tenant namespace mapping | Cross-tenant disclosure or mutation |

## Trust boundaries

1. **Caller → Service** (HTTP): untrusted until authenticated.
2. **Service → Cluster API** (port `ClusterAPI`): the API server is trusted for state, but its responses may be stale or reordered.
3. **Replica ↔ replica** (lease): the peer may be paused or partitioned, so it counts as a stale writer.
4. **Service → successor scheduler** (hand-off): at-least-once delivery over an unreliable channel.
5. **Operator → config/journal files on disk.**

## Attacker capabilities considered

A malicious tenant with valid credentials; a compromised workload sending forged requests; replay of captured requests; a stale ex-leader; a network attacker without mTLS; an insider editing the journal; hostile payloads (size, nesting, NaN, invalid UTF-8).

## STRIDE analysis

| Threat | Boundary | Mitigation (code) | Evidence (tests) | Residual |
|---|---|---|---|---|
| Spoofed caller | 1 | `security.TokenAuthenticator`: signature, iss, aud, exp, nbf, max TTL, key-id rotation | `test_runtime_interface.py::SecurityTest` | HS256 shared keys; OIDC/JWKS not integrated (#27) |
| Spoofed peer / MITM | 1, 4 | mTLS delegated to mesh (ADR-0001); loopback bind default | — | **Open (#29)** |
| Cross-tenant read | 1 | `scope_filter`: unmapped namespaces are invisible; RBAC `$own` tenant rule | `SecurityTest`, `ServiceTest` | Namespace→tenant map is operator-maintained |
| Cross-tenant / unauthorised mutation | 1 | Deny-by-default `Authorizer`; `AdmissionPolicy` (windows, frozen tenants, per-site concurrency) | `SecurityTest` | Drain is granted only to `inv04:site-operators` (cluster-scoped), never via the per-tenant rule |
| Replay / duplicate drain | 1 | Mandatory idempotency key; same key with a different body is refused | `JournalTest`, `ServiceTest` | 24h TTL |
| Tampering with journal | 5 | SHA-256 hash chain; `JournalCorrupt` on open | `JournalTest` | Not externally anchored or signed (#50) |
| Stale leader writes (split brain) | 3 | Lease plus fencing token; `FencingGuard` in the API port | `LeaseTest`, `DrainTest::test_stale_fencing_token_cannot_evict` | Server-side token enforcement needed in production |
| Stale cache decisions | 2 | `Informer.require_fresh`; UID + resourceVersion preconditions on every write | `InformerTest`, `StoreTest` | — |
| Budget bypass through preemption | 2 | `preemption_candidates` excludes PDB-protected pods | `SchedulingTest` | — |
| Repudiation | 1, 5 | `AuditTrail` requires an authenticated actor | `JournalTest` | — |
| Info disclosure in logs and errors | all | `redact()` on journal, logs and spans; `problem()` never leaks internal exceptions; low-cardinality metrics | `ObservabilityTest`, `NegotiationAndMappingTest` | — |
| Hostile payload DoS | 1 | 4 MiB cap, depth 16, 100k items, NaN rejection, token-bucket rate limit, bounded queues | `SchemaFixtureTest`, `FuzzTest`, `ServiceTest::test_rate_limit_sheds_load` | No per-tenant limiter on the HTTP path yet (#32) |
| Secret leakage | 5 | `Secret` type: no repr, no pickle; env/file references only | `SecurityTest::test_secrets_never_render` | No external secret manager (#43) |
| Supply chain | release | Stdlib-only runtime, SBOM, manifest, provenance statement | `tools/release.py --verify` | Artifacts unsigned until the owner's cosign identity exists (#66) |

## Abuse cases → tests

1. A tenant drains a node hosting another tenant's workloads. `DEFAULT_RULES` grants `drain` only to `inv04:site-operators`. Tenant operators get `ORCH_FORBIDDEN` (`SecurityTest::test_rbac_deny_by_default_and_tenant_scope`).
2. A captured drain request is replayed. The replay returns the recorded result, and no second eviction happens (`ServiceTest::test_drain_end_to_end_with_idempotent_replay`).
3. A paused ex-leader resumes and evicts. It is fenced out (`DrainTest::test_stale_fencing_token_cannot_evict`).
4. Someone edits a journal line after the fact. The next start refuses with `ORCH_JOURNAL_CORRUPT` (`JournalTest`).

## Safe behaviour when dependencies are unavailable (C048)

| Dependency down | Behaviour |
|---|---|
| Identity or keys | All requests fail with 401. No mutation. |
| API server | Readiness fails, circuit breaker opens, drains abort before eviction and roll back the cordon. |
| Clock skew beyond 30 s | Tokens are rejected. Lease renewals fail, so the replica steps down. |
| Journal disk | `append` raises and the side effect is not attempted (write-ahead). |
