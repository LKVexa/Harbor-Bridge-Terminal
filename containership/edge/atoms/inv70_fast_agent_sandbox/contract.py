"""Binding contract for INV-70 - Fast agent sandbox.

The fast agent sandbox executes bounded guest bytecode with a fuel counter, explicit stack/value/logical-memory ceilings, strict instruction validation, and no host access except through explicitly granted capabilities. Host callback implementations are trusted and outside the guest isolation boundary.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-70"
ELEMENT_NAME = "Fast agent sandbox"


def build() -> Contract:
    """Return the production contract for INV-70."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the lightweight sandbox: a bounded interpreter, fuel metering, memory ceilings, capability-gated host calls and deterministic termination."
        ),
        owns=[
            "The bounded stack interpreter",
            "Fuel metering",
            "Stack, value and logical guest-memory ceilings",
            "Strict bytecode validation",
            "Capability-gated host calls",
            "Deterministic termination with a reason",
            "The governed PK_FASTBOX_RUN handler (service.Sandbox): caller authentication, admission, "
            "lifecycle, process isolation with wall-clock pre-emption, audit, telemetry and explain"
        ],
        not_owns=[
            "High-risk arbitrary code",
            "Model execution",
            "Tool business logic",
            "Network access by default",
            "Persistent storage"
        ],
        dependencies=[
            Dependency("INV-69 Agentic workload layer", "upstream", "Routes low-risk tool logic here"),
            Dependency("INV-09 Portable compute ISA", "upstream", "The deterministic profile this interpreter follows"),
            Dependency("INV-71 Heavy agent sandbox", "peer", "Takes what this sandbox is too small for"),
            Dependency("GAP-09 Unified observability", "downstream", "Reports fuel and termination reasons")
        ],
        source_of_truth="The fuel and memory counters; a program's own claim to be finished is irrelevant.",
        assumptions=[
            "Every peer, network path and store can fail independently",
            "Callers are untrusted until their identity is established",
            "Behaviour must be identical whether a dependency is local or remote",
            "Nodes provide OS process isolation and the multiprocessing spawn start method",
            "The trust store, time source and audit sink may fail; the sandbox then fails closed (HALT)",
            "The control plane may be partitioned; the sandbox serves on last-known-good config and freezes changes",
            "No persistent storage is used; the audit sink is an append-only stream owned by the embedder"
        ],
        boundaries={
            "tenant": "state and traffic are partitioned per tenant and never shared",
            "environment": "limits and endpoints differ per environment",
            "site": "each site runs its own instance; nothing assumes a global singleton",
            "workload": "budgets and quotas are per workload"
        },
        mandatory=[
            "Meter every instruction against fuel",
            "Enforce stack, value, program and logical guest-memory ceilings",
            "Validate bytecode shape and operand types before execution",
            "Refuse host calls without a capability",
            "Terminate deterministically with a reason",
            "Start every run from a clean state"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running arbitrary native code",
            "Granting network by default",
            "Persisting state"
        ],
        interfaces={
            "run": "PK_FASTBOX_RUN/1,2 - signed caller token, program or signed module, caps, fuel, idempotency key",
            "result": "PK_FASTBOX_RESULT/1,2 - value or termination reason with stable FB-* reason code and lifecycle state",
            "hostcall": "PK_FASTBOX_HOSTCALL/1 - a capability-gated call"
        },
        threats=[
            "Infinite loop pinning a core",
            "Memory bomb",
            "Escape to host through an ungranted call"
        ],
        failure_modes=[
            "Out of fuel",
            "Out of memory",
            "Capability denied",
            "Invalid instruction",
            "Invalid value or oversized value",
            "Stack underflow",
            "Unbound or invalid capability",
            "Host callback error",
            "Host call timeout / wall-clock deadline exceeded",
            "Unauthenticated, expired, replayed or wrongly scoped token",
            "Artifact unsigned, tampered, unapproved or missing provenance/SBOM",
            "Overload shed, circuit open, drain, halt",
            "Worker crash or Wasm backend unavailable (fail closed)"
        ],
        slos=[
            Slo("termination", "guest bytecode terminates within its fuel; host callbacks require an embedding-layer deadline", "no budget"),
            Slo("containment", "zero host calls without capability", "no budget"),
            Slo("startup", "in-process reference VM: p99 run start under 50us; process-isolated run: p50 under 5ms with a warm worker (perf/baseline.json)", "1% may exceed"),
            Slo("deadline", "every run terminates within wall_clock_ms plus kill latency, including hung host callbacks", "no budget")
        ],
        signals={
            "runs": "counter",
            "terminations": "counter by reason",
            "fuel_used": "histogram",
            "latency_us": "histogram by phase",
            "idempotent_replays": "counter",
            "audit": "hash-chained run.finished / config.activated / capability.registered events"
        },
    )
