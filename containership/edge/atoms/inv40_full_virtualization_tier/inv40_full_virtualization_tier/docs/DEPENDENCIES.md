# Dependencies (REPO-001, INV-40-C031)

| Dependency | Kind | Source | Pin | License | Status |
|---|---|---|---|---|---|
| CPython stdlib | runtime | python.org | ≥3.10 | PSF | declared in pyproject |
| pk_core | optional integration (`[pk_core]` extra) | **unknown — not supplied** | **UNPINNED** | unknown | BLOCKED: need the distribution (Post-Kubernetes series core) to pin a range and generate a hashed lock |
| QEMU | host binary | distro package | ≥7.2 proposed, exact pin pending | GPL-2.0 (host tool, not linked or redistributed) | not verified |
| Linux KVM | host kernel | distro | — | GPL-2.0 (host) | not verified |

There are **zero third-party Python runtime dependencies**, so `requirements.lock` is the empty set, recorded with its hash in `evidence/deps.lock.json`. Offline install: `pip install --no-index .` works because nothing is fetched.
API surface used from pk_core: `fvt/compat.py::PK_CORE_API` — a test fails if `contract.py`/`component.py` import anything not declared there.
