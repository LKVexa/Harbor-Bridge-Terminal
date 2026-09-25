"""Shared test bootstrap: make the package (and its vendored pk_core) importable from a clean checkout."""
import pathlib
import sys
import warnings

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
sys.dont_write_bytecode = True
for p in (str(ROOT), str(PKG_DIR / "_vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"inv28_unikernel_implementations.*")

import inv28_unikernel_implementations as pkg  # noqa: E402,F401  (re-exported for tests)
from inv28_unikernel_implementations import fixtures as F  # noqa: E402,F401
from inv28_unikernel_implementations.errors import (  # noqa: E402,F401
    BindingError,
    Inv28Error,
    Reason,
    RefusalError,
    RegistryError,
    ValidationError,
)


def refusal(fn):
    """Run fn, return (code, refusal-or-None); fail if it succeeds."""
    try:
        fn()
    except RefusalError as exc:
        return exc.refusal.code, exc.refusal
    except Inv28Error as exc:
        return exc.code.value, None
    raise AssertionError("expected a refusal, call succeeded")


def codes_for(ref_obj, toolchain_ref):
    for e in ref_obj.eliminated:
        if e["toolchain"] == toolchain_ref:
            return e["codes"]
    return None
