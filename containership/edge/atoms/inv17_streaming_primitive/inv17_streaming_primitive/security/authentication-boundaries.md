# INV-17 Authentication Boundaries

**Controls:** C023, C044
**Owner:** UNASSIGNED — owner to fill
**Status:** DRAFT — describes implemented behaviour; no approval recorded.

## Boundary inventory

| Boundary | Exists? | Authentication | Code |
|---|---|---|---|
| In-process `Stream` API | Yes | **None** — possession of the `Stream` object is the capability | `stream::Stream` |
| Registry API (open/get/write/transfer) | Yes | HMAC-SHA256 capability token, fail closed | `control::StreamRegistry._authorize` -> `security::CapabilityAuthority.verify` |
| Emergency controls | Yes | Principal string allow-list (not cryptographic) | `control::StreamRegistry._admin`, `admins` |
| Configuration activation | Yes | Mandatory `author` and `source_revision` fields (self-declared) | `configuration::ConfigManager.activate` |
| Status/metrics HTTP | Optional | None; binds `127.0.0.1` by default | `observability::serve_status` |
| Component/WIT or network boundary | **No** in this package | N/A — the host/transport layer that introduces it must authenticate | — |
| Adjacent INV adapters | Yes (in-process seams) | None; input validated (`CanonicalCodec.lift`, `OsReadinessBridge.on_ready`) | `adapters` |

## Token format (as implemented)

`base64url(canonical_json(claims)) + "." + base64url(HMAC-SHA256(key[kid], body))`

Claims (`security::Capability.claims`): `aud` (stream id), `ten`, `wl`, `rgt` (sorted rights),
`exp`, `non` (128-bit random nonce), `kid`, `iss` (default `inv17-host`), `v` (=1).

Issue constraints (`CapabilityAuthority.issue`): rights non-empty subset of `security::RIGHTS`;
`0 < ttl <= max_ttl` (default 300 s); ids non-empty strings <= 128 chars.

## Verification order (`CapabilityAuthority.verify`)

1. `right` must be a known right (`ValueError` otherwise — caller bug).
2. Token must be a string with exactly one `.` and <= 4096 chars -> else `AuthError("malformed token")`.
3. Base64/JSON decode -> `AuthError` on failure.
4. `v == 1` and `kid` is a string -> else `AuthError("unsupported token version")`.
5. Key lookup `KeyRing.get(kid)` -> `TrustServiceUnavailable` (outage) or `AuthError` (unknown kid).
6. Constant-time MAC compare (`hmac.compare_digest`).
7. Revocation check (`_revoked`, keyed by body).
8. Expiry against `TrustedClock.now()` (may raise `TrustServiceUnavailable`).
9. Audience / tenant / workload binding -> `AuthzDenied`.
10. Right present in `rgt` -> `AuthzDenied`.
11. Replay: tokens with signed claim `su=true` are rejected on second presentation -> `TokenReplay`; if the replay cache is full the verify fails closed (`TrustServiceUnavailable`, `dependency="replay-cache"`). Non-single-use tokens are not cached.

Registry-side mapping (`control::StreamRegistry._authorize`): each failure class is recorded in the
audit ledger (`trust.unavailable`, `authz.denied`, `auth.replay`, `auth.denied`) and appended to the
bounded decision log, then re-raised.

## Key management

`security::KeyRing`: keys >= 32 bytes enforced; `rotate(kid, key)` makes a new active key while
old keys still verify; `retire(kid)` removes a non-active key (tokens signed with it then fail with
`AuthError("unknown key id")`). Default construction generates a random per-process key — tokens do
not survive restart. Key storage/distribution is the host's responsibility.

## Known gaps

- Direct `Stream` method calls are unauthenticated (by design, object-capability).
- `END_RIGHTS` (reader/writer right sets) is declarative; it is not enforced on `Stream` methods.
- Admin principal is not authenticated.
- Tests: `tests/test_security.py`, `tests/test_adversarial.py` (planned paths).
