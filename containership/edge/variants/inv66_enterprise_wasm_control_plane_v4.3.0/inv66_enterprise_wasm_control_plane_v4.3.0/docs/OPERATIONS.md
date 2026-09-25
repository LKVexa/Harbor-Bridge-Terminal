# INV-66 operations: observability, runbooks, backup/restore, incident response, reviews

Document ID `INV66-OPS` · v1.0.0 · covers MC-049 – MC-054, MC-063 – MC-066. Every procedure below is executable with the shipped CLI/tools; none relies on author memory.

## 1. Signals (MC-049 – MC-053)

* **Endpoints:** `/healthz` (audit chain verifies), `/readyz` (leader + config + store OK + dependency/breaker states), `/version` (version, protocols, config revision+digest, audit head, capabilities), `/metrics` (Prometheus text).
* **Metrics:** `inv66_admissions_total{outcome}`, `inv66_admission_latency_ms_bucket`, `inv66_rbac_denials_total{capability}`, `inv66_authn_failures_total{code}`, `inv66_audit_entries_total{kind}`, `inv66_deliveries_total{outcome}`, `inv66_store_failures_total`, `inv66_compactions_total`, `inv66_maintenance_errors_total`, gauges `inv66_outbox_depth`, `inv66_inflight`, `inv66_audit_head_sequence`, `inv66_audit_anchor_sequence`, `inv66_freezes_active`, `inv66_leader`. Label cardinality capped at 200 values per label.
* **Logs:** JSON lines, schema `PK_ECP_LOG/1`, fields `ts level service event trace_id span_id request_id tenant lattice outcome duration_ms`; tokens/secrets/signatures redacted by key name and by JWT shape.
* **Traces:** W3C `traceparent` accepted, a child span id is generated per admission and propagated to GAP-13 and INV-63; `trace_id` is stored on the decision and returned to the caller.
* **Explain:** `GET /v1/decisions/{id}/explain` → principal, issuer, config revision+digest+approvers, policy bundle version, every error code, freeze state, lifecycle history.

## 2. Telemetry retention, privacy, dashboards, alerts (MC-054)

| Signal | Retention | Sampling | Privacy |
|---|---|---|---|
| Metrics | 400 days (capacity trend) | none | no principals in labels |
| Logs | 30 days hot, 1 year cold | none for `warn`+, info may be sampled ≥ 10 % | principals are pseudonymous ids; no tokens/secrets |
| Traces | 7 days | 10 % head sampling, 100 % on error | same as logs |
| Audit journal | per `audit_retention_records` + archive policy; legal hold overrides purge | never sampled | contains principals and manifests; access = `audit.read` |

Dashboards: `deploy/dashboard.json` (Grafana). Alerts: `deploy/alerts.yaml` (Prometheus rules) — each rule links the runbook section below.

## 3. Day-0 bootstrap (MC-064)

1. Provision encrypted volume for `/var/lib/inv66/store` and a separate WORM location for anchors.
2. Create secrets: anchor MAC key (`head -c32 /dev/urandom > /etc/inv66/anchor.key; chmod 600`), TLS material.
3. Write `config.json` (`PK_ECP_CONFIG/1`) with `secrets.anchor_key: file:///etc/inv66/anchor.key`, identity issuers, signers, bindings, quotas; get a second approver into `approved_by` (enforced for prod).
4. `inv66 validate-config config.json` → record the printed digest in the change ticket.
5. Install (`pip install -c constraints.txt .` or `deploy/Dockerfile`), enable `deploy/inv66.service`.
6. Start; check `/readyz` = 200, `/version` shows the expected config digest; run `inv66 verify`.

## 4. Day-1 deployment / upgrade (MC-061, MC-064)

Follow `deploy/rollout.yaml`. Before each stage: `inv66 verify` on the site store, take a backup (§6). Upgrade the standby first, fail over by stopping the leader (lease expires in ≤ 10 s), upgrade the old leader. Rollback: redeploy the previous artifact digest; the journal format is forward-compatible within `PK_ECP_AUDIT/1`.

## 5. Day-2 operations (MC-064)

| Task | Procedure |
|---|---|
| Change policy/RBAC/registries/signers | new revision (revision number must exceed every prior one) → `POST /v1/config` with an org-admin/policy-admin token; verify `/version` digest |
| Roll back config | `POST /v1/config/rollback {"revision": N}` |
| Rotate keys | THREAT_MODEL.md "Keys and secrets" |
| Emergency stop (kill switch) | `POST /v1/freeze {"scope":"org:<org>","on":true,"reason":"..."}` — blocks admission *and* delivery of already-admitted items; tenant/lattice scopes for targeted quarantine |
| Quarantine a deployment | `POST /v1/decisions/{id}/transition {"to":"quarantined"}` then `rolled_back` or `admitted` |
| Drain delivery backlog | automatic each maintenance tick; manual: restart or call `drain_outbox` via ops shell |
| Capacity | ARCHITECTURE.md §4 thresholds; add a site instance per environment/site, never a second writer on one store |
| Compaction / retention | automatic; `purge_archives(older_than_seq, legal_hold)` for archive lifecycle |
| Maintenance windows | freeze the scope, perform work, `inv66 verify`, unfreeze |

## 6. Backup, restore, migration, reconstruction (MC-063)

* **Backup:** `inv66 backup --store DIR --dest DIR --config C` — consistent (takes the writer lock), writes `BACKUP_MANIFEST.json` (per-file SHA-256, head). Schedule hourly + before every change; copy off-site. RPO = backup interval (journal replication on the volume gives RPO≈0 within a site).
* **Restore:** stop the service; `inv66 restore --backup B --store EMPTY_DIR --config C` verifies manifest hashes, chain and anchors, drops the old lease; start the service → new epoch. RTO target 15 min. Tampered backups are refused (tested).
* **Reconstruction:** state = replay of snapshot + journal; nothing else needs restoring. Inventory is rebuilt from admission/lifecycle entries.
* **Migration** (future store formats): replay records through `ControlPlaneService._apply` into the new store; verify the new chain; keep the old store read-only until the next anchor verifies.
* **Drills:** quarterly restore drill into a scratch directory; record `restore` output JSON as evidence.

## 7. Incident response and on-call (MC-065)

| Sev | Examples | Page | Response |
|---|---|---|---|
| Sev1 | `Inv66AuditChainBroken`, `Inv66AnchorMismatch`, unadmitted delivery suspected, no leader > 2 min in prod | immediately, 24×7 | ack 5 min; security owner engaged |
| Sev2 | policy engine down (all admissions rejected), store failures, outbox depth rising > 30 min | 24×7 | ack 15 min |
| Sev3 | latency SLO burn, quota saturation | business hours | next business day |

Containment: freeze the narrowest scope that stops harm (lattice → tenant → org). **Evidence preservation:** before any repair, `inv66 backup` the store and copy the WORM anchor file; export audit (`POST /v1/audit/export`) — its MAC'd manifest is the evidence seal. **Recovery criteria:** `inv66 verify` passes, anchors verify, `/readyz` 200 for 30 min, no alert firing. **Communications:** service owner notifies affected tenants with decision ids and time window; post-incident review within 5 business days, actions tracked in `governance/WAIVERS.json` or backlog.

## 8. Recurring reviews (MC-066)

`python tools/review.py --config <config.json> --out governance/reviews/<date>.json` (scheduled weekly in CI; results retained): access review (expired/soon-expiring bindings, broad org-level grants, subjects with both deploy and config rights), policy/config review (revision history, approvers), dependency review (installed vs `constraints.txt`), waiver expiry, architecture review due date (ADR). Findings with severity ≥ High fail the job.
