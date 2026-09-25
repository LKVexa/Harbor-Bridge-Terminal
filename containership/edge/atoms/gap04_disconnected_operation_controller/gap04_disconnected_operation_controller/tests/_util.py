import pathlib, sys, tempfile, shutil, io, contextlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from gap04_disconnected_operation_controller.runtime import testing as T  # noqa: E402
from gap04_disconnected_operation_controller.runtime.errors import Gap04Error  # noqa: E402


class Tmp:
    def __enter__(self):
        self.d = pathlib.Path(tempfile.mkdtemp(prefix="gap04-"))
        return self.d

    def __exit__(self, *a):
        shutil.rmtree(self.d, ignore_errors=True)


class Quiet(io.StringIO):
    pass


def node(tmp, **kw):
    from gap04_disconnected_operation_controller.runtime.observability import StructuredLogger
    kw.setdefault("logger", StructuredLogger("site-a", kw.get("owner", "node-1"), stream=Quiet()))
    return T.make_node(tmp, **kw)


def code(tc, c, fn, *a, **kw):
    with tc.assertRaises(Gap04Error) as cm:
        fn(*a, **kw)
    tc.assertEqual(cm.exception.code, c, cm.exception)
    return cm.exception
