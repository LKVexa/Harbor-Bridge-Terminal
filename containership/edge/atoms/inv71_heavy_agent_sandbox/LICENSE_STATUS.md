# Licence status (INV71-X005)

**No licence selected.** The package has no `LICENSE` file, and redistribution and use terms are undefined. Choosing a licence and confirming rights to all contents is a decision for the repository owner or their legal authority. The remediation pass did not make that decision for them.

Facts relevant to that decision:
- All code in this package was written for INV-71 (versions 4.0.0-4.3.0). No third-party code, test corpus or specification text is vendored (see `THIRD-PARTY-NOTICES.md`).
- Runtime dependencies: none (Python standard library only). Optional test dependency: `jsonschema` (MIT). It is used only to validate fixtures and is not redistributed.
- Future production artifacts carry their own licences. Firecracker is Apache-2.0. The Linux kernel is GPL-2.0, and guest rootfs packages have mixed licences. Those licences will attach to images and snapshots, not to this Python package. A build-time licence inventory must be produced for them.

`tools/production_gate.py` fails while `LICENSE` is absent.
