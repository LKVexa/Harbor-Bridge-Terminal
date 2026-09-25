# INV-27 normative requirements (MC-014; C011–C019)

**Status:** Draft for approval (W-APPROVALS).

The key words SHALL, SHALL NOT and MAY are used as in RFC 2119. Every requirement names the test
that verifies it.

## Source function

The source function is: application plus only the required OS primitives (C011).

| ID | Requirement | Verified by |
|---|---|---|
| S-01 | INV-27 SHALL derive the syscall surface, capabilities and single-address-space property of an image from the image bytes. It SHALL NOT accept a caller claim as evidence. | `test_seal.CallerClaimsAreNotEvidence` |
| S-02 | INV-27 SHALL refuse any image that links process creation, exec, a runtime loader, or a debug/shell surface. | `test_seal.SealBreakers` |
| S-03 | INV-27 SHALL refuse dynamically linked images (PT_INTERP or DT_NEEDED). | `SealBreakers` |
| S-04 | INV-27 SHALL admit an image only when the manifest syscall set equals the derived set and that set is a subset of the site's permitted set. | `CallerClaimsAreNotEvidence` |
| S-05 | INV-27 SHALL bind every admission to the image's sha256. It SHALL execute only the bytes whose digest was verified. | `test_seal.Identity`, `test_service.Boot` |
| S-06 | INV-27 SHALL require a valid signature from a key in the current trust root over a provenance statement that binds the digest and names an approved builder and toolchain version. | `test_seal.Signatures` |
| S-07 | INV-27 SHALL fail closed on unknown formats, unknown toolchains, missing evidence, parser errors, stale trust roots, or an unavailable/unapproved VMM. | `test_parser`, `Signatures`, `test_service.Boot` |
| S-08 | INV-27 SHALL enforce the boot contract: the entry is in exactly one executable segment, there is no W+X segment, a named entry symbol equals e_entry, and memory is sufficient. | `test_seal.BootContract` |
| S-09 | INV-27 SHALL attach only what the site isolation policy allows. It SHALL NOT attach anything named only in the manifest. | `test_seal.Isolation`, `test_qemu_plan_is_hardened_and_attaches_only_the_plan` |
| S-10 | A refused image SHALL cause zero VMM, device, network or storage side effects. | `test_service.ZeroSideEffects` |
| S-11 | INV-27 SHALL record, for every automated decision, a decision record naming each step and the facts it used. | `test_service.Observability` |

## Deployment contexts (C012)

INV-27 runs in `dev`, `staging`, `prod` and `edge` (`config.validate`). The following apply only to `prod`:

- It SHALL require a source digest in provenance.
- It SHALL refuse the script (test) VMM backend.
- Attested-facts mode needs the explicit `attested_facts_approved` flag.

## Outcomes (C013–C014)

Every outcome is one of `success`, `refused`, `terminal`, `retryable` or `degraded`, with a stable
code (`errors.REGISTRY`, `ops/ERROR_CODES.json`). Retry is permitted only for `retryable` codes, and
only for idempotent operations.

## Lifecycle (C015)

The lifecycle is defined in `docs/LIFECYCLE.md`, which is generated from `lifecycle.TRANSITIONS`.
Illegal transitions SHALL raise `UK_ILLEGAL_TRANSITION` and leave the state unchanged.

## Capacity and fairness (C017)

See `docs/CAPACITY.md`. Per-tenant token buckets plus a global in-flight cap SHALL shed load before
any work starts. A per-tenant instance quota SHALL be enforced atomically.

## Disconnected operation (C018)

See `docs/DISCONNECTED.md`. Admitted instances keep running (fail static). New admissions SHALL stop
once the cached trust root is older than its maximum age (fail closed).

## Precedence (C019)

Precedence is security > residency > SLO > cost. It is strict and lexicographic
(`precedence.resolve`); no weight lets cost buy back security.

## Degraded operation (MC-055)

- Telemetry loss SHALL NOT fail a decision (`Logger.failures` counts it).
- A full audit buffer SHALL refuse new events (`OverflowError`) rather than drop them.
- A missing optional crypto backend SHALL refuse to write plaintext.
