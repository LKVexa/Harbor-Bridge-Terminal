"""INV-67 v4.3 Kubernetes integration plane.

Stdlib-only runtime around the v4.2 pure translator: CRD contract, reconciler,
Kubernetes client abstraction, downstream adapter, lifecycle, security, resilience,
observability and evidence. Nothing here imports ``pk_core``.
"""
PLANE_VERSION = "4.3.0"
