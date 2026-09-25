# INV-61 Exceptions, Waivers & Technical Debt Register (C099)

Every entry needs owner, rationale, risk, compensating control, approval, review date, expiry. **Owner and approval are blank because no owner exists yet (W-001); `tools/exit_gate.py` therefore reports NO_GO until they are filled.**

| ID | Item | Rationale | Risk | Compensating control | Owner | Approved | Review | Expiry |
|---|---|---|---|---|---|---|---|---|
| W-001 | No accountable owner / approvers; ADRs 0001–0004 unapproved | Not determinable from archive | Governance gates cannot close | Roles and escalation structure defined in OWNERS.md | — | — | 2026-10-22 | 2026-12-31 |
| W-002 | `pk_core` not available: 3 gate tests skip; no pinned artifact/digest | Package absent from archive | Original 100-item gate path unreproducible | Runtime decoupled; lazy import with version pin `pk_core==4.0.*`; gate extra declared | — | — | 2026-10-22 | 2026-12-31 |
| W-003 | Original `MASTER.md` unrecovered | Not in archive | Historical wording lost | ADR-0002 supersession + traceability CI | — | — | 2026-10-22 | 2026-12-31 |
| W-004 | Encryption at rest of `state.json` delegated to host volume | Stdlib has no AEAD | Callee outputs on disk in clear if volume unencrypted | Deployment manifest requires encrypted volume; file mode 0600 | — | — | 2026-10-22 | 2027-03-31 |
| W-005 | Not wire-interoperable with Bytecode Alliance `wrpc`; no independent peer fixture | No external implementation available offline | Ecosystem interop | Golden fixtures + open frame spec | — | — | 2026-10-22 | 2027-03-31 |
| W-006 | Adjacent-layer tests use contract stubs for INV-11/60/65/36 | Siblings not in archive | Real integration drift | Stubs encode INV-61 contract exactly | — | — | 2026-10-22 | 2026-12-31 |
| W-007 | Lease authority is in-process reference; no linearizable store | No store in scope | Split-brain across real nodes | Fencing contract tested; ADR-0003 mandates store | — | — | 2026-10-22 | 2026-12-31 |
| W-008 | No side-channel / timing tests | Out of 4.3.0 scope | Info leak via timing | Constant-time MAC compare; authn before lookup | — | — | 2026-10-22 | 2027-03-31 |
| W-009 | Python cannot kill a hung callee thread | Language limitation | Worker pool slot held | Deadline response still returned; breaker; pool bounded; cancel token | — | — | 2026-10-22 | 2027-03-31 |
| W-010 | Cross-architecture (ARM, Windows), Wasm-runtime, multi-host/netns, fleet-scale, soak ≥ 24 h and power measurements not executed | Only a Linux x86-64 container available | Unverified tiers | Pure-stdlib code; CPython 3.10–3.13 matrix executed; CI workflow defines the remaining jobs | — | — | 2026-10-22 | 2026-12-31 |
| W-011 | Release signing (Sigstore/GPG) not performed; provenance is unsigned SLSA-style statement | No signing identity in scope | Artifact authenticity relies on checksums channel | SHA256SUMS + SBOM + provenance generated and verified | — | — | 2026-10-22 | 2026-12-31 |
| W-012 | Dashboards/alerts defined as code but not deployed; SLOs unmeasured in production | No production environment | Detection gaps | `deploy/alerts.yml`, `deploy/dashboard.json` shipped | — | — | 2026-10-22 | 2026-12-31 |

## Deprecated behaviours

| Behaviour | Deprecated in | Removal | Replacement |
|---|---|---|---|
| `rpc.Endpoint` / `PK_WRPC_FRAME/1` in-process dict frames | 4.3.0 | 4.5.0 | `server.RpcService` + `transport` |
| `Endpoint.mismatches` aggregate | 4.2.0 | 4.5.0 | `Endpoint.stats.signature_mismatch` |
