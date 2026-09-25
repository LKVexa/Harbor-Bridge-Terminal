# Third-party and carried-in parts

| Donor | Part(s) | License | Adaptation |
|---|---|---|---|
| Owner's `inv68_resource_packing` v4.3.0 (work order `inv68_resource_packing-20260923`, GitHub Junkyard `_YARDOFFICE`) | `redaction.py` | owner's code, no license file (same owner) | verbatim, docstring header added |
| same | `audit.py` | owner's code | schema renamed `PK_SNAPSHOT_AUDIT/1`, CLI renamed `inv26-audit` |
| same | `provenance.py` | owner's code | build type URN renamed |
| same | `telemetry.py` (Metrics, StructuredLogger, traceparent) | owner's code | renamed metrics catalog; added `Health`; logger never raises on exporter failure |
| PyPI `cryptography` 46.0.7 | runtime dependency (AES-GCM, Ed25519) | Apache-2.0 OR BSD-3-Clause | not vendored |
| PyPI `cffi` 2.0.0 | transitive runtime dependency | MIT | not vendored |

No public-repository code was copied. The Firecracker and Cloud Hypervisor REST paths used by
`hypervisor.py` follow those projects' public API documentation (Apache-2.0 projects); no code from them is included.
