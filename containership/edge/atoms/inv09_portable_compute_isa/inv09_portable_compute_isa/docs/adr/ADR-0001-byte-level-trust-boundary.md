# ADR-0001: Byte-level validation is the trust boundary
Status: accepted (v4.3.0). Context: v4.2.0 validated a descriptor whose `used_features` a caller could
fill in. Decision: facts come only from `prod/typecheck.validate_module(bytes)`; the v4.2.0 kernel
(`validator.py`) is kept as a documented policy mirror whose profiles are tested for equality with the
bundle. Consequence: callers cannot express "trust me" — there is no API for it.
