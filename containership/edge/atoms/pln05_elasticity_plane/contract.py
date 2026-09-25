"""Binding contract for PLN-05 - Elasticity plane (``pk_core`` rendering of :mod:`spec`).

The elasticity plane decides how much capacity exists, including the scale-to-zero case that container orchestration handles badly. It converts observed demand into a capacity target with explicit hysteresis, so the estate does not oscillate.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

from . import spec
from .spec import ELEMENT_ID, ELEMENT_NAME  # noqa: F401  (re-exported)


def build() -> Contract:
    """Return the production contract for PLN-05."""
    return Contract(
        element=spec.ELEMENT_ID,
        name=spec.ELEMENT_NAME,
        responsibility=spec.RESPONSIBILITY,
        owns=list(spec.OWNS),
        not_owns=list(spec.NOT_OWNS),
        dependencies=[Dependency(*d) for d in spec.DEPENDENCIES],
        source_of_truth=spec.SOURCE_OF_TRUTH,
        assumptions=list(spec.ASSUMPTIONS),
        boundaries=dict(spec.BOUNDARIES),
        mandatory=list(spec.MANDATORY),
        optional=list(spec.OPTIONAL),
        non_goals=list(spec.NON_GOALS),
        interfaces=dict(spec.INTERFACES),
        threats=list(spec.THREATS),
        failure_modes=list(spec.FAILURE_MODES),
        slos=[Slo(*s) for s in spec.SLOS],
        signals=dict(spec.SIGNALS),
    )
