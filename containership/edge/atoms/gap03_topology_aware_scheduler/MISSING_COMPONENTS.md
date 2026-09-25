# GAP-03 missing components — status after v4.3.0

v4.3.0 implements the control plane that v4.2.0 listed as missing (package `controlplane/`, 30+ stdlib-only modules) and
executes the 1,380-check professional checklist against it (`certification/run_checklist.py`, evidence in `evidence/`).

**Reading this table:** *verified* = implementation present and a passing test/artifact that names the check proves it
**locally, by the builder** — no check is claimed complete, because nothing here has been independently verified.
*blocked* = the check needs something this archive cannot contain (named owners, real adjacent services, HSM/KMS,
a production CI/benchmark runner, an exercised procedure, approvals, the missing MASTER.md). Production exit gate: **NO_GO**.

| ID | Component | Pri | Verified | Blocked | Main blocker classes |
|---|---|---|---|---|---|
| MC-001 | Versioned wire/schema definitions for PK_TOPOLOGY/1, PK_LOCALITY_COST/1, and PK_FAIR_SHARE/1 | P0 | 25 | 5 | BLK-OWNER (1), BLK-CI (1), BLK-EXERCISE (1) |
| MC-002 | Authenticated topology mutation boundary | P0 | 24 | 6 | BLK-OWNER (1), BLK-INFRA (1), BLK-KMS (1) |
| MC-003 | Tenant entitlement / reservation authority | P0 | 25 | 5 | BLK-OWNER (1), BLK-KMS (1), BLK-EXERCISE (1) |
| MC-004 | Durable topology state store | P0 | 25 | 5 | BLK-OWNER (1), BLK-CONSENSUS (1), BLK-EXERCISE (1) |
| MC-005 | Durable fair-share ledger | P0 | 25 | 5 | BLK-RUNNER (2), BLK-OWNER (1), BLK-EXERCISE (1) |
| MC-006 | Distributed coordination / leader fencing | P0 | 24 | 6 | BLK-EXERCISE (2), BLK-OWNER (1), BLK-CONSENSUS (1) |
| MC-007 | Distributed atomic placement commit protocol | P0 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-008 | Adjacent SCH-01 integration | P0 | 22 | 8 | BLK-ADJACENT (3), BLK-OWNER (1), BLK-INFRA (1) |
| MC-009 | GAP-02 hardware-capability feed integration | P0 | 24 | 6 | BLK-OWNER (1), BLK-KMS (1), BLK-EXERCISE (1) |
| MC-010 | GAP-14 data-gravity integration | P0 | 25 | 5 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-ADJACENT (1) |
| MC-011 | PLN-05 elasticity/demand integration | P0 | 25 | 5 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-ADJACENT (1) |
| MC-012 | Identity, attestation, and topology-provenance verification | P0 | 24 | 6 | BLK-KMS (2), BLK-OWNER (1), BLK-EXERCISE (1) |
| MC-013 | Tamper-evident security audit log | P0 | 24 | 6 | BLK-OWNER (1), BLK-INFRA (1), BLK-KMS (1) |
| MC-014 | Service-level failure codes and RPC error model | P0 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-015 | Production configuration subsystem | P0 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-016 | Safe degraded-mode/failover policy | P0 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-017 | Emergency freeze/quarantine/disable control | P0 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-018 | Production health/readiness endpoint | P0 | 25 | 5 | BLK-OWNER (1), BLK-INFRA (1), BLK-EXERCISE (1) |
| MC-019 | Metrics exporter | P1 | 25 | 5 | BLK-OWNER (1), BLK-INFRA (1), BLK-EXERCISE (1) |
| MC-020 | Structured logging pipeline | P1 | 25 | 5 | BLK-OWNER (1), BLK-INFRA (1), BLK-EXERCISE (1) |
| MC-021 | Distributed tracing propagation | P1 | 25 | 5 | BLK-OWNER (1), BLK-ADJACENT (1), BLK-EXERCISE (1) |
| MC-022 | Operator explain API/view | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-023 | Dashboard and alert definitions | P1 | 24 | 6 | BLK-OWNER (1), BLK-CI (1), BLK-PROCESS (1) |
| MC-024 | Telemetry privacy/retention/export policy | P1 | 23 | 7 | BLK-INFRA (2), BLK-OWNER (1), BLK-APPROVAL (1) |
| MC-025 | Admission control / load shedding / circuit breaker | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-026 | Retry/backoff/idempotency layer | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-027 | Latency-refinement engine | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-028 | Topology/cost cache with invalidation | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-029 | Multi-objective score composition | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-030 | Capacity/saturation model | P1 | 24 | 6 | BLK-RUNNER (3), BLK-OWNER (1), BLK-EXERCISE (1) |
| MC-031 | Production benchmark baseline and regression gate | P1 | 23 | 7 | BLK-RUNNER (2), BLK-OWNER (1), BLK-CI (1) |
| MC-032 | Fault-injection / partition test suite | P1 | 24 | 6 | BLK-OWNER (1), BLK-INFRA (1), BLK-CI (1) |
| MC-033 | Fuzz/property/adversarial tests | P1 | 26 | 4 | BLK-OWNER (1), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-034 | Adjacent-layer integration/contract test fixtures | P1 | 22 | 8 | BLK-ADJACENT (3), BLK-OWNER (1), BLK-CI (1) |
| MC-035 | Compatibility matrix and multi-platform CI | P1 | 20 | 10 | BLK-CI (4), BLK-OWNER (1), BLK-INFRA (1) |
| MC-036 | Accountable owner and escalation metadata | P2 | 18 | 12 | BLK-OWNER (6), BLK-EXERCISE (2), BLK-INFRA (1) |
| MC-037 | Approved architecture decision record | P2 | 24 | 6 | BLK-OWNER (1), BLK-APPROVAL (1), BLK-PROCESS (1) |
| MC-038 | Full requirements traceability matrix | P2 | 25 | 5 | BLK-OWNER (2), BLK-EXERCISE (1), BLK-RUNNER (1) |
| MC-039 | Original MASTER.md source bundle | P2 | 16 | 14 | BLK-SOURCE (10), BLK-OWNER (1), BLK-EXERCISE (1) |
| MC-040 | Supply-chain manifest/signing/SBOM pipeline | P2 | 18 | 12 | BLK-KMS (3), BLK-RELEASE (2), BLK-OWNER (1) |
| MC-041 | Canary/staged deployment controller | P2 | 25 | 5 | BLK-EXERCISE (2), BLK-OWNER (1), BLK-RUNNER (1) |
| MC-042 | Backup/restore/migration tooling | P2 | 22 | 8 | BLK-INFRA (2), BLK-OWNER (1), BLK-CRYPTO (1) |
| MC-043 | Incident response runbook | P2 | 23 | 7 | BLK-OWNER (2), BLK-EXERCISE (2), BLK-APPROVAL (1) |
| MC-044 | Patch/vulnerability/EOL policy | P2 | 22 | 8 | BLK-OWNER (1), BLK-ADVISORY (1), BLK-CI (1) |
| MC-045 | Exception/waiver/debt registry | P2 | 25 | 5 | BLK-OWNER (1), BLK-INFRA (1), BLK-EXERCISE (1) |
| MC-046 | Formal production exit-gate evidence bundle | P2 | 18 | 12 | BLK-RELEASE (3), BLK-OWNER (2), BLK-EXERCISE (2) |

**Totals:** 1100 locally verified, 280 blocked, 0 failed, 0 weak, 0 unbound of 1380.

## What is still genuinely missing (cannot be produced inside this archive)

- Named accountable owner, on-call rotations, RACI names, CODEOWNERS handles, escalation contacts (MC-036, every CHK-002).
- Real SCH-01 / GAP-02 / GAP-14 / PLN-05 implementations and their exact schemas (only schema-faithful harnesses/fixtures here).
- Production consensus store for the lease (reference majority-lease implementation only) and a replicated durable store.
- HSM/KMS key custody, mTLS transport, organisation signing service, trusted builder, advisory feed, licence scanner.
- Executed CI matrix, controlled benchmark runners with approved thresholds, nightly fault matrix, restore rehearsals.
- Exercised runbooks / game days, approved ADR, approved support policy, communication templates.
- The original `MASTER.md` (see `governance/MC-039_MASTER_md_provenance.json`) — recorded as absent, not fabricated.
- Encryption at rest for backups (no approved cipher in the stdlib; manifest is Ed25519-signed instead).
