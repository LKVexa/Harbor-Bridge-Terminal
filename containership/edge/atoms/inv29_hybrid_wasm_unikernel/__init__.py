"""INV-29 - Hybrid Wasm/unikernel (master-applied component).

The security-critical core (model, interfaces, records, admission, lifecycle,
telemetry, evidence, deps) is dependency-free.  ``COMPONENT`` and the contract
need the external ``pk_core`` runtime and are loaded lazily, behind a startup
compatibility assertion (see ``deps.require_pk_core``).
"""

__version__ = "4.3.0"
PK_CORE_CONTRACT_API = "pk_core.contract/1"

from .model import HostImage, ImportUnsatisfied, LayerMissing, WasmModule, compose, verify
from .admission import (AdmissionPolicy, AdmissionRefused, AdmissionRequest, Admitter, Keyring,
                        ReplayGuard, error_code, verify_record)

_LAZY = {"COMPONENT", "HybridWasmUnikernelComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"}


def __getattr__(name):
    if name in _LAZY:
        from .deps import require_pk_core
        require_pk_core()
        from . import component, contract
        return {"COMPONENT": component.COMPONENT,
                "HybridWasmUnikernelComponent": component.HybridWasmUnikernelComponent,
                "ELEMENT_ID": contract.ELEMENT_ID, "ELEMENT_NAME": contract.ELEMENT_NAME,
                "build_contract": contract.build}[name]
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "HybridWasmUnikernelComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract", "HostImage", "WasmModule", "LayerMissing", "ImportUnsatisfied", "compose",
           "verify", "AdmissionPolicy", "AdmissionRefused", "AdmissionRequest", "Admitter", "Keyring",
           "ReplayGuard", "error_code", "verify_record"]
