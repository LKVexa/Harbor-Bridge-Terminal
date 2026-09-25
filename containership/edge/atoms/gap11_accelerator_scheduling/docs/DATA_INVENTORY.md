# GAP-11 data inventory (GAP11-*.15)

| Component | Datum | Authoritative source | Confidentiality / integrity | Retention | Versioning |
|---|---|---|---|---|---|
| GAP11-P0-01 | `lease/<id>` | store WAL | integrity: sha256 per record; confidentiality: tenant id is sensitive | until snapshot; usage/ kept for accounting | schema field in record; WAL line format v1 |
| GAP11-P0-01 | `dev/<id>` | inventory adapter -> store | integrity sha256; security_tenant sensitive | life of device | additive fields only |
| GAP11-P0-02 | `__fence__/controller` | store | integrity | forever | monotonic int |
| GAP11-P0-03 | `ctl/leader` | store | integrity | overwritten | fields additive |
| GAP11-P0-04 | `lease/<id>` | store WAL | integrity: sha256 per record; confidentiality: tenant id is sensitive | until snapshot; usage/ kept for accounting | schema field in record; WAL line format v1 |
| GAP11-P0-05 | `idem/<tenant>:<rid>` | store | integrity | idempotency_retention_s | payload digest sha256 |
| GAP11-P0-06 | `dev/<id>` | inventory adapter -> store | integrity sha256; security_tenant sensitive | life of device | additive fields only |
| GAP11-P0-07 | `dev/<id>` | inventory adapter -> store | integrity sha256; security_tenant sensitive | life of device | additive fields only |
| GAP11-P0-08 | `dev/<id>` | inventory adapter -> store | integrity sha256; security_tenant sensitive | life of device | additive fields only |
| GAP11-P0-09 | `attestation quotes` | GAP-06 | integrity | max_age_s | claims additive |
| GAP11-P0-10 | `nonce cache` | memory | integrity | nonce_window_s | n/a |
| GAP11-P0-11 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P0-12 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P0-13 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P0-14 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P0-15 | `lease/<id>` | store WAL | integrity: sha256 per record; confidentiality: tenant id is sensitive | until snapshot; usage/ kept for accounting | schema field in record; WAL line format v1 |
| GAP11-P0-16 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-17 | `lease/<id>` | store WAL | integrity: sha256 per record; confidentiality: tenant id is sensitive | until snapshot; usage/ kept for accounting | schema field in record; WAL line format v1 |
| GAP11-P1-18 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-19 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-20 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-21 | `dev/<id>` | inventory adapter -> store | integrity sha256; security_tenant sensitive | life of device | additive fields only |
| GAP11-P1-22 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-23 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-24 | `audit.jsonl` | controller | integrity HMAC; redacted | policy: 400 days (PROPOSED) | entry format v1 |
| GAP11-P1-25 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-26 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-27 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-28 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P1-29 | `config layers` | operator | integrity digest | last-known-good kept | schema keys additive |
| GAP11-P1-30 | `keys` | KMS | confidentiality | rotation policy (PROPOSED 90d) | kid versioning |
| GAP11-P1-31 | `usage/<lease>` | store | integrity | PROPOSED 400 days | additive |
| GAP11-P1-32 | `dev/<id>` | inventory adapter -> store | integrity sha256; security_tenant sensitive | life of device | additive fields only |
| GAP11-P2-33 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-34 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-35 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-36 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-37 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-38 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-39 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-40 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-41 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-42 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-43 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-44 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-45 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-46 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-47 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-48 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-49 | *(no persistent datum; stateless or document)* | — | — | — | — |
| GAP11-P2-50 | *(no persistent datum; stateless or document)* | — | — | — | — |
