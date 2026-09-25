# INV-65 - Capability providers

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** not present in this archive; see `AUDIT_REPORT_4.2.0.md` (M01)
**Machine-readable gaps:** `MISSING_COMPONENTS_4.3.0.json` (supersedes the 4.2.0 list)
**Release gate:** `conformance/PK_GATE_RESULTS.json` — currently **NO_GO** (P0 blockers M02, M23)

Capability providers are the long-lived processes that give components access to the outside world -- a key-value store, an HTTP server, a message broker -- behind a contract id. One provider serves many links, so the rule that matters is isolation between them: each named link has its own configuration and secret reference, and one component/link cannot see or use another's.

## Responsibility

Own provider lifecycle and link isolation: contract identity, per-named-link configuration, health checking, revocation, and restart without resurrecting revoked links.

## Owns

- Provider contract identity
- Per-named-link configuration and secret references
- Link isolation
- Provider health checks
- Restart with non-revoked link-state restoration
- Durable link revocation

## Explicitly does not own

- Component logic
- The backing services
- Link authorization policy
- Artifact signing
- Scheduling providers

## Non-goals

- Implementing backends
- Authorizing links
- Scheduling

## Interfaces

- `contract` - PK_PROVIDER_CONTRACT/1 - contract id the provider implements
- `health` - PK_PROVIDER_HEALTH/1 - provider health status
- `link` - PK_PROVIDER_LINK/1 - component, link name, config, secret reference

## Service-level objectives

- **isolation** - zero calls served with another link's configuration (error budget: no budget)
- **restart continuity** - every non-revoked link restored after restart (error budget: no budget)
- **call overhead** - p99 provider dispatch under 1ms (error budget: 1% may exceed)

## Running it

```
python -m unittest discover -s inv65_capability_providers/tests -v
python inv65_capability_providers/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-65 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-65 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-65`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-65`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.


## Reference provider hardening in 4.2.0

The in-memory `Provider` model now supports multiple named links per component while preserving the
legacy implicit `default` link API. Link updates and restart snapshots are lock-protected; unlink is
durable across restart; raw link configuration is private; attacker-controlled configuration is
restricted to bounded plain-data shapes; obvious inline secret fields are rejected in favor of secret
references; operations and identifiers are validated; and provider errors expose stable error codes.

`provider.py` remains the conformance/reference model (the invariant oracle).

## Production runtime in 4.3.0

4.3.0 executes the 40-component remediation checklist. The production composition is
`service.ProviderService`, served by `host/server.py` over `transport/http_adapter.py`; see
`docs/architecture.md` for the layer order and `MISSING_COMPONENTS_4.3.0.json` for the honest
disposition of every M01–M40 item (18 closed-local, 18 partial, 4 blocked).

```
# from the directory that contains inv65_capability_providers/
python3 -B -m unittest discover -s inv65_capability_providers/tests -t .     # stdlib only; crypto tests need the [crypto] extra
python3 -B -m inv65_capability_providers.tools.release_gate                  # evidence + gate verdict
python3 -B inv65_capability_providers/tools/verify_evidence.py
python3 -m inv65_capability_providers.host.server --config host.json         # production host (TLS required)
```

The runtime and its tests do **not** need `pk_core`; only `component.py`/`contract.py` (the 100-item
conformance answer) do, and those tests still skip until `pk_core` is supplied and pinned (M02).
`MASTER.md` is still absent and was not fabricated (M01).
