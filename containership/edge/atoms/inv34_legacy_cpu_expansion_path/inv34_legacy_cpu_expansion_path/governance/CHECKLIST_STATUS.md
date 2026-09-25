# INV-34 v5.1.0 — checklist execution status (generated)

CI run `ci-20260923T031611Z-633db9` · 2088 items over 74 components + final gate

| Status | Items |
|---|---|
| BLOCKED | 692 |
| OPEN | 48 |
| PARTIAL | 1261 |
| VERIFIED_LOCAL | 87 |

| Component lifecycle | Count |
|---|---|
| Not Started | 3 |
| Designed | 9 |
| Implemented | 21 |
| Verified | 41 |
| Evidence Ready | 0 |
| Production Accepted | 0 |

**Production decision: NO_GO.** No component is Evidence Ready or Production Accepted.

| MC | Lifecycle | Scope | Blockers | Verified / Partial / Blocked / Open |
|---|---|---|---|---|
| GLOBAL | Verified | invariants enforced in code and tests |  | 5 / 1 / 2 / 0 |
| MC-001 | Implemented | pin/lock + fail-closed gate; pk_core itself absent | B-PKCORE | 1 / 15 / 13 / 0 |
| MC-002 | Designed | owner registry shape only | B-OWNER | 0 / 11 / 16 / 0 |
| MC-003 | Verified | 30 SHALL requirements |  | 0 / 19 / 9 / 0 |
| MC-004 | Verified | generated RTM, dangling-link check |  | 2 / 16 / 10 / 0 |
| MC-005 | Verified | Cloud Hypervisor REST adapter vs scripted peer | B-LIVE-HV | 9 / 12 / 9 / 0 |
| MC-006 | Verified | signed guest cpulist observation | B-LIVE-HV | 9 / 14 / 6 / 0 |
| MC-007 | Implemented | API pinned; ACPI revision unpinned | B-OWNER | 3 / 17 / 7 / 0 |
| MC-008 | Implemented | matrix drafted; no live row certified | B-LIVE-HV | 3 / 19 / 6 / 0 |
| MC-009 | Verified | stdlib HTTP boundary; TLS in front not bundled |  | 7 / 16 / 6 / 0 |
| MC-010 | Verified | reference HMAC authn | B-KEYS | 1 / 21 / 7 / 0 |
| MC-011 | Verified | capability policy |  | 2 / 20 / 6 / 0 |
| MC-012 | Verified | in-process quota; not fleet-shared | B-REPLICATED-STORE | 1 / 19 / 8 / 0 |
| MC-013 | Verified | deadline/backpressure; cancel = no side effect only before call |  | 3 / 19 / 6 / 0 |
| MC-014 | Implemented | protocol negotiation; only v1 exists, no mixed-version run |  | 3 / 19 / 6 / 0 |
| MC-015 | Verified | declarative JSON config |  | 1 / 21 / 6 / 0 |
| MC-016 | Verified | provenance JSONL |  | 2 / 18 / 7 / 0 |
| MC-017 | Verified | atomic pointer swap |  | 2 / 20 / 6 / 0 |
| MC-018 | Verified | config rollback; state never rolled back |  | 1 / 19 / 8 / 0 |
| MC-019 | Verified | single-host durable CAS store | B-REPLICATED-STORE | 2 / 20 / 7 / 0 |
| MC-020 | Verified | durable idempotency |  | 4 / 16 / 8 / 0 |
| MC-021 | Verified | lease + fence on shared single-host store | B-REPLICATED-STORE | 1 / 17 / 10 / 0 |
| MC-022 | Verified |  |  | 4 / 18 / 6 / 0 |
| MC-023 | Verified |  |  | 1 / 21 / 6 / 0 |
| MC-024 | Verified | failover via lease expiry on one host | B-REPLICATED-STORE | 0 / 22 / 6 / 0 |
| MC-025 | Verified |  |  | 2 / 20 / 6 / 0 |
| MC-026 | Verified |  |  | 0 / 21 / 7 / 0 |
| MC-027 | Verified | per-VM freeze endpoint; fleet-wide policy not bundled |  | 1 / 19 / 9 / 0 |
| MC-028 | Verified | thresholds PROPOSED | B-APPROVAL | 0 / 22 / 6 / 0 |
| MC-029 | Implemented | partition modelled as adapter/transport loss only | B-FLEET | 0 / 21 / 7 / 0 |
| MC-030 | Verified |  |  | 0 / 24 / 4 / 0 |
| MC-031 | Implemented | env secret source + rotation; no KMS | B-KEYS | 0 / 22 / 6 / 0 |
| MC-032 | Implemented | digests + manifest; unsigned | B-KEYS | 1 / 17 / 10 / 0 |
| MC-033 | Implemented | CycloneDX SBOM generated; no attestation signature | B-KEYS | 1 / 18 / 9 / 0 |
| MC-034 | Verified | local chain; no external anchor |  | 2 / 22 / 4 / 0 |
| MC-035 | Verified |  |  | 0 / 22 / 7 / 0 |
| MC-036 | Verified |  |  | 0 / 24 / 4 / 0 |
| MC-037 | Implemented | multi-process single host; no cross-host | B-FLEET | 0 / 23 / 6 / 0 |
| MC-038 | Verified | emulator faults | B-LIVE-HV | 1 / 21 / 6 / 0 |
| MC-039 | Implemented | adjacent layers in-process | B-LIVE-HV | 0 / 25 / 3 / 0 |
| MC-040 | Implemented | contract vs donor OpenAPI shape, not live API | B-LIVE-HV | 0 / 23 / 5 / 0 |
| MC-041 | Verified | local harness |  | 1 / 15 / 11 / 0 |
| MC-042 | Designed | PROPOSED values | B-APPROVAL | 0 / 16 / 12 / 0 |
| MC-043 | Implemented | steady/burst/fault local | B-FLEET | 0 / 16 / 12 / 0 |
| MC-044 | Implemented | per-VM state bytes + latency; no tenant workload | B-FLEET | 0 / 17 / 10 / 0 |
| MC-045 | Designed | analysis of local path | B-LIVE-HV | 0 / 19 / 9 / 0 |
| MC-046 | Verified | bounded queue/in-flight/journal/idempotency |  | 1 / 17 / 10 / 0 |
| MC-047 | Not Started |  | B-HW | 0 / 0 / 27 / 0 |
| MC-048 | Verified |  |  | 1 / 17 / 10 / 0 |
| MC-049 | Implemented | gate vs PROPOSED limits | B-APPROVAL | 0 / 16 / 11 / 0 |
| MC-050 | Verified |  |  | 1 / 20 / 7 / 0 |
| MC-051 | Verified | Prometheus text |  | 1 / 20 / 7 / 0 |
| MC-052 | Verified |  |  | 1 / 19 / 8 / 0 |
| MC-053 | Verified |  |  | 1 / 18 / 8 / 0 |
| MC-054 | Verified |  |  | 0 / 21 / 7 / 0 |
| MC-055 | Verified |  |  | 1 / 20 / 7 / 0 |
| MC-056 | Implemented | release+config digest on journal/explain; no infra graph | B-DEPLOY | 0 / 19 / 8 / 0 |
| MC-057 | Designed | TELEMETRY_POLICY PROPOSED | B-APPROVAL | 0 / 21 / 7 / 0 |
| MC-058 | Implemented | alert rules; no dashboard backend | B-DEPLOY | 0 / 18 / 9 / 0 |
| MC-059 | Not Started |  | B-FLEET | 0 / 0 / 28 / 0 |
| MC-060 | Not Started |  | B-FLEET | 0 / 0 / 28 / 0 |
| MC-061 | Implemented | gate fails closed | B-PKCORE | 1 / 16 / 10 / 0 |
| MC-062 | Designed | DRAFT | B-OWNER | 0 / 16 / 12 / 0 |
| MC-063 | Implemented | canary evaluator; no deploy system | B-DEPLOY | 0 / 16 / 12 / 0 |
| MC-064 | Designed | DRAFT | B-OWNER | 0 / 16 / 12 / 0 |
| MC-065 | Verified |  |  | 1 / 20 / 7 / 0 |
| MC-066 | Implemented | day0/1/2 local with evidence capture | B-DEPLOY | 0 / 16 / 12 / 0 |
| MC-067 | Designed | DRAFT | B-OWNER | 0 / 14 / 14 / 0 |
| MC-068 | Designed | DRAFT | B-OWNER | 0 / 17 / 11 / 0 |
| MC-069 | Implemented | registry schema, empty | B-OWNER | 0 / 15 / 12 / 0 |
| MC-070 | Implemented | gate evaluates to NO_GO | B-OWNER | 0 / 0 / 16 / 12 |
| MC-071 | Verified |  |  | 2 / 18 / 8 / 0 |
| MC-072 | Verified |  |  | 0 / 0 / 10 / 18 |
| MC-073 | Verified | stdlib AST lint policy (no mypy installed) |  | 0 / 0 / 10 / 18 |
| MC-074 | Designed | no licence invented | B-LICENSE | 0 / 14 / 14 / 0 |
| FINAL | Not Started |  |  | 0 / 0 / 10 / 0 |
