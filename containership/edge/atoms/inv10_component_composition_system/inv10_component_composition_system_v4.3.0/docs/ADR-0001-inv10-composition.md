# ADR-0001 — INV-10 composition technology and function decisions (MC-20)

* **Status:** Proposed — awaiting approver signature (see `docs/OWNERSHIP.md`). Not approved by this build.
* **Date:** 2026-09-22 · **Release:** 4.3.0

## Context
INV-10 4.2.0 shipped a correct pure linker but lacked schemas, adjacent-layer ports, a control plane,
security/observability layers and release evidence (50 residual components, MISSING_COMPONENTS.md).

## Decisions
1. **Pure core, layered services.** `composition.compose` stays dependency-free and unchanged; every new
   capability wraps it. Rationale: identity stability (4.2.0 ids == 4.3.0 ids) and independent testability.
2. **Stdlib only.** No runtime third-party deps. Consequence: HMAC-SHA256 used for artifact/release
   signatures and tokens; an asymmetric verifier (Sigstore/ed25519) must be plugged via the same
   `verify` / `KeyProvider` interfaces before multi-party trust is claimed.
3. **Ports for adjacent layers.** INV-09/11/12 and PLN-02 are `Protocol` ports with fail-closed reference
   implementations, not reimplementations of those layers.
4. **Fail-closed defaults.** Link policy default-deny; unknown environment ⇒ external unavailable; missing
   provenance ⇒ rejected; degraded key service ⇒ refuse to sign/verify.
5. **Files, not databases.** Store, activation pointer, idempotency journal, audit and config ledger are
   append-only JSONL / atomically renamed JSON (safe on synced folders; no SQLite).
6. **Optional capabilities are explicit and recorded.** Aliasing and dead-export elimination are opt-in
   pre-link rewrites whose parameters are bound into `extension_digest`.

## Consequences / residual risk
Reference adapters are not the real INV-09/11/12/PLN-02 services; production claims need integration with
those services and the qualified `pk_core`. Performance evidence is from a single host (see evidence/).
