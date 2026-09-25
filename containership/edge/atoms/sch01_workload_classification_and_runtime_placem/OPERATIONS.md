# SCH-01 Operations - 4.2.0

## Day 0 - bootstrap

1. Run the standalone engine test suite.
2. If the deployment uses the conformance framework, make `pk_core` available and run `tests/test_component.py`.
3. Validate the adjacent execution controller and topology/fair-share provider if those integrations are required.
4. Archive the exact source version and generated conformance evidence before deployment.

## Day 1 - deployment

- Deploy the immutable scheduler artifact and site/environment configuration through the owning platform.
- Treat missing attestation, policy, or execution-plane dependencies as a fail-closed condition where they are required by deployment policy.
- Do not interpret skipped `pk_core` tests as a release gate pass.

## Day 2 - operation

- Re-run standalone tests on every code change.
- Re-run the external conformance gate whenever the contract, integrations, or deployment policy changes.
- Investigate increases in `NO_CANDIDATE` and in rejection reasons rather than weakening hard constraints.

## Rollback

Roll back to the previously approved immutable artifact and its matching configuration/evidence set. The repository does not yet provide a transactional configuration store, canary controller, or automated rollback orchestrator.

## Emergency disable

Disable registration/traffic to SCH-01 through the owning control plane. This repository does not contain a production kill-switch implementation by itself.
