# Versioning and compatibility

The package uses semantic versioning for the Python reference implementation. `PK_MSG_ENVELOPE/1`, `PK_MSG_PUBLISH/1`, `PK_MSG_SUBSCRIBE/1`, `PK_MSG_CONFIG/1`, `PK_MSG_DECISION/1` and `PK_MSG_HEALTH/1` are independently versioned interface identifiers with JSON Schemas under `schemas/`.

Within interface major version `/1`, additions must be backward compatible: existing mandatory fields keep their meaning, callers may ignore newly added optional fields, and stable error codes are not repurposed. Removing or changing the meaning/type of a mandatory field, changing authorization semantics, or changing subscriber-delivery semantics requires a new interface major version. Peer negotiation: `schemas.negotiate`.

The local package supports Python 3.10 and newer per `pyproject.toml`. The platform compatibility matrix is `docs/COMPATIBILITY.md`; support windows and end-of-life are in `docs/SUPPORT_POLICY.md`.
