# INV-07 compatibility matrix

| Dimension | Declared | Verified in this archive | Status |
|---|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 | 3.11.15 (Linux, this pass) | 3.10/3.12/3.13 **not run** |
| OS / CPU | Linux x86_64/arm64, Windows 10+ x86_64, macOS 13+ | Linux x86_64 | others **not run** |
| git | ≥ 2.31 (GIT_CONFIG_COUNT) | 2.43.0 | older refused at start |
| OpenPGP | GnuPG ≥ 2.2 (optional lane) | 2.4.x lane ran | — |
| Git servers | any smart-HTTPS/SSH server (GitHub, GitLab, Gitea, Azure Repos) | `file://` only | **BLOCKED**: no server reachable |
| Kubernetes | 1.27–1.31 server-side apply | recorded-request tests only | **BLOCKED**: no cluster |
| Argo CD | 2.9+ (`Application` v1alpha1) | status normalisation fixtures | **BLOCKED** |
| Flux | v2.2+ (`source.toolkit.fluxcd.io/v1`, `kustomize.toolkit.fluxcd.io/v1`) | fixtures | **BLOCKED** |
| Helm / Kustomize rendering | external pinned binaries | not bundled | **BLOCKED** |
| KMS / HSM | adapter slot (`kms:` refs) | fake provider only | **BLOCKED** |
| Policy engines | built-in; OPA/CEL adapter slot | built-in | OPA **BLOCKED** |
| Container runtime | OCI (containerd, CRI-O, Docker) | Dockerfile not built | **BLOCKED**: base image digest must be pinned |
| Schemas | PK_GITOPS_*/1 | stdlib + jsonschema 4.26 lane | — |
| Adjacent | INV-05 (target), INV-06 (migration), GAP-07 (provenance verifier slot), INV-63 (peer) | interfaces only | **BLOCKED**: siblings absent |
