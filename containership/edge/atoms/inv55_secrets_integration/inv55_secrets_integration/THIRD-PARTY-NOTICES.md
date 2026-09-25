# Third-party notices

INV-55 4.3.0 ships **no third-party code**. Runtime and tests use only the CPython standard library.

Pattern-only references consulted during the 4.3.0 chop-shop pass (no code copied):

| Donor (GitHub Junkyard car) | Part consulted | Use | Licence |
|---|---|---|---|
| `amplifier-bundle-redaction` | `modules/hook-redaction/amplifier_module_hook_redaction/__init__.py` | fail-closed scrub-on-error pattern (a scrub failure yields "redaction not applied", never the raw event) → mirrored in `telemetry.scrub` refusing `_SecretValue` | no LICENSE file in the yard copy — pattern only, nothing copied |
