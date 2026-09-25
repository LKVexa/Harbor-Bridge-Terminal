"""INV-09 v4.3.0 production validation boundary (byte-level).

Implements the P0 chain from the missing-components checklist:
M01 decoder -> M02 type validator -> M03 feature detector -> M04 binding ->
M07 digest -> M08 attestation -> M09 cache -> M10/M11 admission, governed by
M05/M06 registries, M12 failure schema and M13 resource governor.
Pure stdlib except M08 signing, which needs ``cryptography`` (Ed25519) and
fails closed when it is absent.
"""
VALIDATOR_ID = "inv09-wasmval"
VALIDATOR_VERSION = "4.3.0"
