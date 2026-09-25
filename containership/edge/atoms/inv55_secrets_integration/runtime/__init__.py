"""Standalone production runtime for INV-55 (stdlib only).

Layers, outermost first::

    SecretsService  (service.py)   public boundary: PK_SECRET_RESOLVE/1, ROTATE/1, SCOPE/1
      -> negotiation   (negotiation.py)  protocol-version negotiation
      -> identity      (identity.py)     workload authentication (signed tokens)
      -> quarantine    (quarantine.py)   operator freeze / disable
      -> admission     (resilience.py)   quota, bulkhead, circuit breaker
      -> authz         (authz.py)        deny-by-default capability policy
      -> cache         (cache.py)        lease cache + disconnected policy
      -> provider      (provider.py / vault.py)  secret storage adapter
    audit (audit.py) / telemetry (telemetry.py) / health (health.py) observe every layer.
"""
RUNTIME_VERSION = "4.3.0"
PROTOCOLS = ("PK_SECRET_RESOLVE/1", "PK_SECRET_ROTATE/1", "PK_SECRET_SCOPE/1")
