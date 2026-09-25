"""SURROGATE adjacent-layer fixtures (INV-15, INV-10, INV-17, INV-20).

These are *local, contract-shaped stand-ins* written against the dependency
descriptions in ``contract.py``.  They let INV-16 prove its own side of each
integration (ownership, cancellation/trap propagation, cleanup, isolation,
exactly-once) today.  They are NOT the real sibling components; every closure
item that requires the real fixture stays BLOCKED/PARTIAL in
``docs/CLOSURE_LEDGER.md`` until the pinned sibling replaces the surrogate
behind the same interface (``SURROGATE = True`` marks each module).
"""
