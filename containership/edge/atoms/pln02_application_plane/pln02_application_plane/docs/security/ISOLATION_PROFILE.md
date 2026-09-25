# Ambient-authority reduction and isolation profile (MC-20, C043, C046, C047)

The resolver needs **no** filesystem, network, device, kernel or secret authority. The service needs exactly:

| Capability | Scope | Why |
|---|---|---|
| FS read/write | `<store root>`, `<audit file>`, `<catalogue cache>`, `<config root>` | durable state |
| Network egress | INV-65 catalogue endpoint only (via the `source` callable) | catalogue refresh |
| Secrets | `catalogue`, `token`, `audit`, `artifact` keys via a KMS-backed `SecretStore` | trust |
| Nothing else | no device, no raw sockets, no subprocess, no ptrace | — |

Reference deployment profile (systemd; equivalent seccomp/AppArmor/container settings apply):

```ini
[Service]
User=pln02
DynamicUser=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
NoNewPrivileges=yes
ReadWritePaths=/var/lib/pln02
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressDeny=any
IPAddressAllow=<inv65-catalogue-cidr>
CapabilityBoundingSet=
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources @mount @debug
MemoryDenyWriteExecute=yes
LockPersonality=yes
UMask=0077
```

Encryption: in-transit TLS is terminated by the hosting RPC layer (not in this archive); at-rest encryption of
`/var/lib/pln02` is provided by the host volume (LUKS/cloud KMS). This archive cannot verify either, so the
gate records C047 and the deployment half of MC-20 as **BLOCKED_EXTERNAL** until a deployment attestation is
attached to the evidence bundle.

Tenant isolation inside the process: tenant-scoped store paths, per-tenant admission buckets, entitlement
checks, tenant-labelled telemetry. Cross-tenant memory isolation requires one process per tenant class if
co-tenancy of hostile tenants is in scope.
