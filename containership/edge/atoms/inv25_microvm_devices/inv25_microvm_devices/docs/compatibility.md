# Compatibility matrix and negotiation (work items 12, 15, 24 — C016, C027, C031, C084, C093)

Machine-readable source: `compat.MATRIX` and `compat.SUPPORTED_SCHEMAS`.

## Schemas
| Interface | Supported | Security floor |
|---|---|---|
| catalogue | PK_DEVICE_CATALOGUE/1 | 1 |
| diff | PK_DEVICE_SURFACE_DIFF/1 | 1 |
| error | PK_DEVICE_ERROR/1 | 1 |
| audit | PK_DEVICE_AUDIT_EVENT/1 | 1 |
| activation | PK_DEVICE_CONFIG_ACTIVATION/1 | 1 |

## Peers
| Peer | Range | Status | Evidence |
|---|---|---|---|
| pk_core | >=4.0,<5.0 (PROPOSED) | unverified | not available — work item 1 |
| INV-24 / INV-35 / INV-26 / GAP-13 | unpinned | unverified | contract fixtures only |
| INV-43 (optional) | unpinned | optional-unverified | fixture only |
| OASIS VIRTIO | 1.2 | declared | ADR-0001 |
| CPython | 3.10–3.13 | supported | CI matrix |

## Platform matrix (C084)
| Arch / OS | Status |
|---|---|
| linux/x86_64, CPython 3.11 | exercised (this pass) |
| linux/x86_64, CPython 3.10/3.12/3.13 | CI matrix — pending first run |
| linux/arm64 | experimental — hardware evidence required |
| Hypervisors (Firecracker / Cloud Hypervisor / QEMU microvm) | unsupported until peer evidence exists |

The catalogue package is pure Python with no endianness/word-size dependence; hypervisor cells are
peer-owned. Support claims are removed if a cell cannot be tested for 90 days.

## Negotiation policy
- Each side advertises its full list; the highest mutually supported version wins (`compat.negotiate`).
- No overlap ⇒ `INV25_COMPATIBILITY_MISMATCH` — fail closed, never silent downgrade.
- Offers below the security floor and malformed/unknown-future identifiers are ignored.
- A new major schema version ships alongside the old one for ≥ 2 minor releases with a deprecation notice
  in `CHANGELOG.md`; mixed-version rolling deploys therefore always share one version.
- Old catalogue documents are re-validated by `catalogue_from_export` on load.
- `pk_core` outside the supported range is rejected at startup (`compat.check_pk_core`).
