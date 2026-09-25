# Compatibility and versioning policy (items 05, 50, 56)

Machine-readable matrix: `plane/compat.py::SUPPORTED_MATRIX` (checked at bootstrap; peers outside it are refused).

| Dimension | Supported | Evidence in this archive |
|---|---|---|
| Kubernetes | 1.29 – 1.32 | **none against real clusters** (EXC-005); fake API server only |
| Python | 3.10 – 3.13 | CI matrix defined in `.github/workflows/ci.yml`; locally verified on 3.11 |
| CRD | `inv67.linearfinance.org/v1alpha1` (served+storage) | contract tests |
| Wire | `PK_K8S_TRANSLATE/1`, `PK_K8S_REFUSE/1`, `PK_K8S_STATUS/1`, `PK_K8S_PLACE/1` | schema conformance tests |
| pk_core / SCH-01 / INV-68 / PLN-02 / GAP-15 | versions not published by those owners | **unknown — EXC-006** |

## Semantic versioning

* **Python API / package:** SemVer. Removing or changing a public function signature = major.
* **JSON schemas:** the `/N` suffix is the major version; additive optional fields are allowed within a major only when the consumer schema permits them. Our schemas use `additionalProperties: false`, so any field addition is a new major (`/2`) — deliberate: no silent drops on either side.
* **CRD:** `v1alpha1` may change with notice; `v1beta1` onwards follows Kubernetes deprecation policy (≥ 9 months or 3 releases).
* **Config (`INV67_CONFIG/1`):** unknown keys are refused, so new keys require a new controller before the config that uses them (roll controller first, config second).

## Skew windows

* Controller replicas: N and N-1 minor may coexist during a rollout; only the leader acts, fencing makes handoff safe.
* CRD storage vs served: exactly one storage version; a new version is served for one minor before becoming storage, with storage-version migration run in between.
* Downstream: INV-67 N supports `PK_K8S_PLACE/1` only; a `/2` requires a dual-writing release.

## Unknown values

Unknown enum values from peers are mapped to `Unknown` (status) or refused (inputs). Feature negotiation: the controller advertises `certifiedFeatures` on `/version`.

## Deprecation / EOL

Deprecations are announced in `CHANGELOG.md` and `SUPPORTED_VERSIONS.md` with a removal version; removal no sooner than two minor releases later. Each Kubernetes minor is dropped when upstream EOLs it.
