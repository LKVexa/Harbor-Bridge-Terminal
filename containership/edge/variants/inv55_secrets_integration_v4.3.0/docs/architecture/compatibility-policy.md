# Compatibility and versioning policy

| ID | INV55-ARCH-COMPAT | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Protocol negotiation (`service.py::SecretsService.negotiate`)

- Every request MUST carry `protocol` of the form `PK_SECRET_<NAME>/<n>` (n: 1–3 digits).
- Supported set is `service.py::PROTOCOLS`: `PK_SECRET_RESOLVE/1`, `PK_SECRET_ROTATE/1`, `PK_SECRET_SCOPE/1`. Anything else → `UNSUPPORTED_VERSION` (terminal, 400).
- There is no "best common version" downgrade: the caller MUST pick an exact supported version. Supported versions are advertised in `health()["protocols"]`.
- `negotiate(protocol, expected)` MUST reject a protocol family that does not match the operation (e.g. `PK_SECRET_SCOPE/1` on `resolve`) with UNSUPPORTED_VERSION. Evidence: `tests/test_service_contract.py::ResolveUseContract.test_unsupported_and_mismatched_protocol`, `test_tolerant_reader_ignores_unknown_fields`.

## Tolerant reader

- Request handlers read only the keys they need via `request.get(...)`; unknown fields MUST be ignored (current behaviour).
- Responses MAY gain new fields in a minor release; clients MUST ignore unknown response fields.
- Removing or changing the meaning of a field, error code, or outcome REQUIRES a new protocol major (`/2`).

## Error-code stability

- `ErrorCode` code strings (e.g. `INV55-E001-DENIED`) MUST NOT be renumbered or reused. New codes MAY be added.

## Deprecation window

- When `/2` of a protocol ships, `/1` MUST remain in `PROTOCOLS` for at least two minor releases or 6 months, whichever is longer (proposed; `status: PENDING-OWNER-APPROVAL`).
- Deprecation MUST be announced in `CHANGELOG.md` and waiver-register.md.
- No deprecation telemetry (per-version request counts) exists; `inv55_requests_total` has no `protocol` label. NOT IMPLEMENTED.

## Package/semantic versioning

- `service.py::__version__` = `4.3.0`. MAJOR = breaking wire/behaviour change; MINOR = additive; PATCH = fixes.
- Downgrade: the state file format is `inv55-state/1` (`SecretsService._load_state` refuses other formats); the audit chain resumes via `audit.resume_from_file`. A package that predates these features would ignore both.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Protocol-family check now enforced |
