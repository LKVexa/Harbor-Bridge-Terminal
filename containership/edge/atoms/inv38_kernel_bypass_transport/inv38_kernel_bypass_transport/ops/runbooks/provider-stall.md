# Runbook: provider-stall (INV-38-C097)

**Detection:** see `observability/alerts/inv38-alerts.yaml`.
**Immediate containment:** disable bypass / drain queues / revoke VF as applicable.
**Diagnosis:** `tools/inv38-explain <operation_id>`; inspect decision + audit records.
**Recovery:** revalidate identity/policy/key/time; verify provider health; re-enable bypass.
**Evidence:** preserve logs, traces, audit chain (`audit_log.verify_chain`), config/release digests.
