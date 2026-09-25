# Authorised execution paths and bypass inventory (#10)

The only allow-producing function is `AdmissionController.admit()` (outcome `allow`, `runnable: true`). Runtimes
get bytes only through `AdmissionController.handoff(decision)`. It re-hashes content-store bytes at handoff (TOCTOU),
re-checks quarantine and refuses decisions made under a superseded trust generation.

| path | enforcement | status in this package |
|---|---|---|
| Orchestrator admission (Kubernetes) | `ValidatingAdmissionWebhook` → GAP-07 service (`deploy/k8s/webhook.yaml`), `failurePolicy: Fail` | manifest provided; service wiring is estate-side |
| Direct runtime API (containerd/Wasm/microVM) | runtime calls `handoff()` and loads only the returned bytes | contract + tests; runtime plugin estate-side |
| Local content cache | `VerifiedContentStore` is digest-addressed and re-verified on every handoff | implemented |
| Side-loading / operator tooling | no bypass API exists; break-glass only, via signed `PK_BREAK_GLASS/1` (2 approvers, ≤24 h, single-use nonce, audited, post-event review flag) | implemented |
| Rollback to prior artifact | treated as a new admission under **current** trust and policy; old decisions are not reused (cache keyed by trust + policy digest) | implemented |
| Recovery / DR | trust restore needs a verified backup; a stale restore needs a two-party recovery approval | implemented |
| Cached decisions | key = artifact digest, kind, trust digest, policy digest, bundle digest, waivers; TTL; cleared on any trust generation swap | implemented |

Outcomes: `allow` (runnable), `deny`, `defer` (transient dependency: time, trust, policy, KMS, log, overload),
and `error` (defect). Only `allow` is runnable. Every exception path maps to a non-runnable outcome.

Readiness (`controller.health.readiness()`) is false when trust is stale or absent, policy is expired or absent, or
trusted time is outside budget. Liveness is separate. Drift testing: `tests/test_v6_admission.py` covers side-load
(no bundle), cache after revocation, mutable tag, TOCTOU swap, overload, internal defect and dependency loss. The
estate's deployment-drift job must additionally assert that the webhook stays registered with `failurePolicy: Fail`.
