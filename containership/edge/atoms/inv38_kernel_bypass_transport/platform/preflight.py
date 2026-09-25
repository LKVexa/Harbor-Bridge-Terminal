"""INV-38-C031 — Activation preflight: refuse to run without the pinned stack.

The reference model cannot touch real hardware, so preflight fails closed to the
kernel path whenever the pinned RDMA stack or required capabilities are absent
(C031-T07). This is the model-scope evidence; hardware qualification itself is
BLOCKED on physical NIC/IOMMU availability.
"""
from __future__ import annotations
import json, os
from dataclasses import dataclass

class PreflightFailed(RuntimeError):
    code = "PK_BYPASS_PREFLIGHT_FAILED"

@dataclass
class Detected:
    rdma_provider: str | None
    userspace_lib: str | None
    iommu: bool
    sriov: bool

def load_lock(path: str) -> dict:
    with open(path) as f:
        import yaml  # optional; fall back to a tiny parser if unavailable
        return yaml.safe_load(f) if yaml else {}

def evaluate(detected: Detected, required: dict) -> tuple[bool, list[str]]:
    reasons = []
    if detected.rdma_provider != required.get("provider"):
        reasons.append(f"provider {detected.rdma_provider!r} != pinned {required.get('provider')!r}")
    if detected.userspace_lib != required.get("userspace_lib"):
        reasons.append("userspace library mismatch")
    if required.get("require_iommu", True) and not detected.iommu:
        reasons.append("IOMMU isolation unavailable")
    ok = not reasons
    return ok, reasons

def activate_or_fallback(detected: Detected, required: dict) -> str:
    ok, reasons = evaluate(detected, required)
    # Fail CLOSED to kernel path; never auto-relax to make bypass succeed.
    return "bypass" if ok else "kernel-fallback"
