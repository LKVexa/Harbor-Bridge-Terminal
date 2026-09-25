"""INV-08 production overlay (components 01-66 of the v4.2.0 missing-component checklists).

Stdlib-only.  Everything here is additive: the 15 files of the hardened v4.2.0
reference package are left byte-identical and are imported, never edited.

Honesty rule for this overlay: a module implements and tests the machine-reachable
part of a component.  Owner assignment, independent review, real providers, real
KMS/HSM, real attestation hardware, signed releases with an asymmetric trust root
and live environments are *not* produced here; ``status.py`` records each of those
checks as BLOCKED with the missing input named.
"""
OVERLAY_VERSION = "1.0.0"
BASE_VERSION = "4.2.0"
