# Key custody, creation ceremony and provider contract

## Contract (`keys.KeyCustody`)
`sign(ref, message, request_id)`, `public_key(ref)`, `metadata(ref)` and `health(ref)`. The contract has no
operation that returns private-key bytes. Adapters take an injected client that is already authenticated with
**workload identity**, as listed below. No adapter accepts static credentials.

| provider | adapter | identity | version pinning |
|---|---|---|---|
| AWS KMS | `AwsKmsCustody(boto3.client("kms"))` | IRSA / EKS Pod Identity / instance role | `KeyRef.version` = concrete key id (never alias) |
| Azure Key Vault / Managed HSM | `AzureKeyVaultCustody(KeyClient, CryptographyClient factory)` | Managed identity / workload identity federation | key version in `KeyRef.version` |
| Google Cloud KMS | `GcpKmsCustody(KeyManagementServiceClient)` | Workload Identity | `cryptoKeyVersions/N` |
| HashiCorp Vault Transit | `VaultTransitCustody(hvac.Client)` | Kubernetes/JWT auth | `key_version`, and the `vault:vN:` prefix is checked |
| PKCS#11 HSM | `Pkcs11Custody(session_factory, mechanisms)` | HSM partition login (PIN from secret manager) | label `name@version` |
| TPM | via the PKCS#11 adapter (tpm2-pkcs11) | platform | as PKCS#11 |

`ResilientCustody` wraps each adapter. It adds a per-call timeout, retries only for transient errors (throttle, timeout,
outage, HSM session exhaustion), a circuit breaker (`CIRCUIT_OPEN`) and request correlation IDs in the audit ledger.
**Every signature is checked against the pinned SPKI before it is released.** An alias or version that silently moved
fails with `KEY_MISMATCH`. `check_key_policy` enforces enabled state, protection level (`hsm`, `external-hsm` or `tpm`
by default), non-exportability and the permitted algorithm. `health()` reads metadata only and never spends a signing
operation. No path falls back to a software key. Outage codes are `KEY_UNAVAILABLE` (transient) and
`KEY_DISABLED` (permanent).

## Ceremony (production release and config-authority keys)
1. Change ticket opened. At least 3 participants: key custodian, security officer and an independent witness.
2. Keys are generated **inside** the provider or HSM as non-exportable asymmetric signing keys, with the algorithm
   from the signature profile. Record the provider key id and version, the protection level, the region and the
   public SPKI SHA-256.
3. IAM or role policy grants the signer workload `Sign` + `GetPublicKey` on that exact key or version only. Operators
   get no `Sign` permission, and key deletion needs two-person approval with a scheduled-deletion window of at least 30 days.
4. The SPKI is placed into a `PK_CERT/1` leaf issued by the intermediate CA (offline root) and distributed in a new
   trust generation signed by the config authority.
5. Evidence goes to the release evidence bundle: provider metadata JSON, IAM policy digest, witness signatures and the
   SPKI pin.
6. Backup: providers that support it hold backups under provider-managed HSM wrapping. No plaintext export happens,
   ever. If a key is lost, **rotate**; never restore.
7. Destruction: revoke the kid in a trust delta, wait out the retention window of artifacts that depend on it, then
   schedule deletion with two-person approval.

Separation of duties: the **config authority** (signs trust, policy, waivers and break-glass) and the **release
signers** (sign artifacts) are separate keys held by separate teams. `verify_config` checks the purpose set of each
authority key.
