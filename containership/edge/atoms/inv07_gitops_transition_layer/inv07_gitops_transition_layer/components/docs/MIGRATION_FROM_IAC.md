# Migration from traditional IaC (INV-06 → INV-07)

Implemented by `components/migration.py`; states per partition (namespace or resource group):

1. **Inventory** — list every resource the IaC pipeline manages in the partition, with its IaC state digest.
2. **iac_owned → dual_observe** — INV-07 renders and diffs, never mutates. Run the dual-run detector (`migration.compare`) each sync.
3. **dual_observe → dual_run** — INV-07 applies only objects carrying its ownership annotation; IaC keeps the rest. Any object both would change is a conflict and blocks cutover.
4. **Stabilisation** — N consecutive clean comparisons (default 3), zero conflicts, zero unowned objects.
5. **dual_run → gitops_owned** — requires a distinct named approver; records IaC digest and first GitOps OID (lineage). Disable the IaC pipeline for the partition.

**Rollback boundary:** any state before `gitops_owned` can return to `iac_owned`; after cutover, rollback is a signed revert in Git, not a return to IaC.
