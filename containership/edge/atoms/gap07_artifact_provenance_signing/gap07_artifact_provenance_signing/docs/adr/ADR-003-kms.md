# ADR-003: KMS/HSM
Status: accepted; the estate must choose its primary provider
Decision: provider-neutral `KeyCustody` with AWS KMS, Azure Key Vault/MHSM, GCP KMS, Vault Transit and PKCS#11 adapters. Production requires protection level hsm, external-hsm or tpm, and non-exportable keys. Versions are pinned and every signature is verified post-sign.
Open: which provider is primary per estate region (estate decision).
