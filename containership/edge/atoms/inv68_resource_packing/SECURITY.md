# INV-68 security architecture 4.3.0 (MC-06, MC-11, MC-14)

## Identity and authorization (MC-06; C023, C024, C042–C046)

* **Principals:** `workload-scheduler` (SCH-01), `k8s-adapter` (INV-67), `node`,
  `operator`, `controller`. Wildcard tenant scope only for operator/controller.
* **Credentials:** `v1.<claims>.<HMAC-SHA256>` tokens (auth.py): `sub, kind, tenants,
  caps, iat, exp (≤ 1 h), nonce (single use), kid`. Clock skew ±30 s. Trust roots are
  keyed by `kid` so keys rotate by adding the new kid, re-issuing, then removing the old.
* **Capabilities (least privilege):** see `auth.KIND_CEILING` — a scheduler can never
  hold `config:*` or `control:freeze` even if a token claims it.
* **Policy evaluation points:** every public service method authenticates first, then
  `Authorizer.require(capability, tenant)`. The pure engine has no ambient authority:
  no file, network, subprocess or environment access.
* **Denials:** `UNAUTHENTICATED` / `FORBIDDEN` / `REPLAY_DETECTED`, never a hint about
  which check failed; all audited through the request log.
* **Node / peer / control-plane identity:** nodes and controllers are principals of
  their own kind; peer components (INV-67, INV-72, GAP-10) never call INV-68 with
  ambient trust. Production SHOULD replace HMAC with mTLS (SPIFFE IDs) or OIDC
  workload identity; `Authorizer.authenticate(token) -> Principal` is the seam.

## Secrets (MC-11; C039, C075)

Configuration may contain only `secretref://<provider>/<key>[@version]` references;
anything credential-like is `SECRET_IN_CONFIG`. Keys (token trust roots, audit MAC,
anchor key, release signing key) come from the deployment's secret store at
process start and are never written to disk by INV-68. Logs, errors, audit details,
metric labels and explain lineage pass through `redaction.redact`. The repository is
scanned on every run (SECRET_SCAN.json; 2 allow-listed fake credentials in negative tests).

## Cryptographic profile (MC-14; C047)

| Use | Algorithm | Status |
|---|---|---|
| request tokens | HMAC-SHA256, 256-bit keys | implemented |
| audit record MAC + anchor | HMAC-SHA256 | implemented (keys supplied by deployment) |
| audit chain | SHA-256 hash chain | implemented |
| config identity | SHA-256 over canonical JSON | implemented |
| release provenance | Ed25519 DSSE (in-toto v1) | implemented; managed signer NOT configured (ephemeral key) |
| transport | TLS 1.3 required for any network adapter (none shipped) | policy only |
| at rest | state dir on encrypted volume (deployment) — INV-68 stores no secrets | policy only |

Rotation: token keys ≤ 90 days, audit keys ≤ 365 days with re-seal, signing keys per
release manager policy. Rotation evidence requires an owner (MC-03).

## Trusted-service outage behaviour (MC-14; C048)

| Dependency | Outage behaviour | Fail mode | Evidence |
|---|---|---|---|
| identity (token keys unavailable at start) | service cannot authenticate → every call `UNAUTHENTICATED` | closed | auth tests |
| policy/config store unreadable | last intact snapshot from journal; none → `NOT_READY` | closed | FAULTS F07/F08 |
| audit sink | pack decisions buffered (bounded) with counted loss; config/freeze changes refused | closed for policy, open (visible) for decisions | FAULTS F05/F06 |
| capacity source | breaker; `DEPENDENCY_UNAVAILABLE` → `CIRCUIT_OPEN`; never packs on stale data | closed | FAULTS F01–F03 |
| time | token skew bound ±30 s; capacity from >30 s in the future refused | closed | FAULTS F12, service tests |
| key service (signing) | release build falls back to ephemeral key and the gate reports NO_GO | closed | RELEASE_VERIFY |

## Reporting

See `SECURITY_RESPONSE.md`.
