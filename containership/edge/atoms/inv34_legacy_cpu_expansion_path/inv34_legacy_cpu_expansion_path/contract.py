"""Binding contract for INV-34 - Legacy CPU expansion path.

INV-34 is the conventional-VM CPU scaling path defined by the source checklist.
Its guest-visible mechanism is ACPI CPU hot-plug.  This package owns the policy,
validation, desired/observed state model, and adapter contract; a concrete
hypervisor driver remains an integration dependency.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-34"
ELEMENT_NAME = "Legacy CPU expansion path"


def build() -> Contract:
    """Return the production contract for INV-34."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the conventional-VM CPU expansion control path: validate monotonic vCPU growth requests, "
            "enforce configured and host capacity ceilings, model accepted versus observed CPU counts, and "
            "drive expansion through a versioned ACPI CPU hot-plug adapter boundary without claiming success "
            "until the backend/guest observation converges."
        ),
        owns=[
            "Validation of CPU expansion requests",
            "Monotonic desired-vCPU state and generation control",
            "Guest and host CPU expansion ceilings",
            "ACPI CPU hot-plug capability gating",
            "Accepted-versus-observed convergence semantics",
            "Machine-readable CPU expansion result and status contracts",
        ],
        not_owns=[
            "Physical CPU procurement or host firmware",
            "Hypervisor implementation internals",
            "Guest-kernel CPU hot-plug implementation",
            "CPU feature-level compatibility policy",
            "Workload placement and scheduler policy",
            "CPU hot-unplug",
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports host CPU capacity and hot-plug capability"),
            Dependency("GAP-15 Runtime compatibility certification", "upstream", "Certifies supported hypervisor/guest combinations"),
            Dependency("Hypervisor CPU hot-plug adapter", "downstream", "Translates accepted targets into hypervisor/ACPI operations"),
            Dependency("Guest CPU online observation", "downstream", "Confirms CPUs actually became available to the guest"),
        ],
        source_of_truth=(
            "The controller's versioned desired state plus independently observed guest/hypervisor online-vCPU count; "
            "an accepted request is not considered converged until observed_vcpus equals desired_vcpus."
        ),
        assumptions=[
            "The VM/hypervisor exposes ACPI CPU hot-plug for expansion requests",
            "The guest operating system supports CPU hot-add and can report online CPU count",
            "CPU hot-unplug is outside this legacy path",
            "Host-capacity discovery is refreshed by an upstream capability source",
        ],
        boundaries={
            "tenant": "tenant requests are policy input; authorization is enforced by the calling control plane",
            "environment": "environment policy may lower the configured VM maximum or disable expansion",
            "site": "site capacity constrains the target but does not change request semantics",
            "workload": "workload placement is external; this component acts on a specific VM identifier",
        },
        mandatory=[
            "Use ACPI CPU hot-plug for conventional-VM CPU expansion",
            "Require both hypervisor and guest hot-plug support before accepting growth",
            "Reject CPU hot-unplug through this path",
            "Reject targets above the configured VM maximum or discovered host capacity",
            "Use generation checks to reject stale control-plane updates",
            "Keep accepted desired count separate from observed online count",
            "Provide bounded idempotency handling for repeated expansion requests",
        ],
        optional=[
            "Hypervisor-specific batching of multiple CPU additions",
            "Predictive pre-expansion based on workload demand",
            "Automatic retries in an external reconciler after retryable capacity/dependency failures",
        ],
        non_goals=[
            "CPU feature emulation",
            "CPU hot-unplug",
            "Selecting hardware",
            "Guest scheduler tuning",
            "Pretending an accepted request has completed before observation",
        ],
        interfaces={
            "request": "PK_CPU_EXPANSION_REQUEST/1 - idempotent desired-vCPU expansion request",
            "result": "PK_CPU_EXPANSION_RESULT/1 - accepted/noop result with generation",
            "status": "PK_CPU_EXPANSION_STATUS/1 - desired/observed convergence state",
            "backend": "ACPI CPU hot-plug adapter boundary - hypervisor-specific execution and guest observation",
        },
        threats=[
            "Unauthorized callers expanding a VM to consume host capacity",
            "Stale controllers overwriting newer desired state",
            "Request replay or idempotency-key reuse with changed parameters",
            "False completion claims before the guest on-lines added CPUs",
            "Resource exhaustion through unbounded target or replay-cache inputs",
        ],
        failure_modes=[
            "Hypervisor or guest does not support ACPI CPU hot-plug",
            "Target exceeds VM maximum or current host capacity",
            "Guest accepts the hot-plug notification but does not online every CPU",
            "Controller generation is stale",
            "Host capacity changes while an expansion is pending",
        ],
        slos=[
            Slo("request safety", "zero accepted requests above configured or discovered capacity", "no budget"),
            Slo("completion honesty", "zero requests reported converged before observed count reaches desired count", "no budget"),
            Slo("stale-write safety", "zero state changes accepted from a mismatched expected generation", "no budget"),
        ],
        signals={
            "cpu_expansion_requests": "counter by accepted/noop/rejected outcome and error code",
            "cpu_expansion_pending_vcpus": "gauge of desired minus observed vCPUs per VM",
            "cpu_expansion_generation": "gauge of current state generation per VM",
            "cpu_expansion_convergence_seconds": "histogram from accepted target to observed convergence",
        },
    )
