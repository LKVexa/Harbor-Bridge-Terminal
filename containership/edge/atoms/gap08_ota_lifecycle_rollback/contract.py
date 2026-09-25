"""Binding contract for GAP-08 - OTA lifecycle/rollback.

OTA lifecycle and rollback is how an edge estate survives its own updates. Every rollout is staged, every stage has a health gate, and the rollback target is pinned before the first node is touched -- so a bad update stops at the canary instead of reaching the fleet.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

from .contract_data import ELEMENT_ID, ELEMENT_NAME


def build() -> Contract:
    """Return the production contract for GAP-08."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the over-the-air update lifecycle: stage a signed bundle across waves, gate each wave on health, and roll back to the pinned previous version the moment a gate fails."
        ),
        owns=[
            "Rollout waves and their ordering",
            "Per-wave health-gate orchestration",
            "The pinned rollback target",
            "Automatic and operator-triggered rollback orchestration",
            "Exact-bundle admission of an upstream verification result",
            "Deferred-node bookkeeping and gated catch-up",
            "Local rollout state snapshot and integrity validation",
            "Explicit quarantine state for rollback failures",
            "Controller ownership: leases and fencing tokens for rollouts",
            "Durable CAS rollout-state contract (reference file store) and backup/restore",
            "Cross-rollout conflict detection and blast-radius admission",
            "Authenticated consumption of GAP-07 verification and GAP-09 health evidence",
            "Fenced, idempotent node command protocol and authenticated acknowledgements",
            "Emergency freeze, authorization policy, cancellation, quarantine recovery and reconciliation",
            "External audit sealing, error taxonomy, telemetry and operator explain view"
        ],
        not_owns=[
            "Building update bundles",
            "Signing keys",
            "Node health measurement",
            "Node lifecycle transitions",
            "What the update contains"
        ],
        dependencies=[
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Verifies and binds provenance to the exact update bundle before any wave starts"),
            Dependency("GAP-09 Unified observability", "upstream", "Supplies authenticated, fresh health evidence for each gate"),
            Dependency("GAP-01 Edge Node Supervisor", "downstream", "Drains, installs, restarts, rolls back, and acknowledges node operations"),
            Dependency("GAP-15 Runtime compatibility certification", "upstream", "Certifies the bundle is compatible before rollout"),
            Dependency("GAP-03 Topology-aware scheduler", "upstream", "Supplies a wave plan that respects site and fault-domain blast-radius constraints"),
            Dependency("GAP-05 State replication/consistency model", "peer", "Persists rollout snapshots and supplies distributed ownership/fencing semantics"),
            Dependency("GAP-06 Device identity and attestation", "upstream", "Authenticates target nodes and binds acknowledgements to device identity"),
            Dependency("External WORM audit service", "peer", "Seals rollout audit events in a separate trust domain")
        ],
        source_of_truth="The persisted rollout state containing the immutable pinned rollback target; the local package defines and validates the state representation, while durable replicated storage is supplied externally.",
        assumptions=[
            "A node may be offline when its wave runs and must be caught later",
            "Health evidence lags the change that caused it",
            "A rollback may itself fail on some nodes"
        ],
        boundaries={
            "tenant": "OTA is estate infrastructure and is never tenant-triggered",
            "environment": "an environment is rolled out independently and does not auto-promote",
            "site": "site/fault-domain safety is a wave-plan admission requirement supplied by the topology scheduler; this local engine only validates uniqueness and non-decreasing wave size",
            "workload": "workloads are drained per node by the supervisor, not by this element"
        },
        mandatory=[
            "Admit only verification results bound to the exact update bundle",
            "Pin the rollback target before the first node is touched",
            "Evaluate a health gate after every wave and deferred-node retry",
            "Roll back automatically when a gate fails",
            "Never start a wave while the previous one is unhealthy",
            "Do not report completion while deferred nodes remain",
            "Report and quarantine rollback failures instead of hiding partial rollback"
        ],
        optional=[
            "Time-of-day rollout windows",
            "Bandwidth-aware bundle distribution",
            "Manual gate approval for the final wave"
        ],
        non_goals=[
            "Building or signing bundles",
            "Measuring node health",
            "Guaranteeing a rollback succeeds on a bricked node",
            "Promoting between environments"
        ],
        interfaces={
            "rollout": "PK_ROLLOUT/1 - staged rollout progress and completion",
            "gate": "PK_ROLLOUT_GATE/1 - the health verdict for a wave or deferred retry",
            "rollback": "PK_ROLLBACK/1 - revert to the pinned target and report partial failure",
            "state": "PK_ROLLOUT_STATE/1 - crash-recoverable rollout snapshot",
            "audit": "PK_ROLLOUT_AUDIT/1 - local chained transition-integrity record",
            "verification": "PK_VERIFICATION/1 - upstream exact-bundle verification input",
            "controller_state": "PK_CONTROLLER_STATE/1 - durable controller record wrapping PK_ROLLOUT_STATE/1",
            "command": "PK_NODE_COMMAND/1 - fenced idempotent node command",
            "ack": "PK_NODE_ACK/1 - signed, attested node acknowledgement",
            "health_evidence": "PK_HEALTH_EVIDENCE/1 - signed GAP-09 gate evidence",
            "error": "PK_ERROR/1 - machine-readable error envelope",
            "audit_seal": "PK_AUDIT_SEAL/1 - externally sealed audit entry"
        },
        threats=[
            "A verification verdict replayed or rebound to the wrong bundle",
            "Gate suppression or stale health evidence used to push a bad update through",
            "Rollback target repointed mid-rollout",
            "Wave ordering manipulated to take out a whole site",
            "Duplicate/stale controllers executing the same node operation",
            "Local state or audit history rewritten after an incident"
        ],
        failure_modes=[
            "Health gate fails after a wave",
            "A node is offline during its wave and becomes deferred",
            "Rollback fails on a subset of nodes and those nodes require quarantine",
            "Bundle verification is absent, malformed, stale, or bound to another artifact",
            "Controller crashes after partial progress and must restore persisted state",
            "Distributed ownership or state-store dependency is unavailable"
        ],
        slos=[
            Slo("blast radius", "a failing update reaches no more than the first wave before rollback", "no budget"),
            Slo("rollback pinning", "zero rollouts started without a pinned rollback target", "no budget"),
            Slo("gate honesty", "zero waves started while the previous gate was failing", "no budget")
        ],
        signals={
            "rollout_wave": "current wave index and lifecycle state",
            "gate_verdicts": "counter by wave/retry and outcome",
            "rollbacks": "counter with trigger, completeness, and failure count",
            "nodes_updated": "gauge by version",
            "deferred_nodes": "gauge and age of nodes offline during their wave",
            "quarantined_nodes": "gauge of nodes that failed rollback",
            "state_restore_failures": "counter of snapshot or audit-integrity rejection"
        },
    )
