# State classification, backup and reconstruction (component 24)

| State | Class | Authoritative source | Backup |
|---|---|---|---|
| Source / wheel | immutable, rebuildable | tagged source revision + `tools/release.py` | artifact registry retention |
| WIT + generated bindings | source / rebuildable | `wit/inv20.wit` → `witgen.py` | with source |
| Configuration revisions | mutable, persistent | config repository + `ConfigStore` provenance (digest, author, approver) | config repo history; RPO 0 for approved revisions |
| Policy / capability definitions | mutable, persistent | policy repository; capability signing key in secret store | secret-store backup (owner: UNASSIGNED) |
| Runtime request state | ephemeral | — | **not applicable**: stateless per request; lost on crash by design |
| Cache / connection state | ephemeral, reconstructable | DNS + policy | not applicable |
| Idempotency/replay state | not introduced in 4.3.0 | — | not applicable |
| Audit / evidence | persistent, compliance | append-only audit sink + evidence bundles per release | WORM storage, retention 400 d (proposed) |

Restore order: (1) artifact by digest, (2) approved configuration revision, (3) policy + keys,
(4) verify capabilities/tenant boundaries (run `tests/test_identity.py` + a canary), (5) verify audit
continuity with `verify_audit_stream` against the last published anchor.
RTO: 30 min for a full environment (proposed). A destroyed runtime is reconstructed with
`config.bootstrap_default()` (egress off) and then the approved revision is staged/activated —
deterministic digest proven by `ReconstructionTest`.
