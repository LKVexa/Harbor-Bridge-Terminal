# GAP-10 Architecture Decision Records

Status key: **Accepted** = implemented and tested in 4.3.0. **Proposed** = needs owner/reviewer sign-off before production.

## ADR-0001 — Scope, authoritative data and trust boundaries

- **Status:** Accepted (sign-off pending, see EXCEPTION_REGISTER EX-001)
- **Context:** v4.2.0 produced a ceiling but trusted every caller and had no integration surface.
- **Decision:** GAP-10 owns the per-node ceiling decision only. Authoritative inputs are (a) GAP-09 envelopes verified by `TelemetryAdapter`, (b) the active signed policy revision from `PolicyService`, (c) the calibration inventory, and (d) signed operator controls. Trust boundaries are: GAP-09 → adapter (HMAC + attestation + scope), author/approver → policy service, operator → control plane, GAP-10 → consumers (fencing token + decision id). Everything else is untrusted.
- **Non-goals:** placement, fan/governor control, node lifecycle, accelerator allocation, sensor attestation.
- **Consequences:** Every component in `docs/COMPONENTS.md` names its scope, non-goals, fail-closed default and permissions against this boundary.

## ADR-0002 — Fail-closed everywhere; restriction is monotone under failure

- **Status:** Accepted
- **Decision:** No failure path (missing, stale, forged, replayed, untrusted clock, store outage, lost lease, partition, consumer without decision) may yield a less restrictive ceiling. Derived signals (prediction, cooling domain, accelerators, battery runtime) can only *raise* severity and are capped at `critical`; only observed emergencies exclude. Every error code is in `FAIL_CLOSED`.
- **Consequences:** Availability is traded for safety: a GAP-10 outage stops new admission (`FailClosedContract.absent_fraction = 0`). Operators can choose a small positive fraction ≤ critical, recorded as an exception.

## ADR-0003 — Leadership, fencing and durable state

- **Status:** Accepted for semantics; **Proposed** for backing store.
- **Decision:** One controller per shard via `LeaseManager` with monotonically increasing fencing tokens. Tokens are checked by the controller before each decision, by `FileStateStore.save`, and by `CeilingView.publish`. The in-process lease and file store implement the contract; production must back `LeaseManager` and `PolicyService` with a linearizable store (etcd/Consul/SQL CAS) exposing the same methods.
- **Consequences:** Split-brain cannot publish or persist a stale decision. Multi-host HA requires the external store (EX-002).

## ADR-0004 — Signatures: HMAC-SHA256 now, asymmetric in production

- **Status:** Accepted with exception EX-003
- **Decision:** Telemetry, policy, controls and release provenance are authenticated with capability- and scope-bound HMAC-SHA256 keys (stdlib only). Verification is behind `KeyRing.verify` / `build_release.verify` so an HSM/KMS or Sigstore-backed asymmetric implementation can replace it without API change.
- **Consequences:** HMAC gives integrity and authentication but not non-repudiation; the verifier holds the secret. Accepted for 4.3.0 with a dated exception.

## ADR-0005 — Constraint precedence

- **Status:** Accepted
- **Decision:** Order: thermal-safety > emergency-operator > security > residency > maintenance > SLO > cost. Every source is an *upper bound*; the effective fraction is the minimum. Requests for more capacity are recorded (`ignored_increase`) and never override a higher-precedence bound.

## ADR-0006 — Uncalibrated hardware defaults

- **Status:** Accepted
- **Decision:** Nodes without a validated calibration entry use `UNKNOWN_PROFILE` (throttle 70 °C), which yields thresholds tighter than the generic defaults. Emergency is always set ≥5 °C below vendor throttle so GAP-10 acts before firmware.
