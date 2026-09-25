"""Framework-independent source of truth for the PLN-05 contract and scope.

``contract.py`` renders this into a ``pk_core`` ``Contract``; README, the
scope declaration (``spec/pln05_scope.json``) and the traceability matrix are
checked against it by ``tools/check_repo.py`` so the documents cannot drift
from the code (MC-01).  Scope follows ADR-0001 (status: PROPOSED pending owner
approval): PLN-05 is a hysteretic capacity-target controller.
"""
from __future__ import annotations

ELEMENT_ID = "PLN-05"
ELEMENT_NAME = "Elasticity plane"
SCOPE_ADR = "docs/adr/ADR-0001-pln05-authoritative-scope.md"

RESPONSIBILITY = (
    "Own capacity targets per workload: convert observed demand into a bounded, hysteretic "
    "scale decision including scale-to-zero, and never emit a target outside the declared "
    "floor and ceiling."
)

#: responsibility -> OWN | ORCHESTRATE | CALL | OBSERVE | OUT_OF_SCOPE (ADR-0001 matrix)
RESPONSIBILITY_MATRIX = {
    "demand observation": "OBSERVE",
    "hysteresis": "OWN",
    "capacity target calculation": "OWN",
    "floor/ceiling enforcement": "OWN",
    "scale-to-zero decision": "OWN",
    "placement": "OUT_OF_SCOPE",
    "provisioning": "OUT_OF_SCOPE",
    "resource reassignment (HyperFlux-style)": "OUT_OF_SCOPE",
    "snapshot": "OUT_OF_SCOPE",
    "restore": "OUT_OF_SCOPE",
    "microfunction lifecycle (Dandelion-style)": "OUT_OF_SCOPE",
    "failover of controller ownership": "OWN",
    "execution ownership": "OUT_OF_SCOPE",
}

OWNS = [
    "Capacity targets per workload",
    "Scale-up and scale-down hysteresis",
    "Scale-to-zero and cold-start admission",
    "Floor and ceiling enforcement",
    "Oscillation suppression",
]
NOT_OWNS = [
    "Placement of new capacity",
    "Node provisioning",
    "Workload isolation",
    "The demand signal itself",
    "Cost accounting",
]
DEPENDENCIES = [
    ("GAP-09 Unified observability", "upstream", "Supplies the demand signal"),
    ("PLN-01 Intent plane", "upstream", "Supplies declared floor, ceiling, and target utilisation"),
    ("SCH-01 Workload classification and placement", "downstream", "Places the capacity this plane asks for"),
    ("GAP-10 Power/thermal-aware scheduling", "peer", "May cap the ceiling below the declared value"),
]
SOURCE_OF_TRUTH = "The declared floor/ceiling from the intent plane; observed demand is input, never authority."
SOURCE_PRECEDENCE = ["ADR (accepted)", "spec.py / spec/*.json", "schemas/*.json", "code", "tests",
                     "README.md", "CHECKLIST.json requirement prose"]
ASSUMPTIONS = [
    "The demand signal is delayed and noisy",
    "Cold start is expensive enough that scale-to-zero needs an explicit grace period",
    "A ceiling may be lowered externally by power or thermal pressure",
]
BOUNDARIES = {
    "tenant": "capacity targets and ceilings are per tenant",
    "environment": "hysteresis parameters differ per environment",
    "site": "a site's ceiling may be lower than the environment ceiling",
    "workload": "each workload has an independent controller instance",
}
MANDATORY = [
    "Emit a capacity target within the declared floor and ceiling at all times",
    "Apply separate scale-up and scale-down thresholds",
    "Hold a scale-down decision for the declared grace period before acting",
    "Support scale-to-zero when the floor is zero",
    "Suppress oscillation between adjacent targets",
]
OPTIONAL = ["Predictive pre-scaling", "Cost-aware ceiling selection", "Burst credit accounting"]
NON_GOALS = [
    "Placing or provisioning capacity",
    "Deciding node count",
    "Guaranteeing cold-start latency",
    "Overriding an externally lowered ceiling",
]
INTERFACES = {
    "observe": "PK_DEMAND/1 - demand samples per workload",
    "target": "PK_CAPACITY_TARGET/1 - emitted capacity target with the reason",
    "limits": "PK_CAPACITY_LIMITS/1 - declared floor, ceiling, and hysteresis parameters",
}
THREATS = [
    "Forged demand signal driving a tenant's bill or starving a peer",
    "Ceiling bypass through a crafted limits declaration",
    "Oscillation induced deliberately to churn placement",
    "Scale-to-zero used to suppress a security-relevant workload",
]
FAILURE_MODES = [
    "Demand signal stops arriving",
    "Ceiling lowered below the current target",
    "Cold start exceeds the grace period",
    "Floor and ceiling declared inconsistently",
]
SLOS = [
    ("target bounds", "zero targets outside the declared floor/ceiling", "no budget"),
    ("reaction time", "p95 scale-up decision within two demand samples of threshold breach", "5% may take a third sample"),
    ("stability", "no more than one direction change per workload per grace period", "1% of workloads may exceed under demand step changes"),
]
SIGNALS = {
    "capacity_target": "gauge per workload with the emitting reason",
    "scale_decisions": "counter by direction and reason",
    "suppressed_oscillations": "counter of decisions withheld by hysteresis",
    "demand_staleness_seconds": "gauge of age of the newest demand sample",
}
