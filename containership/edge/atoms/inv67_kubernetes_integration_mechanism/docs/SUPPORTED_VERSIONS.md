# Supported versions and deprecations (item 56)
| INV-67 | Kubernetes | Python | CRD | Wire | Status |
|---|---|---|---|---|---|
| 4.3.x | 1.29–1.32 (declared; not cluster-verified) | 3.10–3.13 | v1alpha1 | TRANSLATE/REFUSE/STATUS/PLACE /1 | current |
| 4.2.x | n/a (translator only) | 3.10+ | — | TRANSLATE/REFUSE/STATUS /1 | supported until 4.5.0 |

Deprecated: legacy per-unit `cpu`/`memory` request aliases in `PK_K8S_TRANSLATE/1` — removal planned for `/2`, not before 4.5.0.
