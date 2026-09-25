# UC-2.7.0 Tenant-Isolation Threat Model

UC-2.7.0 is a **single-operator local candidate**, not a multi-tenant service. Berths provide organizational and state separation, not a security boundary equivalent to a VM/hypervisor.

A tenant-isolation claim would require separate authenticated identities, per-tenant capabilities, OS/hypervisor-enforced memory/process/filesystem/network isolation, secret separation, resource quotas, adversarial cross-tenant tests, and independent qualification. Those conditions are not met. The current controls reduce accidental cross-berth mutation through contained paths, generation fences, checksummed state and command allowlists, but a hostile process sharing the host account is outside the supplied boundary.
