# Third-party notices — INV-03 4.3.0

No third-party source code is vendored in this package. Everything under `hardening/`, `tools/`,
`schemas/`, `fixtures/` and `tests/test_h_*.py` was written new for the 4.3.0 pass.

Reference material consulted for behaviour, not copied:

- Kubernetes Pod Security Standards ("restricted" profile) and the `admission.k8s.io/v1` AdmissionReview
  and `ValidatingWebhookConfiguration` API shapes (Apache-2.0 project documentation).
- W3C Trace Context `traceparent` header format.
- gVisor `runsc --version` output format (`release-YYYYMMDD.N`).
- CycloneDX 1.5 SBOM format.

Development tools (not shipped): jsonschema (MIT), ruff (MIT), mypy (MIT).

The package itself still has **no licence**. None was supplied with the candidate and one has not been
invented; choosing it is the owner's decision (checklist item 70).
