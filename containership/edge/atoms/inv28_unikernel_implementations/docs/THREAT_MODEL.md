# INV-28 threat model (MC-031)

**Owner:** `inv28-security-owner` (see `ops/OWNERS.json`) · **Reviewed:** 2026-09-23 (author review only - independent review pending, see `ops/MC_STATUS.json` MC-031) · **Method:** STRIDE over the data-flow in `docs/ARCHITECTURE.md`.

## Assets

| Asset | Why it matters |
|---|---|
| Register snapshot (`PK_TOOLCHAIN_REGISTRY/1`) | Source of truth for what may be selected |
| Selection policy (`PK_TOOLCHAIN_POLICY/1`) + waivers | Decides what production accepts |
| GAP-15 certificates, advisory feed | External evidence selection relies on |
| Selection ticket (`PK_TOOLCHAIN_TICKET/1`) | Binds a decision to one artifact for INV-27 |
| Audit ledger | After-the-fact accountability and explainability |
| HMAC keys (purposes `registry`, `gap15`, `advisory`, `ticket`) | Everything above is only as authentic as these |

## Actors and trust boundaries

* **Workload owner / scheduler** - submits `PK_TOOLCHAIN_SELECTION_REQUEST/1`; untrusted input.
* **Register operator** - mutates the register through `Registry` with named capabilities.
* **On-call** - holds `emergency` only.
* **GAP-15**, **advisory collector**, **GAP-08** - external services; authenticated by key purpose, never by network position.
* **INV-27** - downstream; trusts nothing but a verified ticket plus the bytes it actually holds.
* Boundaries: request boundary (validation), registry write boundary (authz + CAS), dependency boundary (signature + freshness), build boundary (ticket verification).

## Threats, mitigations, tests

| ID | Threat (STRIDE) | Mitigation | Test |
|---|---|---|---|
| T-01 | Experimental toolchain reaches production (E) | policy floor `min_maturity=mature`; experimental never waivable in production | `tests/test_security.py::test_T01_*` |
| T-02 | Workload silently downgraded to an unsupported runtime (T) | runtime is a first-class constraint; no fallback when requested | `test_T02_*` |
| T-03 | Unmaintained toolchain with no security response lingers (D/E) | contact, review freshness per entry, EOL date and lifecycle all gate production | `test_T03_*` |
| T-04 | Toolchain substitution between selection and build (T/S) | signed ticket binds entry digest + artifact SHA-256; INV-27 hashes the bytes it holds | `test_T04_*`, `tests/test_integration.py::Inv27Binding` |
| T-05 | Forged or edited register (T) | signed snapshot, state digest, head chain, rollback refusal | `test_T05_*`, `tests/test_registry.py::IntegrityAndPersistence` |
| T-06 | Forged GAP-15 certificate (S) | purpose-scoped key; exact artifact/arch/profile match | `test_T06_*` |
| T-07 | Advisory feed suppressed or replayed (T/D) | signed feed; older feed refused; stale feed refuses production | `test_T07_*` |
| T-08 | Waiver abuse: self-approval, bot approval, expired, unwaivable code (E) | approver != owner, service identities refused, expiry, `WAIVABLE` allow-list | `test_T08_*` |
| T-09 | Key confusion / compromise (S) | per-purpose keys, >= 32 bytes; **residual:** HMAC is symmetric (waiver W-002) | `test_T09_*` |
| T-10 | Telemetry leaks tenant/workload identity (I) | keyed pseudonyms, label allow-list, redaction | `test_T10_*` |
| T-11 | Resource exhaustion via hostile inputs (D) | token/set/registry/cache/elimination bounds | `test_T11_*`, `tests/test_ops.py::CapacityModel` |
| T-12 | Unauthorised register mutation (E) | `Authorizer` capabilities per actor | `test_T12_*` |
| T-13 | Clock manipulation to extend reviews/certs (T) | UTC-only aware timestamps; naive `now` refused | `test_T13_*` |
| T-14 | Policy weakened to admit unsafe toolchains (E) | production-rule floor enforced at construction and load | `test_T14_*` |
| T-15 | Audit history rewritten (R) | hash-chained ledger with `verify()`; health degrades on break | `test_T15_*` |

## Residual risks (recorded, not assumed away)

1. **Symmetric keys (T-09).** Any verifier can sign. Needs a KMS plus asymmetric signatures. Waiver W-002.
2. **Trusted clock.** INV-28 refuses naive clocks but cannot tell whether an aware clock is honest. The host must supply one.
3. **Seam-only neighbours.** GAP-15, INV-27 and GAP-08 are verified through the seams shipped here, not against real deployments (MC-041..043 blockers).
4. **Example catalog.** The shipped catalog is illustrative. It cannot be selected in production (`catalog_status=example`), but nobody should read it as a support statement.
