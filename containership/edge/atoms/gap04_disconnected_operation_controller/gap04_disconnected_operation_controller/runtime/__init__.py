"""GAP-04 production runtime layer (v4.3.0).

The ``controller`` module remains the dependency-free reference state machine.
This package composes it with the P0 production controls from the GAP-04
missing-components checklist: signed leases, trusted time, durable journal,
tamper-evident audit, epochs/fencing, reconciliation, adapters, encrypted
state, configuration, and operational surfaces. See ``MASTER.md``.
"""
