# Versioning and compatibility policy (INV55-VER-001, DRAFT)

* **Package** follows SemVer. 4.3.0 is additive over 4.2.0: the reference API (`SecretBroker`, `_SecretValue`, exceptions) is unchanged and re-exported from `component.py`; `reference.py` is the new import-safe home.
* **Wire protocols** are versioned per operation: `PK_SECRET_RESOLVE/n`, `PK_SECRET_ROTATE/n`, `PK_SECRET_SCOPE/n`. A server MUST support the current and previous major for ≥ 2 minor releases after a new major ships (deprecation window), and lists deprecated versions in `runtime/negotiation.py::DEPRECATED`.
* **Negotiation:** the client offers a list; the server picks the highest mutually supported version or fails `INV55-E-UNSUPPORTED-VERSION` (never silently downgrades below the offered set).
* **Tolerant reader:** unknown fields are accepted only inside `ext`; unknown top-level fields are rejected so a newer client cannot smuggle semantics an older server would ignore.
* **Downgrade:** rolling back the runtime to 4.2.x removes the wire boundary entirely (4.2.x has none); rolling back within 4.3.x is config-compatible (`inv55-config/1`).
* **Migration:** configuration schema changes bump `inv55-config/<n>`; the controller refuses unknown schema ids.
