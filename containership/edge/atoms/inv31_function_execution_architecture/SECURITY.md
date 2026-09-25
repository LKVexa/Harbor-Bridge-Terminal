# INV-31 Security Model

## Enforced in this repository

- Warm reuse is exact-match on tenant and code version.
- Instance identity cannot be mutated after construction.
- Invocation scratch state is scoped per active invocation and cleared on completion.
- Concurrent entry is bounded and lock-protected.
- Total instance count is bounded by a fail-closed safety ceiling.
- Empty/blank, oversized, control-character-bearing identifiers and invalid time values are rejected.
- Clock rollback cannot make a future-created instance eligible for warm reuse.
- Pool diagnostics exclude scratch contents.
- Active instances are not destroyed implicitly by drain/quarantine operations.

## Trust boundary

This package does not authenticate tenants, verify executable artifacts, enforce kernel/network/device isolation, manage encryption keys, or provide attestation. It assumes the parent platform supplies a trustworthy tenant identity, a trustworthy code-version identity, and the underlying execution isolation tier.

## Residual security work

The full post-hardening gap list includes artifact signature/provenance verification, authentication/authorization, least-privilege capability design, encryption policy, tamper-evident auditing, side-channel analysis, and adversarial testing. Those controls are not represented as complete implementations in this standalone archive.
