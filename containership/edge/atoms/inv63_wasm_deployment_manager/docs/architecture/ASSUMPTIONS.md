# INV-63 Architecture Assumptions Catalogue

| Field | Value |
|---|---|
| Document ID | INV63-ARCH-ASSUMPTIONS |
| INV-63 C-IDs covered | C005 (with C012, C018, C040) |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Architecture reviewer (role), SRE lead (role), Security reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change (including any edit to `preflight.py`, `config.py::validate`, `deploy/config/**` or `pins.json`). |

## 1. Machine-checked assumptions (A-01..A-08)

Implemented by `preflight.py::run`; readiness is `preflight.ready(checks)` (all checks with `required=True` must pass) and is surfaced by `service.py::DeploymentService.status` (`ready` also requires leadership — `journal.epoch == journal.current_epoch()` — and `controls.global_disabled == False`). Failing a *required* check is fail-closed (not ready); failing a *preferred* check is reported in `status()["preflight"]` and the service keeps running (degrade).

| ID | Assumption (title as in `preflight.py`) | Scope | Req./Pref. | Runtime detection | Violation behaviour |
|---|---|---|---|---|---|
| A-01 | Python runtime >= 3.11 | global | required | preflight `A-01` (`sys.version_info >= (3, 11)`) | fail-closed, `INV63-E-PRECONDITION` |
| A-02 | Host inventory non-empty with spread labels | site | required | preflight `A-02` (every host id and label a non-empty string) | fail-closed, `INV63-E-INSUFFICIENT-CAPACITY` |
| A-03 | At least two failure domains for spread | site | preferred | preflight `A-03` (distinct label count >= 2) | degrade; no error code. At placement time `reconcile_ns` records `"spread relaxed: residency/security precede SLO spread"` in the decision when eligible hosts span < 2 labels and `count > 1` |
| A-04 | Durable state directory writable + fsync | site | required | preflight `A-04` (mkdir, `mkstemp`, write, `os.fsync`, unlink in `state_dir`) | fail-closed, `INV63-E-DEPENDENCY-UNAVAILABLE` |
| A-05 | Clock skew within bound | site | preferred when no reference time is supplied (reported as failed, `"no reference time source"`); **required** when `reference_time` is passed | preflight `A-05` (`abs(clock() - reference_time) <= max_clock_skew_s`, default 30 s) | with reference: fail-closed, `INV63-E-PRECONDITION`; without: degrade (reported only) |
| A-06 | Lattice/control plane reachable | site | preferred | preflight `A-06` (`adapter.ping()`) | degrade to offline mode, `INV63-E-CONTROL-PLANE-OFFLINE` recorded on the check |
| A-07 | Crypto provider present (cryptography pinned) | global | required iff `require_signed_artifacts` (the `crypto_required` argument, as passed by `status()`) | preflight `A-07` (`security.HAVE_CRYPTO`) | fail-closed, `INV63-E-DEPENDENCY-UNAVAILABLE`; independently `security._require_crypto` fails signature/seal calls closed |
| A-08 | Wasm runtime advertises component-model + WASI P2 | workload/site | preferred | preflight `A-08` (`{"wasi-p2","component-model"} <= runtime_capabilities`) | degrade (reported). `status()` passes `adapter.capabilities()` (`InMemoryLattice.capabilities`, or `WadmAdapter.capabilities` via the transport `capabilities` op) |

## 2. Non-machine-checkable assumptions (A-09+)

