# Deployment, upgrade, migration and rollback

Traceability: C038, C092; MC-050.

* **Artefacts:** `deploy/Dockerfile` (non-root, read-only root FS), `deploy/inv05.service` (systemd hardening), `deploy/k8s/statefulset.yaml` (resources, securityContext, probes).
* **Preflight (MC-050-02):** `python tools/preflight.py --config ...` validates config, runtime self-test, TLS files/policy, backend pin status, free disk (> 2× WAL checkpoint size), and secret availability; any failure aborts the rollout.
* **Staged rollout (MC-050-03):** canary one node/site → 1 h bake with gates: readiness ready, `cstate_requests_total{result!="ok"}` ratio < 0.1 %, p99 txn latency within SLO, zero `CSTATE_FAILED`; then 25 % → 100 %.
* **Migrations (MC-050-04):** WAL/snapshot formats are versioned; a format change ships as: N+1 reads old+new, writes old; N+2 writes new. Protocol minors are additive.
* **Rolling upgrades (MC-050-05):** `graceful_shutdown()` drains watches with a terminal `CSTATE_DRAINING` + resume revision; clients resume on another member; transactions are atomic per request, so no txn spans an upgrade.
* **Rollback (MC-050-06):** automatic if any canary gate fails for 10 min; manual via previous image digest. 4.3.0 → 4.2.x is safe (4.2.x had no persistent format).
* **Emergency disable:** `POST /v1/admin/break_glass` (security-admin, audited).
