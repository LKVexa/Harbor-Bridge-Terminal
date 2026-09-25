# INV-23 incident runbook

Common first steps for every incident: capture `inv23-probe --status` output (it contains
no secrets), the claim state directory listing, the relevant `INV23-E0xx` events, and the
current `evidence/` head (`python tools/verify_evidence.py`). Open an incident record
with the event IDs and component version.

| Incident | Containment | Evidence | Rollback / recovery | Post-incident validation |
|---|---|---|---|---|
| False `usable` result | Set consumers to refuse (`require_usable` with `max_nesting=0`) or remove host from pool | probe report + `evidence` block, dmesg, /dev/kvm perms | Revert to previous sealed release; add fixture reproducing the evidence | New backend unit test + hardware row re-run |
| Claim split brain | Stop both VMMs; `ProviderX.status()` | ownership record, history, events E003/E007/E008 | `repair()` to quarantine and bump generation; restart one owner | multiprocess suite + fencing tests on that host |
| Fencing failure (old generation acted) | Disable the downstream operation path | downstream logs with generation numbers | patch downstream to call `ClaimManager.fence()` before privileged ops | integration test proving rejection |
| Evidence corruption | Freeze releases | `tools/verify_evidence.py` output, checksums | restore last good ledger from release archive; re-run gate | verify passes; head chains to previous release |
| Probe-helper compromise | n/a today (no helper); if ctypes DLL hijack suspected, block host | DLL path/hash | reinstall OS component | re-probe on clean host |
| Dependency vulnerability | Pin/patch; vendored pk_core re-pinned only from owner source | pip-audit / advisory | new release with updated SBOM | gate + SBOM diff |
| SLO regression | Keep previous release on affected machine class | `benchmark-results.json` vs baseline | revert commit; or file time-boxed waiver (security/waivers.json) | benchmark back under threshold |
| Unsupported host admitted | Remove host; check COMPATIBILITY row | probe report | fix classification to `indeterminate` for that platform | add matrix row + test |
