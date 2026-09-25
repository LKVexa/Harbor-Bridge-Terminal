# INV-36 requirements specification (generated from requirements/requirements.json)

Baseline **5.1.0**, approval state **proposed** - every requirement awaits named technical and security owner approval (see docs/GOVERNANCE.md).

Each SHALL statement is atomic and has a verification method. `critical` marks safety/security-critical requirements.

## audit

- **INV36-REQ-029** (functional, critical; verify: test) - Security-sensitive actions SHALL be recorded in a hash-chained audit log with signed checkpoints whose offline verification detects deletion, insertion, reordering and modification. _Source: INV-36-C049._

## authentication

- **INV36-REQ-002** (functional, critical; verify: test) - The transport SHALL mutually authenticate both peers with PK_CTRL_HS/1 before any control message is decoded or dispatched. _Source: INV-36-C023,C044._
- **INV36-REQ-003** (functional, critical; verify: test+analysis) - Session traffic keys SHALL be derived from the full handshake transcript, binding both identities, both ephemeral keys, both nonces, the offered suite list and the selected suite. _Source: INV-36-C023._

## authorization

- **INV36-REQ-012** (functional, critical; verify: test) - Every control operation SHALL pass a single mandatory authorization decision (default deny, explicit deny wins) before any handler side effect. _Source: INV-36-C024,C042._
- **INV36-REQ-014** (functional, critical; verify: test) - When authorization policy is absent, expired or rolled back without recovery authorization, all operations SHALL be denied. _Source: INV-36-C048._

## availability

- **INV36-REQ-046** (non-functional; verify: monitoring; threshold: 99.95% monthly) - Control-channel availability per host/guest pair SHALL be >= 99.95% monthly excluding declared maintenance (proposed SLO). _Source: INV-36-C013._

## backpressure

- **INV36-REQ-023** (functional; verify: test) - Admission SHALL be bounded with high/low water marks and per-tenant quotas; overload SHALL shed optional traffic first and return stable retryable errors. _Source: INV-36-C054,C017._

## bounds

- **INV36-REQ-009** (functional, critical; verify: test+fuzz; threshold: 64 KiB plaintext) - Plaintext SHALL NOT exceed 65,536 bytes and wire records SHALL NOT exceed 65,566 bytes; advertised lengths SHALL be validated before payload allocation. _Source: INV-36-C028,C067._

## capacity

- **INV36-REQ-037** (non-functional; verify: test+benchmark) - Defaults SHALL cap sessions at 256 per process and 64 per tenant; established-session memory SHALL be <= 256 KiB per session pair. _Source: INV-36-C017,C067._

## certification

- **INV36-REQ-043** (functional, critical; verify: test) - Production certification SHALL require a PASS from the pk_core estate gate; SKIP, ERROR or absence SHALL NOT count as PASS. _Source: INV-36-C090,C100._

## compatibility

- **INV36-REQ-040** (functional; verify: test) - Peers SHALL speak PK_CTRL_FRAME/2, PK_CTRL_STREAM/1, PK_CTRL_HS/1 and PK_CTRL_MSG/1; unsupported versions SHALL be rejected deterministically. _Source: INV-36-C016,C027._

## confidentiality

- **INV36-REQ-005** (functional, critical; verify: test) - Every control message SHALL be sealed with AES-256-GCM-SIV under direction-specific keys and nonces before leaving the process. _Source: INV-36-C047._
- **INV36-REQ-006** (functional, critical; verify: test) - Relays SHALL NOT be able to read plaintext or forge frames; relay-supplied routing metadata SHALL NOT influence authorization. _Source: INV-36-C047,C024._

## configuration

- **INV36-REQ-019** (functional, critical; verify: test) - Configuration SHALL be validated (schema, ranges, cross-field, security) before activation; invalid security-critical configuration SHALL NOT activate; unknown fields SHALL be rejected. _Source: INV-36-C033,C034._
- **INV36-REQ-020** (functional; verify: test) - Configuration activation SHALL be atomic, recorded with provenance, rolled back automatically on failed health checks, and SHALL refuse rollback to revoked configurations. _Source: INV-36-C036,C037,C038._

