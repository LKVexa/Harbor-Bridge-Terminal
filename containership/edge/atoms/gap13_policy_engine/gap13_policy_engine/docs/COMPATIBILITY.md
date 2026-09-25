# Compatibility / version matrix (G13-MC-017)

Generated from `compat.MATRIX` (authoritative, test-enforced).

```json
{
  "schema": "PK_POLICY_COMPAT/1",
  "engine_release": "5.0.0",
  "bundle_schemas": {
    "accept": [
      "PK_POLICY_BUNDLE/1"
    ],
    "reject": [
      "*"
    ]
  },
  "envelope_schemas": {
    "accept": [
      "PK_POLICY_SIGNED_BUNDLE/1"
    ]
  },
  "verdict_schema": "PK_POLICY_VERDICT/1",
  "explanation_schema": "PK_POLICY_EXPLANATION/1",
  "error_schema": "PK_POLICY_ERROR/1",
  "rpc": {
    "path_prefix": "/v1",
    "versions": [
      "v1"
    ]
  },
  "python": {
    "min": "3.10",
    "tested": [
      "3.10",
      "3.11",
      "3.12",
      "3.13"
    ]
  },
  "platforms": {
    "tested": [
      "linux"
    ],
    "declared_supported": [
      "linux",
      "windows",
      "macos"
    ],
    "note": "Windows/macOS declared portable (stdlib, os.replace, no fork); CI evidence pending -- see WAIVERS.json W-004"
  },
  "optional_dependencies": {
    "cryptography": ">=41 (Ed25519 verification); absent -> bundles fail closed"
  },
  "adjacent_interfaces": {
    "GAP-07": "GAP07_TRUST_SOURCE/1 (trust store) + PK_POLICY_SIGNED_BUNDLE/1",
    "GAP-04": "PK_POLICY_CACHE/1 last-known-good cache, disconnected staleness modes",
    "PLN-01": "consumes PK_POLICY_VERDICT/1",
    "PLN-06": "consumes PK_POLICY_VERDICT/1 (residency attribute is protected/trusted)",
    "PLN-07": "consumes PK_POLICY_VERDICT/1; identity via PK_POLICY_TOKEN/1"
  },
  "breaking_changes_from_4x": [
    "PolicyEngine.load no longer accepts a caller mapping {'verified': True}; a BundleVerifier-minted VerificationResult is required",
    "Rule.matches is type-strict (True != 1, '1' != 1)",
    "verdict gains 'bundle' field; service verdicts add 'mode','lineage','trace_id'"
  ]
}
```
