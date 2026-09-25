# INV-17 Emergency Disable and Quarantine

**Controls:** C059 (checklist §30); C097 (§58).

Source: `control::StreamRegistry.emergency_disable`, `enable`, `quarantine`, `release`, `_admin`, `_gate`; `stream::Stream.freeze`/`unfreeze`.

## 1. Authority

Only principals in `StreamRegistry.admins` (default `{"sre-oncall"}`) may act. Others get `AuthzDenied` and an `authz.denied` audit event. These calls take a principal string, not a capability token; the embedding host must authenticate the operator before calling.

## 2. Controls

| Action | Call | Effect | Audit kind |
|--------|------|--------|-----------|
| Disable component | `emergency_disable(principal, reason)` | `disabled=True`; every stream **not already frozen** is frozen with reason `"component disabled: <reason>"` (existing freeze reasons are kept); `open`/`get`/`write`/`transfer` raise `ComponentDisabled`; `health()` = `disabled`; `/readyz` 503; `inv17_disabled`=1 | `control.disable` |
| Re-enable | `enable(principal, reason)` | `disabled=False`; unfreezes only streams whose `freeze_reason` starts with `component disabled:` | `control.enable` |
| Quarantine scope | `quarantine(principal, scope="tenant"|"workload", value, reason)` → count of streams frozen | adds scope to `frozen_scopes`; freezes matching streams with reason `"quarantine: <reason>"`; registry ops in scope raise `ComponentDisabled` | `control.freeze` |
| Release scope | `release(principal, scope, value)` | removes scope; if not disabled, unfreezes matching streams whose `freeze_reason` starts with `quarantine:` | `control.unfreeze` |

## 3. What freeze does to a stream

- `grant`, `write` → `StreamFrozen`; `write_wait` wakes and raises `StreamFrozen`.
- `read`/`read_wait` continue: buffered data can be drained.
- `end`, `drop_reader`, `drop_writer` still allowed.
- Clients holding a direct `Stream` reference are stopped by the freeze; the registry gate stops new operations.

## 4. Caveats (as implemented)

- Freezes are tagged by reason prefix: `enable` lifts only `component disabled:` freezes, `release` only `quarantine:` freezes. Streams frozen individually via `Stream.freeze` (or already frozen when disable/quarantine ran) stay frozen until `Stream.unfreeze` is called.
- A stream already quarantined when `emergency_disable` runs keeps its `quarantine:` reason, so `enable` leaves it frozen until `release`.
- If `release` runs while disabled, the scope is removed but its streams stay frozen with the `quarantine:` reason; `enable` will not lift them — call `Stream.unfreeze` on them.
- Streams opened after a quarantine but in the scope cannot be opened (gate refuses), so no gap there.
- Controls are in-memory; a restart clears them (spec/crash-semantics.md). Re-apply after restart.

## 5. Procedure

1. Decide scope: smallest effective (workload < tenant < component).
2. Call control, record returned count and `audit.anchor()`.
3. Verify `/explain` `policy.disabled` / `frozen_scopes` and `/readyz`.
4. Mitigate root cause; then `release`/`enable`; confirm health.
