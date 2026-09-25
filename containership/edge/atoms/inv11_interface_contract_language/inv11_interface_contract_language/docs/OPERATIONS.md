# Operations (telemetry, audit, lifecycle, ownership)

**Telemetry** (`wit.ops.Telemetry`): closed counter set
(`definitions_parsed, parse_failures, classifications, breaking, additive,
compatible, link_refusals, limit_breaches, resolution_failures`), latency
histograms `compare_ms`/`parse_ms` with fixed buckets (milliseconds), a
saturation gauge, Prometheus text via `prometheus()`. No labels carry package
names or paths. Telemetry never feeds back into classification. Mapping to a
vendor stack is an adapter concern.

**Audit** (`wit.ops.AuditLog`): append-only JSONL hash chain; each event binds
subject fingerprints, decision, tool version and UTC time (time is not an
integrity proof). `verify(expected_head)` detects edits, deletions, reordering
and — with the externally recorded head — truncation. Writes are fsynced;
a write failure raises (fail closed).

**Deprecation** (`wit.lifecycle.DeprecationManager`): removal of a symbol is
refused unless it was deprecated, its grace deadline has passed and no known
consumer remains. Consumer discovery is best-effort over supplied worlds; "no
observed consumers" is not "proven none".

**Waivers** (`wit.lifecycle.WaiverRegistry`): fields `id, owner, rationale,
scope, codes, expires, approved_by, audit_ref`; wildcard/empty scope,
expired, self-approved or incomplete waivers are ignored. Scope covers the
exact symbol and its descendants only. A waiver changes the gate result, never
the structural class.

**Adapters** (`wit.lifecycle.adapter_plan`): generated only for additive
diffs (projection that hides additions); every other change is refused with
the blocking changes listed.

**Ownership**: `OWNERSHIP.json`, validated by `ops.load_ownership()`. The
accountable owner and escalation contacts are placeholders until the owner
assigns them, so the ownership gate reports BLOCKED.
