# Exception / waiver / technical-debt / deprecation register  (component 98)

| ID | Item | Type | Owner | Expiry | Compensating control | Status |
|---|---|---|---|---|---|---|
| TD-01 | Provider adapters certified only against fake clients | debt | accountable owner | before first production release | conformance on fakes; production config refuses nothing yet → must not advertise support | OPEN |
| TD-02 | HA transport is in-process only | debt | accountable owner | — | use provider-native replication in production | OPEN |
| TD-03 | Online at-rest key rotation missing | debt | accountable owner | — | offline re-encrypt via backup/restore | OPEN |
| TD-04 | No backup owner / on-call | governance gap | accountable owner | — | none | OPEN |
| TD-05 | pk_core not supplied; conformance gate skipped | external | accountable owner | — | local unittest suite | OPEN |
| TD-06 | No LICENSE decided | legal | accountable owner | before redistribution | `LICENSE-PENDING.md`, not published | OPEN |
| DEP-01 | none | deprecation | — | — | — | — |
No waiver is approved; every row above keeps its component non-PASS.
