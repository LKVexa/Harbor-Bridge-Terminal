# Trust bootstrap (INV-38-C044)

Node, workload/control-plane callers, and backend/provider agents are
authenticated before any queue/memory metadata exchange or resource allocation.
Provider identity is bound to the expected device scope. Artifact identity is
verified separately from process identity (see C045). There is no unauthenticated
maintenance mode (`security/peer-auth-policy.yaml`). Replay/freshness checks apply.
Model tests confirm zero privileged allocation before authentication succeeds.
**Status:** `IN_PROGRESS` — live identities/attestation required for full evidence.
