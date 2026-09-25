# OAM baseline profile (MC-11; C031, C093)

**Pinned baseline:** `oam-dev/spec`, tag `v0.3.0`, commit `3104d27a0ecb55cac84755950e53371aa3e1d2b2`
(retrieved 2026-09-22 via `git clone --depth 1 --branch v0.3.0`; file digests in `provenance/oam-baseline.json`).
**License of the reference:** Open Web Foundation Agreement (per upstream CONTRIBUTING.md). No text is copied here.
**Compatibility level:** schema-level for components and traits; conceptual for providers and links. INV-64 is not an OAM runtime.
**Decision record:** ADR-0001 (proposed).

## Concept mapping

| OAM v0.3.0 (§7 Application) | INV-64 app/v1 | Status |
|---|---|---|
| `apiVersion: core.oam.dev/v1beta1`, `kind: Application` | `schema: app/v1` | adapted (export/import in `oam_profile.py`) |
| `metadata.name` | not in the manifest (the app name is the request's `app` field) | adapted |
| `spec.components[].name` | `components[].name` | adopted (INV-64 restricts to `[A-Za-z0-9._-]{1,128}`) |
| `spec.components[].type` | `components[].type` (extension field) | adopted; namespaced `ns/type` **unsupported** (refused on import) |
| `spec.components[].properties` | `components[].properties` | adopted |
| `spec.components[].traits[]{type, properties}` | top-level `traits[]{type, component, properties}` | adapted (flattened; same information) |
| one trait configuration per type per component | not enforced by app/v1 validation | deviation: export refuses duplicates instead of silently merging |
| `spec.components[].scopes` / application scopes | — | unsupported (refused on import) |
| `policies`, `workflow` (later OAM/KubeVela) | — | unsupported (refused on import) |
| — | `providers[]` | INV-64 extension, carried in annotation `inv64.pk/providers` |
| — | `links[]{from, to}` | INV-64 extension, carried in annotation `inv64.pk/links` |

Why the deviations are safe: INV-64 validates strictly more (link/trait
references, secrets); flattening traits is lossless; unsupported constructs
are refused, never ignored, so no OAM semantics are silently dropped.

## Fixtures

`tests/test_v43.py::AdjacentOamRolloutTest.test_oam_round_trip_and_unsupported` —
round trip app/v1 → OAM → app/v1 keeps the canonical digest; `scopes`,
`policies`, `workflow` and duplicate trait types are refused.

## Changing the baseline

1. Open an ADR superseding ADR-0001's baseline section (architecture-review-board approval).
2. Fetch the new tag, record commit + file digests in a new `provenance/oam-baseline.json` entry; keep the old entry under `history`.
3. Diff the upstream Application/Component/Trait sections; classify each change (adopt/adapt/unsupported); update this table, `oam_profile.py`, fixtures, `compatibility.json` (`oam`), `service.OAM_BASELINE`.
4. Security review of any new construct that could carry executable or credential content.
5. `tools/governance_check.py` and the tests fail if documentation, `compatibility.json` and `service.OAM_BASELINE` disagree.
