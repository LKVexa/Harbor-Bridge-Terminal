"""Sub-check kind vocabulary.  Every one of the 2,420 checklist sub-checks is
mapped to exactly one kind by matching the text of its template (``TEMPLATES``);
component-specific items (the first 1-5 items of a component, whose text is
unique) are ``spec1``..``spec5`` in order of appearance.
"""

# kind: (template prefix as it appears in the checklist, evidence class)
TEMPLATES = {
    # universal (116 each)
    "impl-doc": ("Implement and document the exact behavior required by this inventory item", "test"),
    "owners": ("Assign a named engineering owner", "human"),
    "normative": ("Write a normative requirement statement", "doc"),
    "interfaces": ("Define public/internal interfaces", "doc+test"),
    "deps": ("Enumerate dependencies and trust boundaries", "doc+test"),
    "config": ("Define configurable parameters with units", "doc+test"),
    "telemetry": ("Instrument lifecycle, success/failure", "test"),
    "unit": ("Add deterministic unit tests", "test"),
    "integration": ("Add integration tests using real or standards-compatible dependencies", "test"),
    "fault": ("Add fault-injection tests", "test"),
    "perf": ("Measure CPU, memory, descriptor/socket/task counts", "bench"),
    "runbook": ("Document operator diagnostics, safe remediation", "doc"),
    "acceptance": ("Produce machine-readable acceptance evidence tied to source revision", "gate"),
    "exit": ("**Component exit gate:**", "gate"),
    # group A (traversal, 16)
    "protocol-map": ("Map the component to the applicable wire protocol", "doc"),
    "ownership": ("Define candidate/address/socket ownership", "doc+test"),
    "txn": ("Implement explicit transaction identifiers", "test"),
    "fallback-policy": ("Define protocol downgrade/fallback ordering", "test"),
    "nat-matrix": ("Verify behavior across endpoint-independent, address-dependent", "lab"),
    "pcap": ("Capture packet-level interoperability evidence", "lab"),
    # group B (network, 11)
    "snapshot": ("Build an immutable local-network snapshot model", "test"),
    "notifications": ("Consume operating-system network-change notifications", "test"),
    "coalescing": ("Define event coalescing, debounce, hysteresis", "test"),
    "pinning": ("Make interface/route selection explicit at socket creation", "test"),
    "observe-only": ("Separate observation from mutation", "test"),
    "transitions": ("Test suspend/resume, interface rename, DHCP renewal", "lab"),
    # group C (quality, 15)
    "state-machine": ("Define the component state machine, legal transitions", "test"),
    "separation": ("Separate liveness, reachability, quality, readiness", "test"),
    "monotonic": ("Use monotonic time for durations and deadlines", "test"),
    "anti-oscillation": ("Prevent noisy measurements from causing oscillation", "test"),
    "selection-inputs": ("Ensure relay cost, quota, path quality, identity/trust", "test"),
    "recovery": ("Test recovery from transient loss, prolonged partition", "test"),
    # group D (security, 13)
    "threat-model": ("Create a component-specific threat model", "doc"),
    "authz-identity": ("Bind authorization decisions to authenticated peer/service identity", "test"),
    "auth-control": ("Use cryptographically authenticated control messages", "test"),
    "key-lifecycle": ("Define credential/key lifecycle behavior", "test"),
    "resource-bounds": ("Enforce bounded memory, CPU, sockets, allocations", "test"),
    "audit": ("Generate security audit events with stable reason codes", "test"),
    # group E (state, 11)
    "concurrency-model": ("Choose and document the concurrency model", "doc+test"),
    "atomic": ("Make all externally visible state transitions atomic and orderable", "test"),
    "idempotency": ("Define idempotency and duplicate-event semantics", "test"),
    "bounded": ("Bound queues, histories, caches, task counts", "test"),
    "crash-recovery": ("Specify crash/restart recovery", "test"),
    "race-tests": ("Exercise race detectors/stress tests", "test"),
    # group F (config, 8)
    "schema": ("Define a versioned machine-readable schema", "test"),
    "semantic": ("Perform semantic validation before activation", "test"),
    "overlays": ("Separate immutable artifact configuration from environment/site overlays", "test"),
    "atomic-apply": ("Apply configuration changes atomically", "test"),
    "provenance": ("Record provenance for every effective configuration", "test"),
    "config-tests": ("Test malformed input, unknown fields, rollback", "test"),
    # group G (observability, 10)
    "vocabulary": ("Define a stable telemetry vocabulary", "test"),
    "cardinality": ("Control metric label/cardinality growth", "test"),
    "redaction": ("Apply structured endpoint/identity redaction", "test"),
    "correlation": ("Propagate operation/correlation identifiers", "test"),
    "reason-codes": ("Expose reason codes that distinguish network failure", "test"),
    "alert-validation": ("Validate dashboards and alerts using synthetic failure injection", "test"),
    # group H (testing, 16)
    "deterministic": ("Define deterministic test topology, fixtures, seeds", "test"),
    "coverage": ("Cover happy path, every documented failure branch", "test"),
    "family-matrix": ("Run tests under IPv4, IPv6, dual-stack, NAT variants", "lab"),
    "neg-security": ("Add negative security cases for spoofing, replay", "test"),
    "results": ("Produce machine-readable results containing build ID", "gate"),
    "no-skip": ("Gate release on zero skipped mandatory tests", "gate"),
    # group I (release, 16)
    "runtime-matrix": ("Define the supported platform/runtime/dependency matrix", "test"),
    "reproducible": ("Make builds reproducible and attributable", "test"),
    "staged": ("Implement staged deployment with canary health criteria", "test"),
    "runbooks": ("Create runbooks with preconditions, exact diagnostics", "doc"),
    "vuln": ("Define vulnerability intake, severity, remediation SLA", "human"),
    "gate": ("Require a formal production gate that aggregates", "gate"),
}

KINDS = set(TEMPLATES) | {"spec1", "spec2", "spec3", "spec4", "spec5"}
