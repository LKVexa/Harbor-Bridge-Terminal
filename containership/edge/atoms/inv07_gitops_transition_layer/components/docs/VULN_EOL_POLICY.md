# Patch, EOL and vulnerability policy (PROPOSED — owner approval pending)

* **Supported lifetime:** each minor release 12 months; the last two minors receive security fixes.
* **Runtime surface:** zero third-party Python runtime dependencies; external executables `git` (and optional `gpg`) follow the host OS vendor's patch stream.
* **CVE triage:** critical 24 h / high 7 d / medium 30 d / low next release, from disclosure to released fix.
* **Emergency patch path:** fix branch → full test suite + gates (`tools/gates.py`) → signed release → rolling restart (lease hand-off keeps one writer).
* **Deprecation:** schema majors supported one release after successor; config keys warned one release before removal.
* **Rolling upgrade / rollback:** see `OPERATIONS.md`; state version gates prevent downgrade onto newer state.
* **Advisory feed:** not selected — owner decision (BLOCKED).
