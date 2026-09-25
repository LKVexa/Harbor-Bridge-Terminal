# Day-1: commissioning checklist (MC-051-02)

- [ ] `GET /readyz` = ready; `GET /version` shows expected version, commit, schema, backend.
- [ ] Security: `check_tls_context` clean (preflight); unauthenticated request → 401; foreign trust domain → 401; writer → admin endpoint → 403; audit log shows authn/authz events; `python -m inv05_current_control_state_system.audit <audit.log> <key-hex> <anchor.json>` → ok.
- [ ] Backup: take a backup (`tools/restore_drill.py --create`), verify, restore into an isolated dir, compare revision.
- [ ] Observability: Prometheus scrapes `/metrics` with the operator cert; dashboards in `observability/dashboards` imported; alert rules loaded; test alert fires (`freeze writes` → `INV05Degraded`).
- [ ] Capacity: run `python -m inv05_current_control_state_system.bench --durable tmp --ops 20000` on target hardware; compare with `docs/CAPACITY.md` thresholds; record report.
- [ ] Conformance: `python -m inv05_current_control_state_system.conformance.runner` → ok.
