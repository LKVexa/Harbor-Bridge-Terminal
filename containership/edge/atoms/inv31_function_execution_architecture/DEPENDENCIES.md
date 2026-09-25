# INV-31 Dependencies

## Required framework dependency

- `pk_core` — provides `Contract`, `Dependency`, `Slo`, checklist/finding types, the component base class, and the parent conformance/evidence/gate commands. It is **not bundled** in this archive and no installable version coordinate is declared here.

## Architectural dependencies declared by the contract

- `PLN-04 Execution plane` — supplies the execution-isolation tier.
- `INV-26 MicroVM snapshotting` — can reduce cold-start cost.
- `PLN-05 Elasticity plane` — owns scaling outside this local safety pool.
- `GAP-09 Unified observability` — receives operational signals in the complete system.

The package can run its standalone runtime tests without those adjacent architectural components, but end-to-end certification cannot be performed from this archive alone.
