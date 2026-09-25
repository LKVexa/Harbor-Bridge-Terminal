"""Binding contract for INV-28 - Unikernel implementations.

Unikernel implementations are the concrete toolchains -- MirageOS, Unikraft, OSv and the rest -- and they are not interchangeable. Each supports a different language, a different device set and a different maturity of security response. This element keeps that register honest instead of letting 'unikernel' stand in for a single thing.
"""
from __future__ import annotations

from . import ensure_pk_core

ensure_pk_core()

from pk_core.contract import Contract, Dependency, Slo  # noqa: E402

ELEMENT_ID = "INV-28"
ELEMENT_NAME = "Unikernel implementations"


def build() -> Contract:
    """Return the production contract for INV-28."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the register of supported unikernel toolchains: record each one's language support, maturity, security-response posture and known limitations, and refuse to select a toolchain for a workload whose requirements it does not actually meet."
        ),
        owns=[
            "The toolchain register and its attributes",
            "Language and runtime support per toolchain",
            "Maturity and security-response classification",
            "Toolchain selection for a workload",
            "Refusal when no registered toolchain fits"
        ],
        not_owns=[
            "Building images",
            "Seal verification",
            "The hypervisor",
            "Upstream toolchain development",
            "Placement"
        ],
        dependencies=[
            Dependency("GAP-15 Runtime compatibility certification", "upstream", "Certifies which toolchain/profile pairs are actually tested"),
            Dependency("INV-27 Unikernel execution", "downstream", "Executes images these toolchains produce"),
            Dependency("GAP-08 OTA lifecycle/rollback", "peer", "Rolls out toolchain version changes", required=False)
        ],
        source_of_truth="The signed, revisioned register snapshot (PK_TOOLCHAIN_REGISTRY/1) with each entry's maturity, review provenance, lifecycle and integrity identity, evaluated under the versioned selection policy (PK_TOOLCHAIN_POLICY/1) and GAP-15 certificates; an unregistered toolchain is not selectable.",
        assumptions=[
            "Toolchains differ sharply in language support and maturity",
            "An experimental toolchain may be right for one workload and wrong for another",
            "Security-response posture matters more than feature count in production"
        ],
        boundaries={
            "tenant": "toolchain choice is not tenant-visible policy",
            "environment": "production admits only mature toolchains; a beta toolchain only under an approved, unexpired, scoped waiver; experimental never (policy inv28-default r1, ADR-0001)",
            "site": "a site supports a subset of architectures, hypervisors and providers; selection takes SiteCapabilities and never picks outside them",
            "workload": "a workload declares language, runtime, devices, features and optional hypervisor/provider/ABI needs (PK_TOOLCHAIN_SELECTION_REQUEST/1), never a toolchain"
        },
        mandatory=[
            "Register each toolchain with language support, maturity and security posture",
            "Select a toolchain from declared workload requirements, not by name",
            "Refuse selection when no registered toolchain meets the requirements",
            "Admit only mature toolchains in production (beta only under an approved waiver; experimental never)",
            "Select in production only toolchains with a valid GAP-15 certificate for the exact artifact digest, architecture and profile",
            "Bind every selection to an immutable toolchain identity that INV-27 verifies before build",
            "Record which toolchain was selected and why"
        ],
        optional=[
            "Toolchain benchmark results",
            "Automated upstream CVE tracking",
            "Multi-toolchain build comparison"
        ],
        non_goals=[
            "Developing toolchains upstream",
            "Building images",
            "Verifying image seals",
            "Treating all unikernels as equivalent"
        ],
        interfaces={
            "register": "PK_TOOLCHAIN/2 - a supported unikernel toolchain release and its attributes (schemas/PK_TOOLCHAIN-2.schema.json; v1 shape deprecated, see docs/MIGRATION.md)",
            "select": "PK_TOOLCHAIN_SELECTION/2 | PK_TOOLCHAIN_REFUSAL/1 - the chosen toolchain, the reason and a signed binding ticket, or a structured refusal (schemas/PK_TOOLCHAIN_SELECTION-2.schema.json, schemas/PK_TOOLCHAIN_REFUSAL-1.schema.json)",
            "request": "PK_TOOLCHAIN_SELECTION_REQUEST/1 - validated workload requirements (schemas/PK_TOOLCHAIN_SELECTION_REQUEST-1.schema.json)",
            "ticket": "PK_TOOLCHAIN_TICKET/1 - signed selection-to-build binding verified by INV-27 (schemas/PK_TOOLCHAIN_TICKET-1.schema.json)"
        },
        threats=[
            "An experimental toolchain reaching production",
            "A workload silently downgraded to an unsupported language runtime",
            "An unmaintained toolchain with no security response staying in the register",
            "Toolchain substitution between selection and build"
        ],
        failure_modes=[
            "No toolchain meets the workload's requirements",
            "Only experimental toolchains match in a production environment",
            "Toolchain's security review is stale",
            "Architecture unsupported by every matching toolchain"
        ],
        slos=[
            Slo("selection soundness", "zero selections of a toolchain missing a required capability", "no budget"),
            Slo("production maturity", "zero below-mature toolchains selected in production without an approved, unexpired waiver", "no budget"),
            Slo("review freshness", "100% of registered toolchains reviewed within the declared interval", "no budget")
        ],
        signals={
            "toolchains_registered": "gauge by maturity",
            "selections": "counter by toolchain and environment",
            "selection_refusals": "counter by unmet requirement",
            "stale_reviews": "gauge of toolchains past their review interval"
        },
    )
