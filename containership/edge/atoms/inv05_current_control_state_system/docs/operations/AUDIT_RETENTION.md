# Audit retention and archival (MC-038-05)

* The live audit file is append-only (O_APPEND, 0600); the service has no API to delete or rewrite it.
* Daily: rotate by copying the file and its `anchor()` to WORM object storage (object lock, 1 year governance retention), then start a new file whose first entry references the previous anchor in `extra`.
* Weekly scheduled verification: `python -m inv05_current_control_state_system.audit <file> <key-hex> <anchor.json>` for every archived segment; failures page SEV2.
* Read access requires `admin.audit_read` (security-admin); write access is the service identity only; delete is restricted to the storage retention policy.
