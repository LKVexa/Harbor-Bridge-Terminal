# INV-32 conformance fixtures (v4.3.0)

Consumer-runnable, language-neutral vectors.  A conforming implementation MUST:

* accept every `valid` document and reject every `invalid` document in `request_v2_vectors.json`
  when validated against `../schemas/resource_adjustment_request.v2.schema.json`;
* reject every raw payload in `decoder_negative_vectors.json` at the decoder (before schema validation);
  entries with `code` must yield that stable error code;
* reproduce `sha256` in `audit_canonical_v1.json` from `event_without_hash` using the canonicalisation
  JSON / sorted keys / separators `(",", ":")` / UTF-8 / no ASCII escaping.

`legacy_v1_revert_record.json` is the only accepted `PK_RESOURCE_ADJUSTMENT/1` shape (model-level revert,
retirement per COMPATIBILITY.md).

Run the reference check: `python -m inv32_elastic_virtualization.conformance_check`.
