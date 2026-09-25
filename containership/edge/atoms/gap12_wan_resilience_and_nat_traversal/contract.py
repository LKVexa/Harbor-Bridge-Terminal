"""Binding contract for GAP-12 - WAN resilience and NAT traversal.

WAN resilience and NAT traversal keeps an edge site reachable from behind hostile
or unstable networks.  It escalates connection strategies in cost order, uses
bounded jittered backoff, and distinguishes unknown/stale paths from a confirmed
partition instead of presenting stale reachability as healthy.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-12"
ELEMENT_NAME = "WAN resilience and NAT traversal"


def build() -> Contract:
    """Return the production contract for GAP-12."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own reachability to and from edge sites across hostile networks: escalate through direct, "
            "hole-punched and relayed paths in cost order, apply bounded jittered exponential backoff, "
            "and report confirmed partitions without masking stale or unknown path state."
        ),
        owns=[
            "Connection strategy escalation and its order",
            "NAT traversal attempts and their outcomes",
            "Backoff schedule, jitter and bounds",
            "Path health and the partition verdict",
            "Relay fallback and its byte accounting",
        ],
        not_owns=[
            "Transport encryption",
            "Data replication semantics",
            "Autonomy policy during partition",
            "Application protocols",
            "Relay infrastructure provisioning",
        ],
        dependencies=[
            Dependency("GAP-06 Device identity and attestation", "upstream", "Identifies the peer before a path is used"),
            Dependency("GAP-04 Disconnected-operation controller", "downstream", "Consumes the partition verdict"),
            Dependency("PLN-06 Data plane", "downstream", "Uses the established path for bulk transfer"),
            Dependency("GAP-09 Unified observability", "downstream", "Receives path, retry and traversal signals"),
        ],
        source_of_truth=(
            "The latest completed probe round and its outcomes. A recent success is health evidence; "
            "an exhausted round is partition evidence; an untested or stale path is not healthy."
        ),
        assumptions=[
            "Many edge sites sit behind symmetric or carrier-grade NAT where hole punching can fail",
            "Relays cost money and bandwidth, so they are a last resort",
            "A link may be reachable for probes but unsuitable for bulk traffic",
            "Production callers use a monotonic clock for retry and freshness decisions",
        ],
        boundaries={
            "tenant": "paths are site-level infrastructure, never tenant-specific",
            "environment": "relay pools and traversal policy differ per environment",
            "site": "each site pair has its own path state",
            "workload": "workloads use paths but never select them",
        },
        mandatory=[
            "Try connection strategies in declared cost order",
            "Apply bounded exponential backoff with jitter between safe retries",
            "Report a partition only after every strategy in a probe round is exhausted",
            "Never report a path healthy without a recent successful probe",
            "Fall back to relay only after cheaper strategies fail",
            "Record attempt outcomes without retaining sensitive exception text",
        ],
        optional=[
            "Path quality scoring beyond up/down",
            "Multi-path striping",
            "Predictive relay pre-warming",
        ],
        non_goals=[
            "Encrypting traffic",
            "Provisioning relays",
            "Deciding what to do during a partition",
            "Guaranteeing connectivity through a severed link",
        ],
        interfaces={
            "connect": "PK_PATH_REQUEST/1 - establish a path to a peer site",
            "path": "PK_PATH_STATE/1 - current strategy, health, status and retry state",
            "backoff": "PK_BACKOFF/1 - current retry schedule, jittered delay and bound",
            "relay_accounting": "PK_RELAY_ACCOUNTING/1 - bytes attributed to an active relay path",
        },
        threats=[
            "A hostile relay observing or altering traffic",
            "Retry synchronization or backoff abuse causing denial-of-service",
            "Path state forgery presenting a partition as healthy",
            "Relay billing abuse by forcing relay fallback",
            "Probe/plugin exceptions leaking sensitive endpoint material into diagnostics",
        ],
        failure_modes=[
            "All strategies exhausted",
            "Symmetric NAT defeats hole punching",
            "Relay unavailable",
            "Probe succeeds but bulk transfer fails",
            "Traversal plugin raises or stalls",
        ],
        slos=[
            Slo("path honesty", "zero paths reported healthy without a probe inside the freshness window", "no budget"),
            Slo("escalation order", "zero relay fallbacks before cheaper strategies were tried", "no budget"),
            Slo("backoff bound", "retry interval never exceeds the declared ceiling", "no budget"),
        ],
        signals={
            "path_strategy": "current strategy per site pair",
            "path_status": "unknown, healthy, stale, backing_off or partitioned",
            "traversal_attempts": "counter by strategy and outcome",
            "probe_errors": "counter by strategy and sanitized exception type",
            "backoff_seconds": "gauge of the current exponential retry bound",
            "retry_in_seconds": "gauge of time until the next eligible retry",
            "relay_bytes": "counter of bytes carried over relays",
            "partitions_declared": "counter of site pairs declared partitioned",
        },
    )
