"""Binding contract for GAP-11 - Accelerator scheduling.

Accelerator scheduling treats a GPU, NPU, FPGA, or other declared accelerator as an exclusive, attestable resource rather than a divisible number. A device is either wholly assigned, partitioned into declared slices, or not available -- and a device is scrubbed between tenants before it is handed on.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-11"
ELEMENT_NAME = "Accelerator scheduling"


def build() -> Contract:
    """Return the production contract for GAP-11."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own accelerator allocation: assign whole devices or declared partitions exclusively, never oversubscribe across tenants, and require a completed scrub before a device moves between tenants."
        ),
        owns=[
            "Accelerator inventory and partition topology",
            "Exclusive allocation and release",
            "Cross-tenant scrub enforcement",
            "Refusal to oversubscribe",
            "Accelerator capability matching (memory, generation, features)"
        ],
        not_owns=[
            "Device drivers and firmware",
            "Thermal ceilings",
            "Workload placement",
            "Hardware capability probing",
            "Model or kernel execution"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports which accelerators actually exist"),
            Dependency("GAP-10 Power/thermal-aware scheduling", "upstream", "May reduce how many devices may run at once"),
            Dependency("GAP-09 Unified observability", "peer", "Consumes allocation, refusal, scrub and quarantine telemetry"),
            Dependency("GAP-06 Device identity and attestation", "peer", "Binds discovered accelerator identity/capability to an attested node"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Places only where an accelerator can be allocated"),
            Dependency("INV-72 Accelerated workload requirement", "downstream", "Declares the requirement this element satisfies")
        ],
        source_of_truth=(
            "The lease table plus the physical-device security-tenant epoch: capacity is available only "
            "when no conflicting lease exists, and cross-tenant reuse requires a completed scrub."
        ),
        assumptions=[
            "Accelerators are not safely time-shared between tenants",
            "A scrub takes measurable time and may fail",
            "Partitions are declared by the device, not invented by the scheduler"
        ],
        boundaries={
            "tenant": "no device or partition is ever shared between tenants concurrently",
            "environment": "accelerator pools are per environment",
            "site": "devices do not migrate between sites",
            "workload": "allocation is per workload instance and released on exit"
        },
        mandatory=[
            "Allocate whole devices or declared partitions exclusively",
            "Refuse allocation when no free device matches the requirement",
            "Require a completed scrub before a device serves a different tenant",
            "Release allocations on workload exit using an unambiguous lease identity",
            "Match memory, generation and feature requirements before allocating",
            "Attest partition capacity independently of whole-device capacity",
            "Never co-locate different tenants on one physical accelerator between scrubs"
        ],
        optional=[
            "Time-sliced sharing within a single tenant",
            "Preemption of lower-class workloads",
            "Topology-aware multi-device allocation"
        ],
        non_goals=[
            "Executing kernels",
            "Managing drivers",
            "Sharing a device across tenants",
            "Inventing partitions a device does not declare"
        ],
        interfaces={
            "inventory": "PK_ACCELERATOR_INVENTORY/1 - devices, partitions and their features",
            "allocate": "PK_ACCELERATOR_ALLOCATION/1 - request and lease an accelerator",
            "release": "PK_ACCELERATOR_RELEASE/1 - release exactly one active lease",
            "scrub": "PK_SCRUB/1 - scrub state and completion evidence"
        },
        threats=[
            "Residual tenant data read from an unscrubbed device",
            "Oversubscription giving two tenants the same device",
            "A workload claiming a feature it does not need to widen its options",
            "Scrub skipping under load pressure",
            "Stale or ambiguous release requests freeing the wrong partition",
            "Concurrent allocation races assigning the same partition twice"
        ],
        failure_modes=[
            "No free device matches the requirement",
            "Scrub fails or times out",
            "Device disappears between inventory and allocation",
            "Partition requested that the device does not declare",
            "Partition capacity is unknown or smaller than the requested memory",
            "Ambiguous release while multiple partition leases are active"
        ],
        slos=[
            Slo("exclusivity", "zero devices concurrently allocated to two tenants", "no budget"),
            Slo("scrub", "zero cross-tenant handovers without completed scrub evidence", "no budget"),
            Slo("allocation latency", "p99 allocation decision under 10ms", "1% may exceed")
        ],
        signals={
            "accelerators_allocated": "gauge by device and partition; tenant only in access-controlled detail",
            "allocation_refusals": "counter by unmet requirement",
            "scrub_duration_seconds": "histogram per device",
            "scrub_failures": "counter of devices quarantined for a failed scrub",
            "active_accelerator_leases": "gauge by device and partition",
            "allocation_decision_reason": "structured decision/refusal reason code"
        },
    )
