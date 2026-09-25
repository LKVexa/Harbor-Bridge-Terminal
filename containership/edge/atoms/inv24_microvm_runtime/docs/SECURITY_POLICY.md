# Patching, vulnerability and EOL policy (MC-058)

| Severity (CVSS v3/v4) | Fix/mitigate SLA | Applies to |
|---|---|---|
| Critical (≥9.0) or guest-escape | 72 h mitigate (quarantine/freeze), 7 d patch | Firecracker, jailer, host kernel/KVM, this package |
| High (7.0–8.9) | 14 d | same |
| Medium | 60 d | same |
| Low | next minor | same |

- Firecracker updates: new version → update manifest pin + compatibility matrix + snapshot `supported_firecracker` → full gate → staged rollout.
- Coordinated disclosure: security@ contact **UNASSIGNED**; embargo honoured; fixes land via private branch.
- Supported branches: current MINOR and previous MINOR; EOL announced 90 d ahead. 4.2.x EOL on 4.3.0 GA + 90 d.
