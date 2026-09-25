import os, pathlib, sys, tempfile
PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))
sys.dont_write_bytecode = True
KEY = b"k" * 32
KEY2 = b"z" * 32


def tmpdir():
    return tempfile.mkdtemp(prefix="inv14-")


def make_service(tmp=None, *, max_concurrent=8, tenant_max=4, gate=None, clock=None):
    import identity, admission, lifecycle, audit, telemetry, pollog, service, io
    tmp = tmp or tmpdir()
    kw = {"clock": clock} if clock else {}
    iss = identity.Issuer(KEY, "k1", **kw)
    ver = identity.Verifier({"k1": KEY}, **kw)
    buf = io.StringIO()
    svc = service.LegacyPollService(
        verifier=ver, admission=admission.AdmissionController(max_concurrent=max_concurrent, tenant_max=tenant_max),
        lifecycle=lifecycle.Lifecycle("DEPRECATED"), audit=audit.AuditSink(os.path.join(tmp, "audit.jsonl"), KEY),
        telemetry=telemetry.Telemetry(seed=1), logger=pollog.StructLogger(buf), consumer_gate=gate)
    return svc, iss, buf, tmp
