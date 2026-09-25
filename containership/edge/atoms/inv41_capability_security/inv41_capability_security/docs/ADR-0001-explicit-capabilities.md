# ADR-0001 — Explicit capabilities are the authorization primitive for INV-41

| Field | Value |
|---|---|
| Status | **PROPOSED** (not approved — needs `security_approver` + `accountable_owner`, see `BLOCKERS.json` B-OWN-01) |
| Deciders (required) | accountable_owner (proposed: David Paul Russell), security_approver (UNASSIGNED) |
| Date proposed | 2026-09-22 |
| Review by | 2026-12-21 (90-day cadence, `OWNERS.json`) |
| Supersedes / superseded by | — / — |
| Change rule | Any change to construction, authenticity, attenuation, revocation or serialization semantics requires a new ADR revision reviewed by the security approver (CODEOWNERS enforces two reviewers). |
| Immutability | The approved text is hashed into `dist/RELEASE_MANIFEST.json` `spec_hashes` per release. |

Referenced from README.md, SECURITY.md, docs/THREAT_MODEL.md, docs/REQUIREMENTS.md and the traceability matrix.

## 1. Decision

Inside one process, authority to act on a resource is **possession of an authentic, same-domain capability object** (`Reference`) that was explicitly passed in. No name-based lookup, global registry or caller-supplied token confers authority. `Authority` is the only minting root; `Holder` is an immutable bundle bound to one domain; `Reference.attenuate` can only narrow; `Membrane` revokes every live descendant.

## 2. Expected security properties

| Object | Property |
|---|---|
| `Authority` | Owns a 256-bit random seal and an immutable resource→operations policy. Constructing one creates a new, isolated domain; it grants nothing in any other domain. |
| `Reference` | Guarded construction; HMAC-SHA256 seal over (authority id, token, resource, sorted ops); immutable; non-serializable; `repr` redacted. |
| `Holder` | Immutable, domain-bound; resolves only explicitly bound aliases. |
| Attenuation | Monotonic: result ⊆ parent; widening fails closed (`Widening`). |
| `Membrane` | Revocation is shared by every wrapped, attenuated and nested-wrapped descendant; survives re-wrapping; revoked references cannot be used, delegated, wrapped or bound. |

## 3. Trust boundary

The pure-Python implementation is a **logical** capability boundary against *accidental* ambient authority and API misuse by cooperating code. It is **not** a boundary against hostile code in the same interpreter (reflection, `gc.get_objects`, `object.__setattr__`, monkey patching, module replacement, `ctypes`, debuggers, native extensions). Adversarial workloads MUST run behind a process/Wasm/VM/hardware boundary (`isolation.py` supplies the process tier; namespaces/seccomp/Wasm/microVM are B-ISO-01, waiver WVR-001).

## 4. Why these choices

* **Process-local, non-serializable references.** A serialized reference is a bearer token: it can be copied, replayed and exfiltrated, and revocation would then need to find every copy. Keeping references in-memory means possession cannot outlive the process and revocation needs no distributed state. Cross-process use goes through the `CapabilityBridge` with opaque, session-bound handles.
* **Seal tied to the authority domain, not textual IDs.** Two authorities may share an id string (tests prove an impostor with the same id is refused); authenticity is the HMAC under a secret only the minting domain holds.
* **Monotonic, fail-closed attenuation.** Widening on delegation is the classic confused-deputy escalation; refusing (not clamping) makes misuse visible.
* **Membrane revocation through nesting and derivation.** A revocable wrapper that can be bypassed by attenuating or re-wrapping is not revocation. Every minted descendant registers with every membrane in its chain (weak references, so accounting reflects live objects).

## 5. Alternatives considered

| Alternative | Assessment |
|---|---|
| ACL / RBAC only | Authority follows identity, not the object in hand → ambient authority and confused deputies inside a process. **Complementary**: RBAC may decide the *bootstrap policy* of an `Authority` (see `identity.PrincipalBinder`). |
| Signed bearer tokens / macaroons | Portable and attenuable (caveats), but serialization implies replay risk, key management, clock-based expiry and revocation lists. **Chosen for the cross-process tier only** in the form of opaque session handles, not as in-process authority. |
| OS process sandbox / Wasm / microVM / hardware (CHERI) | Real hostile-code boundaries; far higher cost per call and operational weight. **Required tier for adversarial code**, layered *under* this design, not replaced by it. |
| Central policy decision point (OPA-style) | Single policy source and audit, but every check becomes a network call: availability coupling, latency, and a control-plane outage becomes an authorization outage. Rejected for per-call checks; acceptable for issuing bootstrap policy (signed config, `config.py`). |

**Implications:** ~5–13 µs p50 per core operation on the reference host (`evidence/bench.json`); no external dependency; auditability via the broker; compatibility governed by `contracts/INTERFACES.json`.

## 6. Invariants and where they are enforced

| Invariant | Enforced by | Runtime assumption | Tests |
|---|---|---|---|
| I1 Non-forgeability | guarded `__init__`, HMAC seal | CPython object model not subverted | PR001, CT011, mutants M01/M02 |
| I2 Non-widening delegation | `attenuate`, `grant` | — | PR002, mutants M03/M04 |
| I3 Authority-domain isolation | `_assert_authority` (id **and** seal) | seal secrecy in memory | PR003, CT006, M05 |
| I4 Holder immutability | `__slots__` + sealed `__setattr__`, `MappingProxyType` | no `object.__setattr__` by hostile code | CT005 |
| I5 Revocation closure | `_mint_reference` registers with every membrane; `_assert_live` | lock semantics of `threading.RLock` | RC001–RC007, PR006, M06/M07 |
| I6 Secret redaction | `__repr__`, `errors.describe`, `telemetry.redact`, audit `_check_safe` | — | CT010, PR005, BT002, M08/M19 |
| I7 Non-serializability | `__reduce__`/`__reduce_ex__`/`__copy__`/`__deepcopy__` | — | CT009, M09/M09b |

Behaviour under: **concurrency** — revocation is linearizable at `revoke()` return (REQ-CON in docs/REQUIREMENTS.md); **exceptions** — every failure path raises, none returns a permit; **`python -O`** — no assert defines security (CT015); **serialization** — refused; **introspection** — out of scope (§3).
