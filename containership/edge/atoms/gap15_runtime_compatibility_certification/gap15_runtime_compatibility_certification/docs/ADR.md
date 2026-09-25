# GAP-15 Architecture Decision Records

Status legend: **Proposed** = written by the build, not yet approved by a named
architecture/security reviewer. Every ADR below is *Proposed*; approval is an
open blocker (see `evidence/CHECKLIST_EXECUTION.md`, controls MC-42-07 and MC-42-09).
Superseded ADRs are kept and marked, never deleted.

| ADR | Title | Components | Modules | Status |
|---|---|---|---|---|
| ADR-001 | Storage engine and consistency model | 01, 11, 15 | `production/store.py` | Proposed |
| ADR-002 | Append-only ledger and audit chain | 02, 12 | `production/store.py`, `production/state.py` | Proposed |
| ADR-003 | Cryptographic trust model | 03, 07 | `production/ed25519.py`, `production/signing.py`, `production/authn.py` | Proposed |
| ADR-004 | Identity, attestation and provenance binding | 04, 05 | `production/provenance.py`, `production/attestation.py` | Proposed |
| ADR-005 | API/IDL, schema evolution and canonicalisation | 09, 14 | `production/schemas.py`, `production/canonical.py`, `production/http_api.py` | Proposed |
| ADR-006 | Partitioning, multi-site topology, replication, DR | 15, 25 | `production/partition.py`, `production/store.py` | Proposed |
| ADR-007 | Observability / audit separation, classification, retention, privacy | 12, 26, 27 | `production/observability.py` | Proposed |
| ADR-008 | Lifecycle, EOL, waivers and policy precedence; fail-open/closed matrix | 13, 20, 21, 23, 24, 49 | `production/state.py`, `production/policy.py`, `production/offline.py` | Proposed |
| ADR-009 | Runtime capability and negotiation model | 16, 17, 18, 19 | `production/capability.py`, `production/versions.py`, `production/negotiation.py`, `production/features.py` | Proposed |

---

## ADR-001 — Storage engine and consistency model

**Context.** v4.2.0 kept the matrix in process memory with an in-memory revision
counter (audit residual risks 1, 2, 5). Certification needs transactional,
crash-consistent persistence with lost-update protection.

**Decision.** SQLite (Python stdlib) per node, `journal_mode=WAL`,
`synchronous=FULL`, all writes in `BEGIN IMMEDIATE` transactions (single writer,
serializable). `meta.matrix_revision` is the compare-and-swap token; writers may
pass `expected_revision` and receive `E_REVISION_CONFLICT`. The ledger is the
source of truth; `matrix` is a derived materialisation rebuilt from the ledger
on recovery if it ever diverges.

**Guarantees.** Atomic commit of ledger events + matrix rows + revision + audit
rows; durability on `COMMIT` return (fsync); RPO 0 for committed events on the
node; RTO bounded by restore + replay (measured by `test_measured_rpo_rto`).

**Alternatives considered.** PostgreSQL (SERIALIZABLE, streaming replication) —
better for multi-node, but a server dependency the package cannot ship;
etcd/Raft — right consistency model for multi-site, but not stdlib.

**Consequences.** Single-node durability only. **Quorum loss / replication is
not implemented**: multi-replica operation needs a replicated store (Postgres or
Raft) behind the same `Store` interface. Until then, strong-freshness decisions
must be served by the one authoritative node (MC-11-07 / MC-37-06 blocker).

**Security/reliability impact.** Triggers make the ledger and audit tables
append-only inside the database; tampering outside the triggers is detected by
the hash chain on every open.

## ADR-002 — Append-only ledger and audit chain

**Decision.** Two SHA-256 hash chains (`ledger`, `audit`) with
`entry_hash = SHA256(prev_hash | canonical_body)`; UPDATE/DELETE triggers;
periodic signed checkpoints over both heads (`Store.checkpoint`) exported to an
independent location; JSONL export verifiable with no database. Corrections,
withdrawals, supersession, revocation, quarantine and conflict resolution are new
events. Historical verdicts are reproduced by `state.replay(upto_seq)` and the
same pure `state.certify` used live.

**Known limit.** A chain cannot detect *tail truncation* by itself; the signed
checkpoint exported off-box is the compensating control (the last exported head
must still be present).

## ADR-003 — Cryptographic trust model

