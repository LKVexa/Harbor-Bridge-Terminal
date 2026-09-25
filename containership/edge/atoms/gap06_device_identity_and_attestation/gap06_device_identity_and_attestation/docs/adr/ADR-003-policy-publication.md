# ADR-003: M-of-N Ed25519 signed measurement policy with monotonic versions
Status: Proposed · Date: 2026-09-22

**Decision.** Canonical-JSON bundle, ≥2 distinct pinned approvers, integer version strictly increasing per environment, `not_before` staging, percentage rollout by stable hash, atomic activation in one store transaction. Emergency rollback = re-issue old content under a *new* version with the same quorum.
**Rejected.** Single signer (TH11); timestamp versions (clock-dependent); allowing lower versions with a flag (silent rollback).
**Links.** TH11, TH12 · `mc/policy.py` · `PolicyTest`.
