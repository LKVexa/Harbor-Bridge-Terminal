# Third-party notices

INV-36 5.1.0 contains no copied third-party source code. It depends at runtime on:

| Package | License | Notes |
|---|---|---|
| cryptography | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography - LICENSE, LICENSE.APACHE, LICENSE.BSD in its distribution |
| cffi | MIT | transitive, via cryptography |
| pycparser | BSD-3-Clause | transitive, via cffi |

GitHub Actions used by CI (not redistributed): actions/checkout, actions/setup-python, actions/upload-artifact (MIT).

No parts were pulled from the GitHub Junkyard for this release (see the work order `inv36_control_transport-20260922`).
