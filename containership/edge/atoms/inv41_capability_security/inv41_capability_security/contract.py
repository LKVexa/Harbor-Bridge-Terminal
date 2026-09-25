"""Binding contract for INV-41 - Capability security.

Capability security at the software level is the discipline the whole estate leans on: there is no ambient authority, a component can only do what it was handed, and handing something on can only narrow it. This element is where that rule is enforced for in-process references rather than for network grants.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-41"
ELEMENT_NAME = "Capability security"


def build() -> Contract:
    """Return the production contract for INV-41."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own ambient-authority elimination inside a process: every resource is reached through an unforgeable reference that was explicitly passed in, delegation may only attenuate, and there is no global namespace from which authority can be recovered."
        ),
        owns=[
            "Unforgeable resource references",
            "Explicit delegation and attenuation",
            "Absence of a global or ambient namespace",
            "Revocation through membranes",
            "Refusal of authority recovery by name"
        ],
        not_owns=[
            "Hostile-code isolation inside the same Python interpreter",
            "Hardware capability enforcement",
            "Network capability grants",
            "Policy authorship",
            "The language runtime",
            "Placement"
        ],
        dependencies=[
            Dependency("PLN-07 Security plane", "upstream", "Issues the estate-level grants these in-process references derive from"),
            Dependency("INV-42 Capability descriptors", "downstream", "Serializes these references for transfer"),
            Dependency("INV-30 Capability hardware sandbox", "peer", "Enforces the same discipline in hardware where available"),
            Dependency("INV-44 Wasm hardening system", "peer", "Applies this model to Wasm imports")
        ],
        source_of_truth=(
            "A sealed reference minted by an explicitly held Authority domain: possession is authority, "
            "and no lookup by resource name can recover authority that was not passed in."
        ),
        assumptions=[
            "Any resource-returning global registry becomes an ambient-authority escape hatch",
            "Pure Python object controls are not a hostile same-interpreter sandbox; adversarial code requires a runtime/process/VM/hardware boundary",
            "A component may be compromised and will use everything it holds",
            "Revocation must work without finding every copy of a reference"
        ],
        boundaries={
            "tenant": "references never cross a tenant boundary",
            "environment": "attenuation policy differs per environment",
            "site": "references are process-local and do not travel as such",
            "workload": "each component starts with only what its constructor received"
        },
        mandatory=[
            "Reject direct reference construction and authenticate every minted reference",
            "Bind holders and references to an explicit authority domain",
            "Provide no lookup that returns a reference by name alone",
            "Permit delegation only with equal or narrower authority",
            "Support revocation without tracking every holder",
            "Start every component with an explicitly supplied reference set"
        ],
        optional=[
            "Reference-use auditing",
            "Automatic membrane wrapping at boundaries"
        ],
        non_goals=[
            "Hardware enforcement",
            "Network grant issuance",
            "Global service discovery",
            "Recovering authority a component was not given",
            "Treating Python object encapsulation as isolation from hostile code in the same interpreter"
        ],
        interfaces={
            "grant": "Authority.grant -> sealed PK_REFERENCE/1 capability",
            "bind_holder": "Authority.bind_holder -> immutable authority-domain holder",
            "invoke": "Holder.use / Reference.invoke -> PK_REFERENCE/1 permit result",
            "attenuate": "Holder.delegate / Reference.attenuate -> narrower reference",
            "membrane": "Membrane.wrap/revoke -> revocable wrapper and PK_MEMBRANE/1 result"
        },
        threats=[
            "A global registry used to recover unheld authority",
            "Reference forgery through direct construction, mutation, or cross-authority injection",
            "Same-interpreter hostile code bypassing Python-level encapsulation",
            "Delegation widening a held reference",
            "A revoked reference still usable through a copy"
        ],
        failure_modes=[
            "Lookup attempted for an unheld reference",
            "Attenuation requests more than held",
            "Use of a revoked reference",
            "Component started with no references at all",
            "Reference introduced from a different authority domain"
        ],
        slos=[
            Slo("no ambient authority", "zero resources reachable without a passed reference", "no budget"),
            Slo("attenuation", "zero delegations widening authority", "no budget"),
            Slo("revocation", "100% of references behind a revoked membrane become unusable at once", "no budget")
        ],
        signals={
            "references_granted": "counter by resource and operation set",
            "attenuations": "counter by narrowing",
            "forgery_attempts": "counter of lookups for unheld references",
            "membrane_revocations": "counter with the reference count behind each"
        },
    )
