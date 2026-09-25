# INV-27 runbook (day-0 / day-1 / day-2). Owners: see [OWNERS.md](OWNERS.md)

## Day 0 — bootstrap
1. `python -B inv27_unikernel_execution/tools/bootstrap.py`. This checks the Python version, the
   vendored pk_core digests and the manifest, then runs the full test profile.
2. Load the site config: `ConfigStore.apply(cfg, actor=<you>, reason=...)`. Start from
   `config/example.prod.json`.
3. Load the trust root from the secret store (`TrustRoot.from_dict`). Confirm that `health()` shows
   `trust_root: fresh` and an approved `vmm`.

## Day 1 — deploy
Follow `ops/ROLLOUT.md`. The release gate must be GO; NO_GO blocks the deploy.

## Day 2 — operate

<a id="seal-failures"></a>**Seal failures rising.**
1. Run `explain(<decision_id>)` and look at the failing step.
2. For A2 (signature or provenance) failures, check the builder or key.
3. For A8, A9 or A10 failures, the image changed. Contact the tenant; do not widen `permitted_syscalls`
   without security-owner approval.

<a id="trust-root"></a>**Trust root stale.** Admission is already refused (fail closed). Restore the
secret-store path, then refresh. Instances that are already running are unaffected.

<a id="overload"></a>**Shedding.** Check `uk_inflight` and the per-tenant buckets. Raise limits only
through a config generation (this is audited).

<a id="latency"></a>**p99 over 100 ms.** Look for large-symbol images (TD-1) and the signature
backend. `signing.set_backend("cryptography")` gives constant-time, faster signature checks.

**Quarantine an image or tenant.** Call `quarantine(token, image_ref=... | tenant=...)`. Matching
instances are stopped and new runs are refused.

**Emergency disable.** `disable(token, reason)` makes `health().ready` false. `enable` reverses it.

**Config rollback.** `ConfigStore.rollback(n, actor, reason)`. History is hash-chained, so check it
with `verify_history()`.

**Controller restart.** The journal replays. Instances that were not terminal become
`failed → stopped`, because the VMM process group dies with the controller.
