# INV-12 Canonical Interop Engine — Normative Specification

**Spec version:** 1.0.0 (engine 4.3.0) · **Status:** normative for `canon/` · **Keywords:** MUST, MUST NOT, SHOULD, MAY per RFC 2119/8174.

This document is the normative design record for the missing components MC-001 … MC-018 plus the
operational components that shape their behaviour. Requirement IDs (`REQ-<MC>-<n>`) are stable and are
referenced from `docs/TRACEABILITY.md`, the tests and the release evidence.

## 0. Scope, callers and trust boundaries

* **In scope:** schema loading, canonical types, validation, numeric/Unicode policy, canonical memory
  layout, guest-memory access, realloc/post-return lifecycle, resource handles, error envelope,
  negotiation/evolution, async values, limits, and the observability/config/trust controls that gate them.
* **Out of scope (non-goals):** compilers, WIT authoring tools, composition linking, host function
  implementations, placement, and shipping a production Component Model runtime (the engine defines the
  seam; see `COMPATIBILITY.md`).
* **Callers:** a component runtime adapter (reference: `canon.boundary.Boundary`; real-Wasm harness:
  `tools/wasm_host.mjs`), language bindings (Rust/Go/JS/Python fixtures), CI and release tooling.
* **Callees:** guest `cabi_realloc` / `post_return`, guest exports, the trust service (tokens, trusted
  time), the configuration store, the audit sink.
* **Trust boundaries:** (1) every byte of guest memory and every guest-returned pointer is untrusted;
  (2) every schema and descriptor is untrusted input; (3) configuration is trusted only after quorum
  approval; (4) capability tokens are trusted only after MAC, key-id, expiry and capability checks.

## 1. Global invariants

| ID | Requirement |
|---|---|
| REQ-G-1 | The engine MUST NOT exhibit implementation-defined behaviour: every input either produces the specified result or a registered `PK_INTEROP_*` error. |
| REQ-G-2 | Validation MUST complete before any allocation in guest memory, handle movement, I/O or authorization side-effect. |
| REQ-G-3 | No host object MAY alias guest memory or caller-owned mutable containers after a boundary operation (copy-in, copy-out). |
| REQ-G-4 | Correctness MUST NOT depend on `assert`; behaviour under `python -O` MUST be identical (tested). |
| REQ-G-5 | All size/offset arithmetic MUST be checked against the u32 address space; overflow is `PK_INTEROP_MEMORY_OVERFLOW`. |
| REQ-G-6 | Diagnostics MUST NOT contain payload values, secrets or unbounded attacker strings (`MAX_DETAIL_CHARS`=160, `MAX_PATH_SEGMENTS`=32). |
| REQ-G-7 | Registries, snapshots and resolved types MUST be immutable after construction. |

## 2. MC-001 Schema loader and type AST

* REQ-001-1 The grammar in `canon/types.py` is normative; input outside it MUST fail with `PK_INTEROP_SCHEMA_SYNTAX` carrying `line:column`.
* REQ-001-2 Duplicate declarations, fields, cases, flags, parameters or interfaces MUST fail with `PK_INTEROP_SCHEMA_DUPLICATE`.
* REQ-001-3 Unresolved names, bare resource names used as types, and `own/borrow` of undeclared resources MUST fail with `PK_INTEROP_SCHEMA_UNRESOLVED`.
* REQ-001-4 Any recursive named type MUST fail with `PK_INTEROP_SCHEMA_RECURSIVE` (WIT forbids recursion).
* REQ-001-5 Limits: schema ≤ 1 MiB, ≤ 4096 declarations, ≤ 1024 fields/cases/flags, ≤ 256 tuple elements, type depth ≤ 64 → otherwise `PK_INTEROP_SCHEMA_LIMIT` (never `RecursionError`).
* REQ-001-6 parse → resolve → `Interface.canonical()` → sha256 MUST be deterministic and independent of whitespace, comments and declaration order; the digest is the interface identity.

Valid: `interface a { record p { x: u8 } f: func(v: list<p>) -> result<u32, string>; }`
Invalid: `interface a { record r { x: r } }` → `PK_INTEROP_SCHEMA_RECURSIVE at /r`.

## 3. MC-002/003 Type set; tuple, enum, flags

* REQ-002-1 Primitives are exactly `bool s8 u8 s16 u16 s32 u32 s64 u64 f32 f64 char string`; ranges are the two's-complement / unsigned ranges of their width.
* REQ-003-1 `tuple` is positional and arity-exact (Python host: `tuple` only). `enum` has 1..1024 cases; `flags` has 0..1024 names.
* REQ-003-2 Flags values are sets of declared names; undeclared names on lower (`PK_INTEROP_INVALID_FLAGS`) and undeclared bits on lift MUST be rejected (stricter than the upstream spec, which ignores them).

## 4. MC-004/005 Resource handles, own and borrow

* REQ-004-1 A handle is meaningful only in the table that issued it; foreign handles MUST fail `PK_INTEROP_HANDLE`.
* REQ-004-2 Slots carry a generation; a handle whose generation does not match (stale after drop/reuse) MUST fail `PK_INTEROP_HANDLE`. Index 0 is never valid.
* REQ-005-1 `own<R>` lowering MOVES the handle; the source handle becomes stale; the destructor runs exactly once on the final drop.
* REQ-005-2 `borrow<R>` is scoped to one `CallScope`; own handles with outstanding borrows MUST NOT be moved or dropped (`PK_INTEROP_BORROW`).
* REQ-005-3 A callee returning while holding a borrow MUST fail the call with `PK_INTEROP_BORROW`; the borrow is revoked and the lender's count restored (fail-safe).
* REQ-005-4 Two-table operations MUST lock in ascending `table_id` order.

