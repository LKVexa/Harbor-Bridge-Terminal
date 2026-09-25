# Identity, capability, sandbox, crypto and trust-service policy

## Least-privilege identity and capability design (C024, C042)

| Principal | Typical holder | Actions granted | Scope |
|---|---|---|---|
| vhost worker / VMM I/O thread | per-guest process | `submit`, `complete` | one tenant, its queues |
| controller | orchestration service | `register_memory`, `lifecycle` | one tenant, named queues, current epoch |
| operator | human via tooling | `configure`, `read_status` | named queues |
| security responder | human/automation | `quarantine` | named queues |

Capabilities are short-lived (default 300 s, max 3 600 s), scoped by tenant,
queue set and action set, MACed with the active key, optionally single-use.

## Boundary authentication (C023, C044)

| Peer | Mechanism in reference model | Production binding |
|---|---|---|
| VMM / vhost worker | capability token | token issued after process attestation (SPIFFE-style workload identity) |
| Controller | capability + epoch | mTLS + token; epoch from lease service |
| Node / peer host | n/a (single host) | mTLS with node identity from attestation |
| Artifact | SHA-256 manifest + sealed evidence | Sigstore signature + SLSA provenance (TD-002) |
| Config provider | provenance digest + `configure` capability | signed config bundles |

## Ambient-authority elimination and sandbox policy (C043)

* No module-level mutable authority; all privileged paths take a capability.
* The runtime performs **no file, network, subprocess or environment access** on
  the datapath. File access exists only in `config.load_file` (operator-invoked)
  and release tooling. A static test (`tests/security/test_sandbox_policy.py`)
  enforces this import surface.
* Production processes SHOULD run with seccomp allow-lists, no new privileges,
  read-only root, and only the vhost/vfio device nodes they need.

## Encryption and key rotation (C047)

See `CRYPTO_AND_KEY_POLICY.md`.

## Safe behaviour when trust services fail (C048)

| Service | Failure | Behaviour |
|---|---|---|
| Key service | unavailable | all authz refused E306; cache flushed; `ready=false`; audit append refused (cannot sign) |
| Trusted time | untrusted | all authz refused E306 |
| Attestation | unavailable | no new capabilities minted (production binding) |
| Policy/config | unreachable | last-good config; offline policy (§6 of requirements) |
