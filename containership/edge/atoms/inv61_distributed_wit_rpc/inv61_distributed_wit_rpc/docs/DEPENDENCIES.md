# Dependencies (M01, M30)

| Dependency | Role | Pin | Integrity | Status |
|---|---|---|---|---|
| `cryptography` | AES-256-GCM record layer (M08) | `==46.0.7` (the version this build was tested against) | artifact hashes **not recorded** — the package index was unreachable from the build container | PINNED, HASHES OPEN |
| `cffi` | transitive of `cryptography` | resolved by release CI | not recorded | OPEN |
| `pk_core` | contract/component gate layer (`contract.py`, `component.py`) | **none possible** | none | **BLOCKED** |

## pk_core — what is known and what is not

Imported symbols (enforced by `tests/test_pk_core_compat.py`):
`pk_core.contract.{Contract, Dependency, Slo}`, `pk_core.checklist.{ChecklistItem, Finding}`,
`pk_core.component.Component`.

Unknown, and not invented here: canonical repository, package name on an index, owner,
version, digest, licence. The package is absent from the supplied archive. The
Post-Kubernetes Master Series v4.0.0 build that produced INV-61 is the likeliest
source; the owner has to name it. Until then:

* the transport/codec/security layer (`rpc.py`, `wrpc/`) has no `pk_core` dependency at all;
* the three `test_component` conformance tests skip locally, and the release CI job sets
  `INV61_REQUIRE_PK_CORE=1`, which turns absence into a failure (`test_release_gate_requires_pk_core`).

To close M01: add the source to `pyproject.toml` as an exact pin or VCS revision, record its
sha256 in `requirements.lock` with `--require-hashes`, set `REQUIRED_VERSION`/`REQUIRED_SHA256`
in `wrpc/pkcore_compat.py`, and run the release job.

## Update policy

Review monthly and on any advisory. A dependency bump is a normal change: CI matrix +
bench regression gate + new SBOM. Revocation of a compromised revision: remove the pin,
cut a patch release, and record it in the waiver register (OPERATIONS.md §7).
