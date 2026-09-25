"""INV-60 hardened fabric control plane (4.3.0).

Stdlib-only modules that implement the M09-M75 control surfaces around the
reference ``runtime.Lattice``: result/error model, lifecycle state machines,
identity/authentication, authorization, artifact signing/provenance, limits,
resilience, placement precedence, membership/leases, durable state, audit
ledger, configuration, secrets, telemetry, negotiation, wire schemas and a real
WebAssembly execution backend (Node's WebAssembly engine).

These are verified locally. They are NOT a wasmCloud/NATS/wadm deployment;
see docs/ADR-0001 and WAIVERS.json for what remains blocked.
"""
FABRIC_API_VERSION = "1.0.0"
