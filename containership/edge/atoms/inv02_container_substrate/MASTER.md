# INV-02 Container Substrate — MASTER distribution contract

**Version:** 5.0.0 · **Element:** INV-02 · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Status:** restored (checklist MC68 / E-01). Enforced by `tools/release_evidence.py` (`governance_files_present` gate) and CI.

## 1. What this package is

A stdlib-only Python substrate for container image identity, integrity, storage,
distribution, unpacking, runtime-spec generation, and admission. It *drives* an OCI
runtime (runc / crun / runsc / kata); it is not itself a kernel-level runtime and does
not replace a registry service.

## 2. Distribution contents (authoritative)

| Path | Role | Checklist |
|---|---|---|
| `registry.py` | v4.2 in-memory reference model (kept for compatibility) | — |
| `oci.py` | OCI image-spec model, platform selection | MC01, MC14 |
| `store.py` | durable CAS, metadata DB, CAS tags, leases/GC, fsck/repair, backup/restore, durable quarantine | MC03, MC15, MC30, MC34–38, MC52 |
| `distribution.py` | OCI Distribution client: auth, TLS, mirrors, offline, resumable blobs | MC02, MC16, MC17, MC36, MC39, MC40 |
| `rootfs.py` | layer unpack, snapshotter, bind-mount policy | MC04, MC09, MC13 |
| `runtime.py` | OCI runtime spec, namespaces, cgroups v2, lifecycle, supervision, seccomp, caps, userns, MAC, NNP, devices, secrets, volumes, networking modes, sandboxed runtime classes | MC05–MC12, MC22–MC28, MC33 |
| `trust.py` | Ed25519, keyring rotation, DSSE/in-toto, SBOM, scan states | MC18–MC21, MC55 |
| `policy.py` | admission engine, tenant isolation, decision explain, waivers | MC29, MC32, MC49, MC77 |
| `audit.py` | tamper-evident audit ledger | MC31 |
| `observability.py` | metrics, JSON logs + redaction, tracing, health endpoints | MC45–MC48 |
| `resilience.py` / `timeutil.py` | quotas, admission control, retry, circuit breaker, deadlines | MC41–MC44 |
| `config.py` / `migrations.py` | configuration system; migration framework | MC54, MC76, MC53 |
| `tests/` | unit, adversarial, fuzz, race, fault-injection, local-registry, real-runtime integration | MC57, MC58–MC64 |
| `tools/` | release evidence + SBOM + manifest; benchmarks/soak | MC65, MC67, MC70 |
| `docs/` | ADR, operations runbooks, dashboards/alerts, capacity, backup, upgrade, rotation | MC50–MC53, MC55, MC56, MC72 |
| `COMPONENT_STATUS.json` | per-component status for MC01–MC78 with evidence pointers | G-01 |

## 3. Invariants every release must hold

1. Content is addressed by digest and re-verified on every read; no silent repair.
2. Protected environments resolve digests only; tags come only from the authoritative registry.
3. Security-significant defaults fail closed (seccomp default-deny, no capabilities, NNP, read-only rootfs, no host namespaces, no devices, secrets never in env).
4. Every privilege escalation (capability, device, host namespace, privileged) needs an explicit policy grant.
5. Persisted formats are versioned; newer-than-supported schemas are refused, never downgraded.
6. A skipped test is not a pass; release evidence lists every skip with its reason.

## 4. Release procedure

```text
python -m unittest discover -s inv02_container_substrate/tests -t . -v
python -O -m unittest discover -s inv02_container_substrate/tests -t . -v
python -m inv02_container_substrate.tools.release_evidence
```

A release is shippable only when `evidence/release-evidence.json` reports `"verdict": "PASS"`
and the owner-actions listed in `COMPONENT_STATUS.json` (`status: owner-action`) are closed or waived.
