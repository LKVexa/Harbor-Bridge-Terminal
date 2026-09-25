# INV-36 protocol specification and compatibility policy

Byte-level layouts are generated into [WIRE.md](WIRE.md) from `schema/pk_ctrl.idl.json` (the IDL). This document states semantics, the handshake, error handling and the compatibility rules. The IDL format is a small JSON-based definition language chosen over protobuf/FlatBuffers/CBOR because every structure is fixed-order and fixed-width except explicit length-prefixed fields, which keeps a single canonical encoding (no field reordering, no varints, no optional presence bits) and needs no third-party code generator.

## Layering

```
AF_VSOCK stream
  PK_CTRL_STREAM/1   preamble "PKST" 01 00, then records: type u8 | reserved u8 (=0) | length u32
    HANDSHAKE (1)    PK_CTRL_HS/1 messages
    FRAME (2)        PK_CTRL_FRAME/2 sealed frames -> plaintext is PK_CTRL_MSG/1
    CLOSE (3)        graceful close, length 0
```

## PK_CTRL_HS/1

Messages (`magic "PKHS" | version u8 = 1 | type u8`), max 8192 bytes each, 10 s default deadline:

| Message | Fields |
|---|---|
| CLIENT_HELLO (1) | n_suites u8 (1..8), suites u16[n], nonce_c[32], x25519_pub_c[32], credential_c |
| SERVER_HELLO (2) | suite u16, nonce_s[32], x25519_pub_s[32], credential_s, sig_s[64], mac_s[32] |
| CLIENT_FINISH (3) | sig_c[64], mac_c[32] |

`credential = body_len u16 | canonical JSON body | Ed25519 signature by the trust anchor over "PK_CTRL_CRED/1\0" || body`. The body has exactly the fields `v, subject, role, tenant, env, pub, key_epoch, serial, issuer, anchor_version, not_before, not_after, measurement`; non-canonical JSON is rejected.

Key schedule (`H` = SHA-256 over length-prefixed parts):

```
TH1 = H(CH, SH_core)                 sig_s = Sign_s("PK_CTRL_HS/1 server\0" || TH1)
PRK = HMAC-SHA256(key=TH1, X25519(e_c, e_s))
TH2 = H(CH, SH_core, sig_s)          mac_s = HMAC(Expand(PRK, "s fin", TH2), TH2)
TH3 = H(CH, SH)                      sig_c = Sign_c("PK_CTRL_HS/1 client\0" || TH3)
TH4 = H(CH, SH, sig_c)               mac_c = HMAC(Expand(PRK, "c fin", TH4), TH4)
THF = H(CH, SH, CF)
shared     = Expand(PRK, "exporter", THF)     -> PK_CTRL_SESSION/2 shared secret
session_id = Expand(PRK, "session id", THF)   -> 32 bytes
```

Verification order on each side is fixed so error codes are deterministic: trust chain -> environment namespace -> validity window (+/- `max_clock_skew_s`) -> revocation -> key epoch -> role policy -> expected peer -> attestation -> quarantine/limits (server) -> transcript signature -> key confirmation. Suite selection: the server picks the highest suite present in both lists and >= policy minimum; the client refuses a suite it did not offer. Suite 0 is reserved and never valid.

Security goals: mutual authentication, identity binding, forward secrecy (ephemeral X25519), key confirmation, downgrade resistance (the offered list is inside both signatures), role separation (distinct signature labels), replay resistance (fresh nonces/ephemerals, server nonce/session-ID registry), channel binding (session ID and traffic keys derive from the full transcript). **External cryptographic review is required before production** (ADR-0001).

## PK_CTRL_MSG/1

Fixed order: `version u8=1 | flags u8=0 | msg_type u16 | ext_count u16=0 | op_id[16] | tenant lp8 (1..64, [a-z0-9][a-z0-9._-]*) | traceparent lp8 (0 or 55) | body lp32 (<= 65000)`. The decoder consumes exactly all bytes. Unknown `msg_type` -> `UNKNOWN_MESSAGE_TYPE` (not dispatched, channel stays open); any structural error -> `MESSAGE_FORMAT` (channel closed).

Message-type registry: see [WIRE.md](WIRE.md). Assigned range 1-32767; 32768-61439 reserved for future standard use; 61440-65535 private, never emitted by INV-36. New types are added only by a reviewed change to the IDL by the technical owner; numbers are never reused; retired types move to `retired_message_types`.

## Errors

Every refusal maps to a stable code in `errors.ErrorCode`, serialized as `inv36.error/1` (`schema/error.schema.json`): code name and number, disposition (`success`, `degraded`, `retryable`, `denied`, `protocol_error`, `integrity_failure`, `terminal`), `retryable`, `terminal`, bounded message/detail, optional `retry_after_s` for retryable codes only. Numbers are never reused.

## Lifecycle

```
connecting -> preamble -> authenticating -> ready -> (rekey_due) -> draining -> closed
    any state --stream error / integrity failure / quarantine TERMINATE--> closed
```

`ready -> rekey_due` when `session_max_age_s` or `session_max_frames` is reached; the owner opens a new channel (new handshake) and closes the old one gracefully (CLOSE record).

## Compatibility policy

| Change | Allowed within a major protocol version? |
|---|---|
| New message type (new registry number) | Yes (minor IDL revision); old peers answer `UNKNOWN_MESSAGE_TYPE` without closing the channel. |
| New optional field in PK_CTRL_MSG | No in /1: `ext_count` must be 0. A future /1 minor revision may define TLV extensions; until then extensions require /2. |
| New handshake suite | Yes, additive; old peers never select it. |
| Changing widths, order, semantics, or removing a field | No - requires a new major version (e.g. PK_CTRL_MSG/2). |
| Frame/stream major change | New major; both versions may be served on different ports during migration. |

Unsupported versions are rejected deterministically: stream preamble mismatch -> `STREAM_LENGTH_INVALID`; handshake version -> `HS_NEGOTIATION`; frame version -> `FRAME_FORMAT`; message version -> `MESSAGE_FORMAT`. No migration adapters exist for 4.x (`PK_CTRL_FRAME/1`), which remains unsupported.

Deprecation: a protocol version is announced deprecated at least **two minor releases or 90 days** (whichever is longer) before removal, except for emergency security removals, which are announced with the fix. Maximum supported peer skew: current and previous minor release of the same major protocol.

Golden fixtures for every supported version: `fixtures/golden_frames_v2.json`, `fixtures/golden_messages.json`; tests compare current encoders against them and CI fails on drift (`tools/gen_wire.py --check`).
