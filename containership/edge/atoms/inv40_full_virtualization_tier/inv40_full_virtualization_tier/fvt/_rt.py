"""Import shim: the reference runtime whether loaded as a package or from its directory."""
try:  # package import: inv40_full_virtualization_tier.fvt
    from .. import runtime as runtime  # type: ignore
except (ImportError, ValueError):  # tests put the package directory on sys.path
    import runtime  # type: ignore  # noqa: F401
