# Exception / waiver / technical-debt / deprecation ledger (MC-71)

| ID | Type | Item | Owner | Expires / trigger | Status |
|---|---|---|---|---|---|
| W-01 | waiver | Reference authenticator/key store used until GAP-06/07 exist | owner | sibling delivery | open |
| W-02 | debt | Revocation fsync per record (no batching) | eng | write rate > 1k/s | open |
| W-03 | deprecation | `PK_GRANT/1` bodies | eng | after fleet migrates; flip `require_v2` | announced 4.3.0 |
| W-04 | deprecation | 16-hex legacy revocation ids | eng | with W-03 | announced 4.3.0 |
| W-05 | waiver | No LICENSE designated | owner | before any redistribution | open |
| W-06 | debt | Edge power/thermal not measured | platform | first far-edge pilot | open |
