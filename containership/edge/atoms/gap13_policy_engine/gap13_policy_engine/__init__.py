"""GAP-13 - Policy engine."""

__version__ = "5.0.0"

# The evaluator itself is intentionally standalone and does not require pk_core.
from .errors import BundleRejected, ScopeEscalation, PolicyError  # noqa: E402
from .engine import BUNDLE_STALENESS_BOUND, PolicyEngine, Rule, CompiledIndex  # noqa: E402
from .config import EngineConfig, Limits, ConfigProvenance  # noqa: E402
from .bundle import PolicyBundle, parse_bundle  # noqa: E402
from .verify import (BundleVerifier, TrustStore, TrustedKey, StaticTrustSource, VerificationResult,  # noqa: E402
                     VerificationState)
from .service import PolicyService  # noqa: E402

# Conformance integration remains available when pk_core is installed.
try:
    from .component import COMPONENT, PolicyEngineComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as exc:
    if not (exc.name == "pk_core" or (exc.name or "").startswith("pk_core.")):
        raise
    COMPONENT = None
    PolicyEngineComponent = None
    ELEMENT_ID = "GAP-13"
    ELEMENT_NAME = "Policy engine"
    build_contract = None

__all__ = [
    "__version__", "BUNDLE_STALENESS_BOUND", "BundleRejected", "ScopeEscalation", "PolicyError",
    "PolicyEngine", "Rule", "CompiledIndex", "EngineConfig", "Limits", "ConfigProvenance",
    "PolicyBundle", "parse_bundle", "BundleVerifier", "TrustStore", "TrustedKey", "StaticTrustSource",
    "VerificationResult", "VerificationState", "PolicyService",
    "COMPONENT", "PolicyEngineComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract",
]
