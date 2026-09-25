# Threat model (builder draft — independent security review pending)

**Assets:** correctness of compatibility decisions (a wrong "linkable" can
cause a memory-safety incident across a component boundary); integrity of
release evidence; availability of the classifier.

**Untrusted inputs:** `.wit` sources and dependency packages; PK_INTERFACE /
PK_INTERFACE_DIFF JSON documents; PROVENANCE manifests and signatures;
waiver/deprecation registries.

| Threat | Control | Evidence |
|---|---|---|
| malformed UTF-8 / encoding confusion | strict decode, fatal `E-SRC-UTF8` | test_wit_frontend Negative |
| parser stack exhaustion / hang | `max_nesting`, `max_tokens`, recovery with guaranteed progress, RecursionError trapped | Fuzz.test_pathological_shapes |
| output amplification | diagnostic cap, identifier limit | Limits_ tests |
| comparator blow-up | `WorkBudget` (`max_compare_steps`), memo, coinductive cycle guard | TypeGraph tests |
| JSON duplicate keys / NaN / huge docs | `load_document` rejects; size limit | Schemas tests |
| path traversal in imported packages | `verify_import` refuses paths escaping the package; symlinks not followed by the loader | Provenance tests |
| tampered dependency | digest manifest + Ed25519 signature against explicit trust store | Provenance tests |
| audit log tampering | hash chain; external head for truncation | TelemetryAudit tests |
| waiver abuse | scoped, expiring, non-self-approved waivers; never change class | Lifecycle tests |
| subprocess injection (reference tool) | argv lists, no shell, timeouts | differential.py |
| information disclosure | diagnostics name files by relative path / `<memory:label>`; no source excerpts in evidence | — |

Parser defects that bypass a limit or make an incompatible link "linkable" are
security-impacting: report privately to the security contact in
`OWNERSHIP.json` (currently UNASSIGNED — an owner decision).
