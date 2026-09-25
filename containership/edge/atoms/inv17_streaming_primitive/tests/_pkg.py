"""Import helper: make the package importable from its parent folder (no install needed)."""
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))
import importlib

pkg = importlib.import_module(PKG_DIR.name)
stream = importlib.import_module(PKG_DIR.name + ".stream")
control = importlib.import_module(PKG_DIR.name + ".control")
security = importlib.import_module(PKG_DIR.name + ".security")
configuration = importlib.import_module(PKG_DIR.name + ".configuration")
observability = importlib.import_module(PKG_DIR.name + ".observability")
adapters = importlib.import_module(PKG_DIR.name + ".adapters")


def registry(**kw):
    r = control.StreamRegistry(**kw)
    return r


def open_stream(r, sid="s1", tenant="t1", workload="w1", etype=int, rights=("open", "read", "write", "grant", "close"), **kw):
    tok = r.authority.issue(sid, tenant, workload, rights)
    s = r.open(etype, tenant=tenant, workload=workload, token=tok, stream_id=sid, **kw)
    return s, tok
wire = importlib.import_module(PKG_DIR.name + ".wire")