## connectivity

- **INV36-REQ-001** (functional; verify: test+demo) - The transport SHALL carry INV-36 control messages between host and guest over AF_VSOCK SOCK_STREAM connections on the configured port (default 5036). _Source: INV-36-C011,C021,C031._
- **INV36-REQ-038** (functional, critical; verify: test) - Under intermittent connectivity the transport SHALL detect stalls via monotonic thresholds, reconnect with jittered backoff and a fresh handshake, and SHALL NOT infer authoritative state from missing messages. _Source: INV-36-C018._

## cryptography

- **INV36-REQ-004** (non-functional, critical; verify: inspection+test) - Each session SHALL use fresh ephemeral X25519 keys generated from the OS CSPRNG, providing forward secrecy. _Source: INV-36-C047._
- **INV36-REQ-010** (functional, critical; verify: test) - Sending SHALL fail closed before the 64-bit sequence space wraps. _Source: INV-36-C047._

## dependency-failure

- **INV36-REQ-018** (functional, critical; verify: test) - Failures of the time, trust, attestation or key services SHALL fail new session establishment closed with typed errors. _Source: INV-36-C048._

## deployment

- **INV36-REQ-045** (functional; verify: inspection) - Supported deployment contexts SHALL be cloud and datacenter Linux KVM/Firecracker/QEMU hosts; near-/far-edge only where such a host exists; WAN transport is out of scope (GAP-12). _Source: INV-36-C012._

## failover

- **INV36-REQ-025** (functional, critical; verify: test) - Failover SHALL select only residency- and tenant-compatible alternates and SHALL fence stale owners so no two owners are active. _Source: INV-36-C055._

## framing

- **INV36-REQ-011** (functional, critical; verify: test) - Streams SHALL begin with the PK_CTRL_STREAM/1 preamble; non-matching (legacy or foreign) peers SHALL be rejected before any payload processing. _Source: INV-36-C016,C027._

## governance

- **INV36-REQ-048** (functional; verify: test) - The release gate SHALL fail when license, ownership or governance metadata required by the production exit gate is missing. _Source: INV-36-C009,C100._

## health

- **INV36-REQ-021** (functional; verify: test) - The component SHALL expose live/ready/degraded health with reason codes, SHALL NOT report ready while a required dependency is down, and SHALL apply hysteresis. _Source: INV-36-C052,C071._

## interfaces

- **INV36-REQ-034** (functional; verify: test) - All refusals SHALL map to stable machine-readable error codes (inv36.error/1) with retryability and bounded detail. _Source: INV-36-C026._

## isolation

- **INV36-REQ-013** (functional, critical; verify: test) - Operations targeting a tenant other than the authenticated principal's tenant SHALL be denied unless an explicitly approved rule allows it. _Source: INV-36-C046._

## key-custody

- **INV36-REQ-015** (functional, critical; verify: test+scan) - Long-lived keys SHALL be obtained only via secretref:// handles from a KeyProvider and SHALL NOT appear in configuration, logs, evidence, repr or pickles. _Source: INV-36-C039._

## key-rotation

- **INV36-REQ-016** (functional, critical; verify: test) - Identity key epochs SHALL only increase; the previous epoch SHALL be accepted only within the grace window; rollback SHALL require recovery authorization. _Source: INV-36-C047._

## lifecycle

- **INV36-REQ-041** (functional; verify: test+inspection) - Channels SHALL follow the lifecycle connecting -> preamble -> authenticating -> ready -> (rekey_due) -> draining -> closed, with quarantine/failure transitions to closed. _Source: INV-36-C015._

## observability

