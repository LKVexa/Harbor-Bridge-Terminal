import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from inv15_new_asynchronous_abi.host import AsyncHost, Limits  # noqa: E402


class FakeClock:
    def __init__(self, t=1_000):
        self.t = t

    def __call__(self):
        return self.t


def mk(limits=None, **kw):
    clock = kw.pop("clock", FakeClock())
    h = AsyncHost(limits or Limits(), clock=clock, **kw)
    return h, clock
