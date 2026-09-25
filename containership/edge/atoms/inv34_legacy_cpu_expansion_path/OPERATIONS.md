# INV-34 Operations Runbook

## Day 0 — bootstrap

1. Install the repository beside its required `pk_core` framework if framework gating is desired.
2. Run the standalone unit suite in normal and optimized Python modes.
3. Configure the external capability source and hypervisor/guest adapter.
4. Seed each VM with independently observed current CPU count, configured maximum, host capacity and capability flags.
5. Start with `expansion_enabled=false` until adapter and authorization checks pass in the target environment.

## Day 1 — rollout

Use canary VMs first. For each accepted expansion, record request ID, generation, desired count, adapter operation ID, observed progress and convergence time. Stop rollout on unauthorized requests, observation regressions, repeated non-convergence, or adapter divergence.

## Day 2 — steady state

Track pending-vCPU backlog, rejected requests by error code, state generation, and convergence latency. Refresh host capacity before accepting new targets. Reconcile any VM where desired and observed counts remain different beyond the environment-specific objective.

## Emergency disable

Set the environment/control-plane policy so new instances are constructed with `expansion_enabled=false` (or block requests before the controller). Existing observed CPUs are not removed. Pending expansions must be reconciled or explicitly abandoned by the external controller; this repository does not perform hot-unplug.

## Rollback

Code rollback may revert the controller package, but desired/observed state must not be rolled backward blindly. Restore state only from a durable source that is reconciled against live hypervisor/guest observation. The lack of a bundled durable store is a known production gap.
