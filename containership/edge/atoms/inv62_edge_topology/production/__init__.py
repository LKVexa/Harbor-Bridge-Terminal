"""Production control-plane layer for INV-62 Edge topology (v4.3.0).

Every module is stdlib-only.  See ``docs/ARCHITECTURE.md`` for the layering:

    wire (PK_TOPO_* codecs, limits, negotiation)
      -> service (authn, authz, admission, deadlines, idempotency, tenancy)
         -> policy / election / health / degraded modes
            -> topology (validated graph engine)
    config (schema, overlays, provenance, generations, rollback)
    audit (hash-chained), telemetry (metrics/logs/traces), persistence (WAL+snapshot)
"""
