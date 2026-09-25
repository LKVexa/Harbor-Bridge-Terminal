# GAP-07 production signature profile (PK_SIGNATURE/3)

| alg id | family | key | hash | deterministic | production | strength |
|---|---|---|---|---|---|---|
| `ed25519` | EdDSA (RFC 8032) | Ed25519 | SHA-512 (internal) | yes | yes | 128 |
| `ecdsa-p256-sha256` | ECDSA (FIPS 186-5) | P-256 | SHA-256 | no (RFC 6979 not required) | yes | 128 |
| `ecdsa-p384-sha384` | ECDSA | P-384 | SHA-384 | no | yes | 192 |
| `rsa-pss-sha256-3072` | RSASSA-PSS, MGF1, salt = hash length | RSA 3072, e = 65537 | SHA-256 | no | yes | 128 |
| `rsa-pss-sha384-4096` | RSASSA-PSS | RSA 4096, e = 65537 | SHA-384 | no | yes | 152 |
| `rsa-pss-sha256-2048` | RSASSA-PSS | RSA 2048 | SHA-256 | no | **no** (deprecated 2030-01-01) | 112 |
| `HMAC-SHA256-REF-v2` | v5 reference MAC | shared secret | SHA-256 | yes | **no, reference profile only** | — |
| `rsa-pkcs1v15-sha1` | — | — | — | — | **forbidden** | 0 |

Source of truth: `algorithms.REGISTRY` (exported to `COMPATIBILITY.json`).

## Signed bytes

`ld_encode("signature/3", fields)`:

```
"GAP07" 0x00 "signature/3" 0x00
repeat for v, alg, kid, signer, tenant, site, env, kind, purpose, policy_domain,
           digest_alg, digest, issued_at, nonce, refs:
    u32be(len(name)) name  type-byte  u64be(len(value)) value
type-byte: 0x00 null, 0x01 UTF-8 string, 0x02 decimal integer, 0x03 raw bytes
refs = canonical JSON of the sorted unique list
```

The domain tag separates signature bytes from certificates (`cert/1`), checkpoints (`checkpoint/1`),
signed config (`signed-config/1`), time attestations (`time-attestation/1`), acknowledgements
(`trust-ack/1`) and releases (`release/1`). A signature made in one domain never verifies in another.

## Envelope rules

* Wire form must be canonical JSON (sorted keys, no whitespace); duplicate keys, floats, NaN, BOM,
  lone surrogates, depth > 32 or > 16 KiB are refused before any cryptography.
* `sig` is unpadded base64url; a non-canonical encoding (padding, stray low bits) is refused.
* `alg` must equal the algorithm certified in the signer's `PK_CERT/1` **and** be in the signer's
  authorised algorithm set with strength ≥ `min_strength`. The verifier never infers an algorithm from key shape
  or signature length. The public key must be exactly the type and size the algorithm names.
* `kid` = `tenant/site/env/provider:name@version`, so key ids are unique across namespaces.
* Legacy `PK_SIGNATURE/1` and `/2` are refused by `verify_signature`. `/2` can only be checked by
  `signing.verify_legacy_v2_reference`, which needs a migration approval and an audit ledger, and returns
  `profile: reference`. Production policy never accepts that profile.

## Negative vectors

These are covered in `tests/test_v6_signing.py`: wrong kind, environment, tenant, digest, signer, kid, timestamp,
algorithm, policy domain and digest algorithm, unsorted refs, truncated or padded signatures, missing, extra or duplicate
fields, non-canonical wire form, v1/v2 legacy, key-shape confusion, expiry and future issuance.

## Cross-implementation vectors

`vectors/v6_vectors.json` holds the RFC 8032 test 1 key, the exact signed bytes and signature of a reference
envelope, the `ld_encode`, DSSE PAE and canonical-JSON byte strings, and the RFC 6962 eight-leaf root. Other
verifier implementations (Go, Rust, Wasm) must reproduce these bytes exactly. `tests/test_v6_assurance.py`
pins the published RFC 8032 and RFC 6962 values.