| ID | Assumption | Scope | Req./Pref. | Runtime detection | Violation behaviour |
|---|---|---|---|---|---|
| A-09 | DNS / name resolution for the lattice transport endpoint is correct and stable (transport is injected into `adapter.WadmAdapter`; not bundled) | site | required | not machine-checkable (surfaces indirectly as A-06 failure) | degrade: `_observe` returns False → offline mode, `INV63-E-CONTROL-PLANE-OFFLINE` / `INV63-E-DEPENDENCY-UNAVAILABLE` |
| A-10 | NAT/firewall permits the outbound NATS/Wadm path (B-10) and the inbound API path (B-01) | site | required | not machine-checkable | as A-09; inbound blocked = no requests (externally observed only) |
| A-11 | Every peer, network path and store can fail independently (`contract.py::build` assumptions) — no correlated failure between journal disk and lattice | global | required | not machine-checkable | journal failure: `INV63-E-DEPENDENCY-UNAVAILABLE`/`INV63-E-STATE-CORRUPT` (fail-closed); lattice failure: degrade |
| A-12 | `fsync` on the state filesystem is honoured (no write-back cache lying; not tmpfs/overlay without durability) | site | required | not machine-checkable (A-04 only proves the call succeeds) | silent loss of acknowledged records after power loss; detected on next open only if it produces a broken chain (`INV63-E-STATE-CORRUPT`) |
| A-13 | Only one controller per `state_dir` holds a lease; the `epoch` file is on a filesystem with atomic `rename` visible to all contenders (local disk; not an eventually consistent network FS) | site | required | partially: `Journal.append`/`compact` detect a newer epoch (`INV63-E-STALE-EPOCH`) and concurrent size change (`INV63-E-CONFLICT`) | fail-closed on write. Fencing is single-host only; no distributed consensus lease (waiver DEBT-001, evidence key `consensus-lease`) |
| A-14 | Callers are untrusted until authenticated; token keys (>= 32 bytes) are delivered via `secret_refs.token_keys` (`file:`/`env:`, JSON `{kid: hex}` — `tools/bootstrap.py`) | tenant | required | `TokenAuthority.__init__` rejects short keys (`INV63-E-CONFIG-INVALID`); `resolve_secret_ref` fails `INV63-E-DEPENDENCY-UNAVAILABLE` when missing | fail-closed |
| A-15 | Host labels in the inventory reflect real, independent failure domains (zones) | site | preferred | not machine-checkable (A-03 counts labels only) | spread guarantees are nominal only |
| A-16 | `residency_labels` config correctly maps each host to its jurisdiction | tenant | required for residency workloads | not machine-checkable | wrong placement; if no host matches, `INV63-E-POLICY` |
| A-17 | Lattice actually starts/stops what the adapter requests and `healthy()` is truthful | workload | required | partially: `_observe` re-reads `list_instances` after actions; rollout checks `adapter.healthy` | rollout: `INV63-E-ROLLOUT-FAILED` + automatic rollback |
| A-18 | Behaviour is identical whether a dependency is local or remote (`contract.py` assumption) | global | required | not machine-checkable | n/a |
| A-19 | Node identity/attestation (TPM, measured boot) is provided by the platform | site | required for production | not implemented; evidence key `node-attestation` open | none in code — open item |
| A-20 | A KMS or equivalent delivers 32-byte data keys for `security.Sealer` | site | required when `require_encryption_at_rest` | not implemented (key comes from `secret_refs.data_key`, hex, resolved by `tools/bootstrap.py`); evidence key `kms` open | `Sealer` rejects wrong key length `INV63-E-CONFIG-INVALID`; `DeploymentService` refuses to start without a Sealer when `require_encryption_at_rest` (`INV63-E-CONFIG-INVALID`) |

## 3. Near-edge / far-edge assumptions

| Item | Code fact |
|---|---|
| Tiers | `PK_DEPLOY_CONFIG/1` `tier`; default `cloud` (`config.SECURE_DEFAULTS`); `dc-1` overlay = `datacenter`; `edge-site-a` overlay = `far-edge` |
| Autonomy window | `offline_autonomy_s`, default 3600 s |
| Far-edge rule | `config.validate` rejects `tier == "far-edge"` with `offline_autonomy_s < 300` → `INV63-E-CONFIG-INVALID` |
| `deploy/config/site/edge-site-a.json` | `tier: far-edge`, `offline_autonomy_s: 86400`, `max_inflight: 8`, `queue_depth: 64`, `reconcile_interval_s: 120` |
| Offline inside window | `reconcile_ns`: `_observe()` False → append `offline_intent` to journal, move to `DEGRADED`, decision `defer_offline`, outcome `DEGRADED` |
| Offline beyond window | `mono() - offline_since > offline_autonomy_s` (monotonic clock, immune to wall-clock jumps) → `INV63-E-CONTROL-PLANE-OFFLINE` (RETRYABLE), `retry_after_s = reconcile_interval_s` |
| Rollouts offline | `op_rollout` refuses: `INV63-E-CONTROL-PLANE-OFFLINE` |
| Resync | `DeploymentService.resync()`: when `_observe()` succeeds, reconciles each pending namespace; SUCCESS ones journaled as `resynced` and removed from `pending`; others stay pending. `tick()` calls `resync()` first whenever `pending` is non-empty |
| Edge assumptions not checked | wall-clock drift during long offline periods (A-05 needs a reference time which is often absent offline; affects token nbf/exp, not the autonomy window); journal disk endurance on flash; power loss frequency (A-12) |

## 4. Open items
- A-12, A-13, A-19, A-20 require external evidence (storage qualification, consensus lease, node attestation/TPM, KMS). None has been performed.
- Architecture review of this catalogue (evidence key `arch-review`) not performed.
