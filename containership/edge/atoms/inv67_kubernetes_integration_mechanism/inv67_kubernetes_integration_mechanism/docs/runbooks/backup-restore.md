# Runbook — backup, restore and reconstruction (item 58)
**What is state:** WasmWorkload objects (in etcd — covered by the cluster's etcd backup), the controller's intent journal and audit log (`/var/lib/inv67`), config/secret objects.
**What is reconstructable:** all `status` (re-derived from the runtime on reconcile), leader Lease, metrics.
**Backup:** cluster etcd/Velero backup of the `WasmWorkload` CRs + ConfigMap; ship `audit.jsonl` + exported head digest to the evidence sink daily.
**Restore:** restore CRD then CRs; start controller; it resyncs and re-observes. Because appId includes the object uid, restored objects with *new* uids are new applications — cancel the old placements via the orphan runbook first.
**Audit chain restore:** verify with `AuditLog.verify(records, expected_head)` using the exported head; a mismatch is a security incident.
**Exercise:** restore drill has **not** been run against a real cluster (EXC-007).