## 5. MC-006 Recursive validator and MC-018 limits

* REQ-006-1 Every nested field/element/case payload MUST be validated against its declared type; errors carry the full path (e.g. `["shapes", 1, "rect", 1, "y"]`).
* REQ-006-2 Only exact built-in host types are admitted; subclasses MUST be refused before any user hook executes. Cycles MUST be refused.
* REQ-006-3 The result is a detached copy (REQ-G-3).
* REQ-018-1 Limits (`depth 64, list items 100 000, nodes 200 000, string 16 MiB, total 64 MiB, handles 10 000, concurrent calls 1024, stream window 1024`) form the hard ceiling. Interface- and type-level overrides MAY only tighten it; a loosening override MUST be rejected at construction.
* REQ-018-2 Limits MUST be checked before the proportional work (e.g. list length before iteration, string code-point count before UTF-8 encoding).

## 6. MC-007 Registry, MC-008 numeric policy, MC-009 Unicode

* REQ-007-1 Every supported language profile MUST map every canonical kind exactly once, to an exact representation or an explicit refusal (`None`). The profile digest (`PROFILE_DIGEST`) is what configuration pins.
* REQ-008-1 Numeric conversion is exact-or-refuse (policy `exact/1`): no wrap, clamp, saturate or rounding. JS `Number` → integer only for safe integers; `-0.0`, NaN, ±∞ never become integers; f64→f32 only when exact.
* REQ-008-2 NaN is canonicalized on store (`0x7fc00000`, `0x7ff8000000000000`); ±0 and ±∞ are preserved.
* REQ-009-1 Strings are sequences of Unicode scalar values encoded as UTF-8; lone surrogates, overlong forms, truncated sequences and code points > U+10FFFF MUST fail `PK_INTEROP_ENCODING`; no U+FFFD substitution; no normalization.

## 7. MC-010 Layout, MC-011 guest memory, MC-012 lifecycle, MC-013 variants

* REQ-010-1 Size, alignment and field offsets MUST follow the table in `canon/layout.py` (Component Model canonical ABI). Golden images in `fixtures/corpus/vectors.json` are normative test vectors.
* REQ-010-2 Flattening: `MAX_FLAT_PARAMS`=16, `MAX_FLAT_RESULTS`=1; beyond that values pass indirectly.
* REQ-011-1 Every guest-memory access MUST be bounds-, overflow- and alignment-checked, in that order; reads are copy-out.
* REQ-012-1 Every region returned by a guest `realloc` MUST be validated for alignment, bounds and overlap with live allocations (`PK_INTEROP_REALLOC`).
* REQ-012-2 Lifecycle `IDLE→LOWERING→CALLED→RETURNED→DONE` (or `LOWERING→ROLLED_BACK`); post-return runs exactly once; every allocation is released exactly once; a second post-return or double free MUST fail `PK_INTEROP_LIFECYCLE`.
* REQ-013-1 Discriminant width is u8 (≤256 cases), u16 (≤65 536) else u32; payload at `align_to(disc, max case align)`; discriminants ≥ case count MUST fail `PK_INTEROP_INVALID_DISCRIMINANT`.
* REQ-013-2 Zero-size list elements with a count above 1 000 000 MUST fail `PK_INTEROP_LIMIT` (decompression-bomb guard).

Worked example (`option<option<u32>>`, value `Some(Some(9))`): size 12, align 4 → `01 000000 01000000 09000000`.

## 8. MC-014 Error envelope

`PK_INTEROP_ERROR/1` = `{schema, code, path, source_language, target_language, interface, type_id, retryable, detail}`; exactly these keys. Codes are registered in `canon/errors.py::ERROR_CODES` and are append-only. `retryable` is a property of the code unless overridden by the raiser.

## 9. MC-015 Negotiation and MC-016 evolution

* REQ-015-1 Each dimension (canonical ABI, mapping profile, each interface) resolves to the highest mutually offered value; interfaces match within one semver MAJOR; no overlap or a policy-floor violation fails closed (`PK_INTEROP_VERSION`).
* REQ-015-2 The agreement includes a transcript digest over both canonicalized offers (downgrade detection).
* REQ-016-1 Additions are `compatible` (MINOR); appended enum/variant/flags members are `adapter` (MAJOR unless an adapter is deployed); every other structural change is `breaking` (MAJOR). A declared version bump smaller than required fails `PK_INTEROP_INCOMPATIBLE`.

## 10. MC-017 Async

Future and Stream state machines are specified in `canon/async_model.py`. Writes are validated and copied before enqueue; streams apply backpressure at `window` and timeouts are retryable `PK_INTEROP_LIMIT`; cancellation wakes all waiters and discards buffered elements with accounting. Async values are not yet supported over the reference runtime adapter (explicit `PK_INTEROP_ASYNC`).

## 11. Operational controls (MC-037 … MC-049)

Metrics use a closed label vocabulary (unknown label values fold to `other`); spans accept only allow-listed attributes; audit records are hash-chained and HMAC-sealed; health is `HEALTHY | DEGRADED | BLOCKED`; admission control enforces per-tenant fair shares. Configuration `PK_INTEROP_CONFIG/1` is validated, quorum-approved, atomically activated as an immutable snapshot, and rolled back deterministically. Capability tokens are verified before lowering; trust outages fail closed for privileged actions and allow only previously verified, unexpired tokens within `grace_s` for data-plane calls; loss of trusted time fails closed for everything.