**Decision.** Ed25519 (RFC 8032, strict: non-canonical S rejected) implemented in
pure Python so the package stays stdlib-only; SHA-256 digests; domain-separated
signing input `GAP15-SIG/1|type|environment|version|canonical-json`. Versioned
trust store with per-key validity window, scope set and compromise flag.
Algorithm agility: an explicit allow-list (`ed25519`) and a deprecated list that
returns `E_SIG_ALG_DEPRECATED`. Private keys only behind `KeyProvider`; the
development provider refuses production mode.

**Consequences.** The pure-Python implementation is **not constant-time**. It is
acceptable for verification (public data) but production *signing* must be
delegated to an HSM/KMS provider (MC-03-07, blocker: no HSM available to this
build). FIPS validation is not claimed.

## ADR-004 — Identity, attestation and provenance binding

**Decision.** Artifact identity is `sha256:<hex>` + media type; provenance is an
in-toto Statement / SLSA v1 predicate signed under the GAP-15 envelope with a
closed field set; the SBOM must name the same digest. Node evidence is a signed
`GAP15_QUOTE/1` bound to a service-issued single-use nonce; the runtime profile
id is **derived** from attested measurements, never taken from the caller.

**Consequences.** Real GAP-02 (TPM2/SEV-SNP/TDX quote formats) and GAP-07
(DSSE envelopes, builder roots) integrations are not present; the interfaces are
shaped to receive them. Recorded as blockers MC-04-02 and MC-05-02.

## ADR-005 — API/IDL, schema evolution and canonicalisation

**Decision.** JSON over HTTP(S) with JSON Schema (2020-12 subset) as the IDL;
the same Python dict is both the published schema and the validator input.
Canonical JSON: sorted keys, no whitespace, UTF-8, NFC strings, no floats, no
duplicate keys, 64-bit integer range. Schemas are versioned independently
(`SCHEMA_SET_VERSION`); `schemas.diff` classifies breaking changes for the gate.
API major version is in the path (`/v1`); other majors are rejected.

## ADR-006 — Partitioning, multi-site topology, replication and DR

**Decision.** Partition = `tenant/environment/site`, canonical DNS-label form,
leading column of every key and index; evidence is never reused across
partitions. Restore refuses a backup whose partitions are not the expected set
(no implicit remap). Cross-site **replication and export are not implemented**;
the rule when they are: data may leave a site only to an encryption domain that
satisfies that site's **residency** policy, sensitive identifiers are hashed,
and conflicts are resolved by ledger order per partition (never last-writer-wins
across partitions). Failover/failback automation is a blocker (MC-15-08).

## ADR-007 — Observability / audit separation, classification, retention, privacy

**Decision.** Audit is a chained database table committed in the same
transaction as the change it records; application logs are a separate sink and
changing log level or retention cannot remove audit history. Metrics use a
closed label vocabulary (no artifact/node/trace/signer ids). Logs hash node,
artifact, signer and subject ids (`h:` prefix) and redact secret-bearing keys.
Retention: ledger and audit are retained for the life of the certification
authority (legal hold by default); logs 30 days; traces 7 days. Access to audit
reads requires `audit.read`.

## ADR-008 — Lifecycle, EOL, waivers, precedence; fail-open/fail-closed matrix

**Decision.** Lifecycle states `active → deprecated → blocked-for-new → end-of-life`,
any → `revoked` (terminal), reactivation only as a new `reactivated-by-waiver`
event carrying a waiver id and two-person approval. Verdict precedence:
revocation > quarantine > open conflict > lifecycle > evidence; then the policy
engine (domain-ranked, deny-overrides, revocation/integrity non-waivable).

| Dependency down | Behaviour |
|---|---|
| Trusted time | fail closed: no decisions (`E_TIME_UNTRUSTED`), readiness false |
| Store / chain verification | fail closed: readiness false, no writes |
| Identity / revocation list stale | fail closed: `E_AUTH_REVOCATION_STALE` |
| KMS/HSM | signing paths unavailable; verification continues |
| Provenance / attestation trust | evidence rejected; existing verdicts unchanged |
| Control plane (edge) | offline bundle only, within its hard expiry; absence never allows |
| Metrics / tracing backend | fail open for traffic, alert on scrape age |

## ADR-009 — Runtime capability and negotiation model

**Decision.** Typed capabilities with layer + provenance strength; closed
registries for core fields, `x-<vendor>.` extensions untrusted until recognised;
explicit `UNKNOWN`. Versions per namespace (`semver`, `spec`, `date`, `build`);
ranges must be explicitly upper-bounded (no caret/tilde/wildcard widening).
Negotiation outputs a deterministic transcript and only establishes *capability
fit*; certification still requires exact evidence. Adapters/shims are modelled
explicitly and only trusted ones are applied.
