"""Test-only hooks for falsifier tests (imports tools as modules)."""
import importlib.util
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def interop_with_broken_alt():
    from .wire import codec_alt
    interop = _load("interop")
    orig = codec_alt.decode_wait

    def broken(b):  # accepts anything the header allows, ignoring canonical order
        c = codec_alt._Cur(b)
        codec_alt._header(c)
        n = c.uint(2)
        out = [codec_alt._handle(c) for _ in range(n)]
        c.done()
        return out

    interop.A["wait"] = broken
    try:
        _, fails = interop.run_vectors()
    finally:
        interop.A["wait"] = orig
    return len(fails)
