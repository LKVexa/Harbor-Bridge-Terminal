# Configuration: overlays, provenance, atomic activation, rollback (MC-12, MC-13; C032-C038)

## Immutable vs mutable

| Immutable (part of the artifact / base manifest identity) | Mutable (overlays, per site/environment) |
|---|---|
| `schema`, component/provider **names**, links, the set of traits, the package itself | `properties` subtrees of declared components, providers and traits |

An overlay can never add, remove or rename a component, provider, link or
trait — that is a new base manifest (new canonical digest), which goes
through submit/validation like any other.

## Overlays (`overlay.py`, `schema/overlay-v1.schema.json`)

- Scope: `{tenant, environment[, site]}`; must equal the target exactly (`overlay.scope`).
- Parent: `base_digest` must equal the canonical digest of the base (`overlay.stale_parent`).
- Precedence: base → environment overlays (level 1) → site overlays (level 2). Within a level, two overlays touching the same path or an ancestor/descendant path **conflict** (`overlay.conflict`); order in a list or on disk never decides.
- Operations: `set` `{path, value}`, `unset` `path`; path grammar `components[<name>].properties.a.b` (traits addressed as `traits[<type>@<component>]`).
- Authorization: `merge(..., authorize=)` — the host passes `lambda author, ov: authorizer.decide(principal(author), "config.overlay.write", ...).allowed`; unauthorized ⇒ `authz.denied`. Author ≠ approver is mandatory.
- Secrets: the effective manifest is fully re-validated, so an overlay that introduces an inline secret is refused (`manifest.invalid` with `secret.inline` issues).
- Output `PK_APP_EFFECTIVE_CONFIG/1`: scope, base digest, applied overlays (id, version, level, digest, author, approver, approval ref), effective manifest, effective digest. Identical inputs ⇒ identical digest (replayed in tests).
- Dry run: `overlay.diff(base, effective["manifest"])` lists add/remove/replace per path; redact values before showing them outside the owning tenant.
- Export/import for incident reconstruction: the effective-config record is plain JSON without secrets; re-running `merge` on the recorded base + overlays must reproduce `digest`.

## Provenance

Every revision in `ConfigStore` records: revision ID, effective digest, scope,
actor, release version targeted, created time; the journal records
transaction ID, from/to revision, actor and time for PREPARE/COMMIT/ABORT; the
audit ledger records the same with fail-closed semantics. Configuration history
is append-only (journal) + versioned (revisions never deleted).

## Atomic activation (`activation.py`)

Atomicity scope: one `ConfigStore` directory = one `(tenant, environment, site)` target on one node. Not fleet-atomic (fleets use `rollout.py`).

```
propose(effective)  -> validated | rejected          (full validation; quarantine check)
activate(rev, expected_active=CURRENT)               (CAS; activation.conflict on mismatch)
    PREPARE journaled + fsync -> deadline check -> COMMIT journaled + fsync -> snapshot replaced atomically
    -> audit (fail closed) -> optional health probe -> healthy | auto-rollback + quarantine
rollback(to=None|rev)                                (known-good only; idempotent)
reapprove(digest, approver != original actor)        (lifts quarantine)
```

- Deadlines: activation 30 s (`activation_deadline_s`); exceeding it aborts before COMMIT.
- Crash recovery: interrupted PREPARE ⇒ ABORT; journaled COMMIT ⇒ roll forward. Torn final journal line is ignored.
- Automatic rollback triggers: failed validation (never activates), failed post-commit health probe, rollout gate breach (`rollout.py` calls `revert`).
- Status: `ConfigStore.status()` exposes active, active digest, previous known-good, pending, recent failed, quarantined digests, last recovery action; `service.status()` surfaces it and reports `config.activation_in_progress` / `config.none_active`.
- Rollback readiness is a release gate control (`ROLLBACK_DRILL.json`).
