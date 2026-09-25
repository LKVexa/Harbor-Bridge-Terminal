# Day 1 — rollout, canary, rollback (MC-19, MC-22, MC-68)

**Canary**
1. Gate the new build: `CONDITIONAL_GO` or `GO`.
2. Set `pln07-canary` replicas to 1 with the new digest-pinned image.
3. Watch 30 min: `pln07_requests_total{outcome!="ok"}` ratio vs stable, p99 vs budget, audit chain ok.
4. Promote: update the stable image, rolling update (`maxUnavailable: 0`), then scale canary to 0.

**Config change**
`ConfigStore.activate(overlay, author=, change_id=, health_probe=probe)`. A failing probe rolls back automatically. Manual: `ConfigStore.rollback(author=, reason=)`.

**Code rollback**
Redeploy the previous image digest. The revocation log is forward-compatible; do not delete it.

**Emergency disable**
`POST /admin/freeze {"kind":"plane"}` on each instance (loopback) or scale to 0. Frozen = deny everything, which is safe.
