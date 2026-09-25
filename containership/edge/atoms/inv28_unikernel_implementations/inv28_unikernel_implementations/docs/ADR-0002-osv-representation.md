# ADR-0002: OSv catalog representation (MC-095)

**Status:** PROPOSED (owner decision D-002) · **Date:** 2026-09-23

## Decision
The component description names OSv, but no one has asked for OSv support or evidenced it. The catalog therefore carries OSv as `catalog_status: "unregistered"`, `lifecycle: "candidate"`, and it is unselectable in every environment. Its notes field says this outright.

## Rule enforced by a test
Any toolchain the README names must have a catalog entry, and any catalog entry that is not `supported` must be unselectable in production. The test is `tests/test_interfaces.py::CatalogConsistency`.

## To make OSv supported
Register a pinned version with review provenance, an integrity identity and a GAP-15 certificate, and set `catalog_status: "supported"`. That is the owner's call.
