# Deployment / Support Matrix (MC-006) and Supported Versions (MC-064)

Status: **Draft.** "Validated" means a retained test run exists in `evidence/`. Everything else is declared only and `execution.check_platform(strict=True)` refuses it.

| Dimension | Validated | Declared (not yet validated) | Excluded |
|---|---|---|---|
| OS | Linux x86_64 | Windows 10/11 x64, macOS 13+ arm64 | 32-bit, z/OS |
| Python | 3.11 | 3.10, 3.12, 3.13 | ≤3.9, 3.14+ until tested |
| State backend | local POSIX filesystem with fsync | NFSv4 with close-to-open; Windows NTFS | OneDrive/Dropbox-synced folders, SMB without leases |
| Lock scope | single host, multi-process | shared FS multi-host | cross-site (needs `LeaseBackend` adapter) |
| Execution engine | none bundled | Terraform 1.9.x / OpenTofu 1.8.x pinned by digest | unpinned or auto-downloaded engines |
| Providers | `InMemoryProvider` (conformance) | any provider pinned in `ProviderRegistry` | unpinned providers |
| Tiers | cloud control-plane host | datacenter, near-edge (offline queue) | far-edge constrained (MC-055 power/thermal not measured) |
| pk_core | not bundled | parent-workspace version supplying `Contract/Component` | — |
