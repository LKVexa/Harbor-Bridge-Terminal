# Distribution policy (MC-39)

| Format | Allowed now? | Must contain |
|---|---|---|
| Source archive (zip/tar) | internal only | LICENSE, NOTICE, THIRD_PARTY_NOTICES.md, FILE_MANIFEST.sha256, evidence/ |
| Wheel / sdist | internal only | same, plus `License-Expression` metadata matching LICENSE |
| Container image | not until licence chosen | same + SBOM + image digest in gate evidence |
| Vendored copies into other repos | not until licence chosen | — |

Rules: packaging fails if LICENSE is missing or still pending for an **external** release tier; package metadata
must match LICENSE; any dependency with unknown/copyleft licence blocks release until reviewed; contributors are
recorded via signed-off commits (DCO) in the parent repository; cryptography notice: the package implements
HMAC-SHA256 and optionally uses Ed25519 via `cryptography` — check export rules for the chosen channel.
