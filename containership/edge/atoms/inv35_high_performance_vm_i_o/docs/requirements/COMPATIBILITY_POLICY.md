# Versioning, compatibility and negotiation policy (C016, C027, C093)

## Package versioning
Semantic versioning on `VERSION`: MAJOR = any breaking change to a public
interface, error-code outcome class, lifecycle graph or config field meaning;
MINOR = additive (new optional field, new error code, new profile); PATCH = no
interface change.

## Interface versioning
Each wire schema carries `NAME/MAJOR` (`PK_VIRTQUEUE_SUBMIT/1`). Within a major:
fields may be **added only as optional**; none removed, renamed or re-typed;
`additionalProperties:false` means a *new* field requires a new MINOR package
release that updates the schema, the RTM and the changelog together.

## Error codes
Append-only. A published code keeps its number and outcome class forever
(`schemas/errors/published_codes_4.3.0.json` is the frozen set; a contract test
fails if any published code changes class).

## Negotiation
`ControlPlane.negotiate(offer)` picks the highest common major for each
interface; required interfaces (`PK_VIRTQUEUE_SUBMIT`, `PK_VIRTQUEUE_COMPLETE`)
with no common major ⇒ E503; unknown interfaces in the offer are ignored.

## Deprecation
A major is deprecated for ≥ 2 minor releases and ≥ 180 days before removal,
listed in `health.DEPRECATED` and `governance/WAIVERS.json#deprecations`.

## Supported adjacent versions (C093)

| Adjacent | Supported | Tested in this repo | Notes |
|---|---|---|---|
| CPython | 3.11, 3.12, 3.13 | 3.11.15 (CI matrix covers 3.11–3.13) | `pyproject.toml` |
| pk_core | **unpinned** | none | blocker: owner must publish version + digest |
| INV-24 MicroVM runtime | interface only | contract double | real build pending (WVR-002) |
| INV-25 MicroVM devices | interface only | contract double | real build pending |
| PLN-06 data plane | interface only | contract double | real build pending |
| vhost-user / vDPA / kernel vhost backends | must pass `fixtures/` | none | WVR-002 |