- **INV36-REQ-030** (functional; verify: test) - Metrics SHALL follow the published catalog with bounded label cardinality and documented units/buckets. _Source: INV-36-C072._
- **INV36-REQ-031** (functional, critical; verify: test) - Logs SHALL be structured JSON with stable identifiers, pseudonymized tenant IDs, redacted secrets/payloads and rate-limited repeats; security events SHALL NOT be debug-only. _Source: INV-36-C073,C075._
- **INV36-REQ-032** (functional; verify: test) - Trace context SHALL be continued only from authenticated in-estate peers and replaced at untrusted boundaries. _Source: INV-36-C074._
- **INV36-REQ-033** (functional; verify: test) - An operator explain view SHALL summarize health, sessions, policy version, queue pressure, quarantine and recent decision reasons. _Source: INV-36-C076,C077._

## ordering

- **INV36-REQ-007** (functional, critical; verify: test) - The receiver SHALL accept only the exact next sequence number and SHALL reject reordered frames without advancing state. _Source: INV-36-C015._

## performance

- **INV36-REQ-035** (non-functional; verify: benchmark; threshold: p99 <= 50 us (certified target)) - Seal+open of a 64-byte frame SHALL have p99 latency <= 50 us on a certified target profile. _Source: INV-36-C062._
- **INV36-REQ-036** (non-functional; verify: benchmark; threshold: see perf/thresholds.json) - In the reference environment, handshake p99 SHALL be <= 50 ms and control-operation round trip p99 <= 25 ms. _Source: INV-36-C062._

## precedence

- **INV36-REQ-039** (functional, critical; verify: inspection) - When requirements conflict, precedence SHALL be: security/integrity > tenant isolation/residency > availability > latency SLO > cost > operator preference. _Source: INV-36-C019._

## quarantine

- **INV36-REQ-027** (functional, critical; verify: test) - Quarantine directives SHALL be signed, versioned, time-bounded, scope-validated, require two approvers for broad scopes, override allow policy, and terminate matching sessions on activation. _Source: INV-36-C059,C092._
- **INV36-REQ-028** (functional, critical; verify: test) - An OS-permission-guarded local kill switch SHALL disable session establishment and dispatch when present. _Source: INV-36-C059._

## recovery

- **INV36-REQ-026** (functional, critical; verify: test) - Cryptographic session state SHALL NOT be persisted or resumed; restart SHALL force a new handshake; persisted metadata SHALL be checksummed, versioned and reject corruption. _Source: INV-36-C057._
- **INV36-REQ-047** (non-functional; verify: test; threshold: RTO <= 5 s) - After a process restart with healthy dependencies the endpoint SHALL be ready within 5 s (RTO). _Source: INV-36-C057._

## replay

- **INV36-REQ-008** (functional, critical; verify: test) - The receiver SHALL reject replayed frames and replayed operation IDs without side effects. _Source: INV-36-C057._

## resilience

- **INV36-REQ-022** (functional; verify: test) - Retries SHALL be bounded, jittered, deadline-aware, budgeted across sessions, and SHALL NOT occur after terminal authentication, authorization, protocol or integrity errors. _Source: INV-36-C053._
- **INV36-REQ-024** (functional; verify: test) - Calls to failing dependencies SHALL be guarded by a circuit breaker with bounded half-open probing. _Source: INV-36-C054._

## revocation

- **INV36-REQ-017** (functional, critical; verify: test) - Revoked credentials or key epochs SHALL be refused at handshake; if revocation data is unavailable or stale the handshake SHALL fail closed unless an approved cache window applies. _Source: INV-36-C048._

## robustness

- **INV36-REQ-044** (non-functional, critical; verify: fuzz) - Parsers for records, frames, messages, handshake messages, configuration, policy and directives SHALL NOT crash or over-allocate on arbitrary input. _Source: INV-36-C085._

## supply-chain

- **INV36-REQ-042** (functional, critical; verify: test) - Releases SHALL carry an SBOM, in-toto provenance and a signature over artifact digests; verification SHALL fail closed on any mismatch. _Source: INV-36-C045,C090._

## Precedence

INV36-REQ-039 governs conflicts: security/integrity > tenant isolation/residency > availability > latency SLO > cost > operator preference.

## Change control

A requirement change must update `requirements/requirements.json`, the affected tests' REQ tags and this generated document in the same change; CI runs `traceability --check`. Each release freezes the baseline by tagging the requirements digest into the gate evidence.
