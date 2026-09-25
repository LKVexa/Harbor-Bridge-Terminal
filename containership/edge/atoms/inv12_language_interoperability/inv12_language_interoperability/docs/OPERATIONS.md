# INV-12 Operations, Configuration and Ownership

## Configuration (MC-043/044/045)

Documents follow `PK_INTEROP_CONFIG/1` (see `canon/config.py`). Examples in `docs/examples/` are validated by
the unit suite (`DocsExamplesTest`), so they cannot drift from the schema.

* `docs/examples/config.default.json` — secure defaults (all features off, hard-ceiling limits, 4 languages).
* `docs/examples/config.tight-prod.json` — tightened limits, Rust/Go only.

Activation procedure:
1. Edit a copy; increase `revision`.
2. `validate_config(doc)` locally.
3. Collect `approve(doc, approver, key)` from ≥ quorum distinct approvers (digest-bound).
4. `ConfigManager.activate(doc, approvals, actor=...)` — atomic; recorded in the audit chain with approvers.

## Upgrade / downgrade / migration (MC-053)

* **Minor engine upgrade** (4.3.x → 4.y): corpus and profile unchanged → rolling upgrade allowed.
* **Profile or canonical ABI change**: requires negotiated cut-over; both peers must offer the new value
  before either prefers it; old value kept for one minor release.
* **Downgrade**: permitted only to a release whose `RELEASE_EVIDENCE.json` passed; use Runbook B.
* **Schema evolution**: run `check_version_bump(old, new)`; `adapter` class changes need an adapter deployed
  before consumers see new members.

## One-command environment (MC-053)

`python tools/ci.py` builds all fixtures (Rust, Go, Go→Wasm guest, Node) and runs every gate. `pk_core` gates
run when `PK_CORE_PATH` points at the parent framework; otherwise they are recorded as **BLOCKED**.

## Ownership and maintenance (MC-*-55)

| Role | Responsibility |
|---|---|
| INV-12 maintainer (primary) | engine, corpus, profile, releases, on-call |
| Binding owners (Rust / Go / JS / Python) | fixture parity, toolchain upgrades |
| Platform security | threat model, trust primitives, incident P5 |
| Release manager | evidence bundle, signing (when available) |

*Named individuals and escalation contacts must be filled in by the owning organisation before
production GO; they are intentionally not invented here.*

* Cadence: corpus + matrix on every change (CI); full bench + 20k-iteration fuzz nightly; dependency/toolchain
  review monthly; threat-model review each minor release.
* Deprecation: error codes never removed; profiles/ABI deprecated with ≥ 2 minor releases notice.
* Support horizon: current and previous minor release.
